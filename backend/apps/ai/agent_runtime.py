from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from time import monotonic, sleep
from typing import Any, Callable, Dict, Iterable, List, Optional
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.db.models import Q

from .compat import build_runtime_capabilities
from .models import AIAgentApproval, AIAgentArtifact, AIAgentStep, AIAsyncRun
from .observability import fit_model_char_value, log_ai_request, make_cache_key, normalize_payload
from .response_contracts import normalize_feature_contract
from .runtime_health import assert_runtime_available_for_feature, get_runtime_health


RUN_STATUS_TERMINAL = {"succeeded", "failed", "cancelled"}
APPROVAL_MUTATING_ACTIONS = {"plan_apply", "plan_update", "settings_update", "learning_record_write"}
QUEUED_RUNTIME_FEATURES = ["plan_replan", "retrieval_orchestrator", "vector_rag", "conversation", "study_report"]
STALE_QUEUE_SECONDS = int(getattr(settings, "AI_AGENT_STALE_QUEUE_SECONDS", 30) or 30)
STALE_RUNNING_SECONDS = int(getattr(settings, "AI_AGENT_STALE_RUNNING_SECONDS", 180) or 180)
SYNC_WAIT_TIMEOUT_MS = int(getattr(settings, "AI_AGENT_SYNC_WAIT_TIMEOUT_MS", 2200) or 2200)
SYNC_WAIT_INTERVAL_MS = int(getattr(settings, "AI_AGENT_SYNC_WAIT_INTERVAL_MS", 150) or 150)


@dataclass
class AgentStepResult:
    output_payload: Dict[str, Any] = field(default_factory=dict)
    summary: str = ""
    status: str = "succeeded"
    metadata: Dict[str, Any] = field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    error_message: str = ""


@dataclass
class AgentRunResult:
    feature_type: str
    result_payload: Dict[str, Any]
    degraded: bool = False
    retryable: bool = False
    status_text: str = "已完成"
    error_message: str = ""


def build_runtime_kind() -> str:
    configured = (getattr(settings, "AI_AGENT_RUNTIME_MODE", "celery") or "celery").strip().lower()
    return configured if configured in {"celery", "legacy_thread", "inline"} else "celery"


def redis_reachable() -> bool:
    try:
        import redis

        client = redis.Redis.from_url(
            getattr(settings, "REDIS_URL", "redis://127.0.0.1:6379/0"),
            socket_connect_timeout=0.3,
            socket_timeout=0.3,
        )
        return bool(client.ping())
    except Exception:
        return False


def runtime_capability_flags() -> Dict[str, Any]:
    return get_runtime_health()


def feature_queue_name(feature_type: str) -> str:
    long_features = {"plan_replan", "retrieval_orchestrator", "vector_rag", "conversation", "study_report"}
    return settings.AI_AGENT_QUEUE_LONG if feature_type in long_features else settings.AI_AGENT_QUEUE_SHORT


def create_agent_run(
    *,
    user,
    feature_type: str,
    endpoint: str,
    request_payload: Dict[str, Any],
    request_hash: Optional[str] = None,
    conversation=None,
    parent_run=None,
    runtime_kind: Optional[str] = None,
    status: str = "queued",
    status_text: str = "排队中",
) -> AIAsyncRun:
    normalized_payload = normalize_payload(request_payload)
    return AIAsyncRun.objects.create(
        user=user,
        feature_type=feature_type,
        public_id=uuid4().hex[:24],
        runtime_kind=runtime_kind or build_runtime_kind(),
        queue_name=feature_queue_name(feature_type),
        endpoint=endpoint,
        request_hash=request_hash or make_cache_key(feature_type, normalized_payload, user_id=getattr(user, "id", None)),
        request_payload=normalized_payload,
        conversation=conversation,
        parent_run=parent_run,
        status=status,
        status_text=status_text,
        retryable=True,
    )


def reset_agent_run_for_retry(run: AIAsyncRun) -> AIAsyncRun:
    run.steps.all().delete()
    run.artifacts.all().delete()
    run.approvals.all().delete()
    run.current_agent = ""
    run.approval_state = "not_required"
    run.status = "queued"
    run.status_text = "排队中"
    run.error_message = ""
    run.latency_ms = 0
    run.degraded = False
    run.retryable = True
    run.result_payload = {}
    run.started_at = None
    run.finished_at = None
    run.save(
        update_fields=[
            "current_agent",
            "approval_state",
            "status",
            "status_text",
            "error_message",
            "latency_ms",
            "degraded",
            "retryable",
            "result_payload",
            "started_at",
            "finished_at",
            "updated_at",
        ]
    )
    return run


def serialize_agent_step(step: AIAgentStep) -> Dict[str, Any]:
    return {
        "id": step.id,
        "step_index": int(step.step_index or 0),
        "step_key": step.step_key,
        "step_kind": step.step_kind,
        "agent_name": step.agent_name,
        "title": step.title,
        "status": step.status,
        "summary": (step.output_payload or {}).get("summary", ""),
        "latency_ms": int(step.latency_ms or 0),
        "input_payload": step.input_payload or {},
        "output_payload": step.output_payload or {},
        "metadata": step.metadata or {},
        "error_message": step.error_message,
        "started_at": step.started_at.isoformat() if step.started_at else "",
        "finished_at": step.finished_at.isoformat() if step.finished_at else "",
    }


def serialize_agent_artifact(artifact: AIAgentArtifact) -> Dict[str, Any]:
    return {
        "id": artifact.id,
        "step_id": artifact.step_id,
        "artifact_type": artifact.artifact_type,
        "artifact_key": artifact.artifact_key,
        "title": artifact.title,
        "summary": artifact.summary,
        "payload": artifact.payload or {},
        "created_at": artifact.created_at.isoformat() if artifact.created_at else "",
    }


def serialize_agent_approval(approval: AIAgentApproval) -> Dict[str, Any]:
    return {
        "id": approval.id,
        "approval_key": approval.approval_key,
        "feature_type": approval.feature_type,
        "action_type": approval.action_type,
        "title": approval.title,
        "request_payload": approval.request_payload or {},
        "decision_payload": approval.decision_payload or {},
        "status": approval.status,
        "decision_note": approval.decision_note,
        "approved_at": approval.approved_at.isoformat() if approval.approved_at else "",
    }


def serialize_agent_run(run: AIAsyncRun, include_result: bool = True) -> Dict[str, Any]:
    payload = normalize_payload(run.result_payload if include_result else {})
    if payload:
        payload["runtime_summary"] = build_agent_runtime_summary(run, payload)
    step_count = run.steps.count()
    approval_required = run.approval_state == "pending"
    latest_approval = run.approvals.order_by("-id").first()
    runtime_summary = build_agent_runtime_summary(run, payload)
    runtime_summary.update(
        {
            "active_agent": run.current_agent,
            "step_count": step_count,
            "approval_required": approval_required,
            "resumable": run.status not in RUN_STATUS_TERMINAL,
            "stale": is_run_stale(run),
        }
    )
    return {
        "run_id": run.public_id,
        "feature_type": run.feature_type,
        "status": run.status,
        "status_text": runtime_summary.get("status_text", ""),
        "retryable": bool(run.retryable),
        "degraded": bool(run.degraded),
        "error_message": run.error_message,
        "latency_ms": int(run.latency_ms or 0),
        "runtime_kind": run.runtime_kind,
        "queue_name": run.queue_name,
        "current_agent": run.current_agent,
        "approval_state": run.approval_state,
        "retry_count": int(run.retry_count or 0),
        "stale": is_run_stale(run),
        "started_at": run.started_at.isoformat() if run.started_at else "",
        "finished_at": run.finished_at.isoformat() if run.finished_at else "",
        "runtime_summary": runtime_summary,
        "latest_approval": serialize_agent_approval(latest_approval) if latest_approval else None,
        "result": payload if include_result and run.status == "succeeded" else None,
    }


def build_agent_runtime_summary(run: AIAsyncRun, result_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = result_payload or {}
    summary = dict((payload.get("runtime_summary") or {}))
    if run.status == "queued":
        status_text = "排队中"
        description = "AI 正在排队准备执行。"
    elif run.status == "running":
        status_text = "运行中"
        description = "AI 正在执行多步骤智能体流程。"
    elif run.status == "waiting_approval":
        status_text = "等待审批"
        description = "本次智能体执行包含写操作，正在等待你的确认。"
    elif run.status == "cancelled":
        status_text = "已取消"
        description = "本次智能体执行已取消。"
    elif run.status == "succeeded":
        status_text = "已完成，当前结果为降级模式" if run.degraded else "已完成"
        description = "AI 智能体流程已完成。"
    else:
        status_text = "执行失败"
        description = run.error_message or "AI 智能体执行失败，请稍后重试。"
    summary.update(
        {
            "run_id": run.public_id,
            "status": run.status,
            "status_text": status_text,
            "summary": description if run.latency_ms <= 0 else f"{description} · {run.latency_ms}ms",
            "latency_ms": int(run.latency_ms or 0),
            "cache_hit": False,
            "degraded": bool(run.degraded),
            "degraded_reason": run.error_message if run.degraded else "",
            "retryable": bool(run.retryable),
            "retry_after": 0,
            "endpoint": run.endpoint or "",
            "active_agent": run.current_agent,
            "step_count": run.steps.count() if getattr(run, "pk", None) else 0,
            "approval_required": run.approval_state == "pending",
            "resumable": run.status not in RUN_STATUS_TERMINAL,
            "stale": is_run_stale(run),
        }
    )
    return summary


def is_run_stale(run: AIAsyncRun) -> bool:
    now = timezone.now()
    if run.status == "queued":
        reference = run.updated_at or run.created_at
        return bool(reference and reference <= now - timedelta(seconds=STALE_QUEUE_SECONDS))
    if run.status == "running":
        reference = run.started_at or run.updated_at or run.created_at
        return bool(reference and reference <= now - timedelta(seconds=STALE_RUNNING_SECONDS))
    return False


def list_stale_runs(*, feature_type: Optional[str] = None, limit: int = 100) -> List[AIAsyncRun]:
    now = timezone.now()
    queued_before = now - timedelta(seconds=STALE_QUEUE_SECONDS)
    running_before = now - timedelta(seconds=STALE_RUNNING_SECONDS)
    queryset = AIAsyncRun.objects.filter(
        Q(status="queued", updated_at__lte=queued_before)
        | Q(status="running", started_at__lte=running_before)
        | Q(status="running", started_at__isnull=True, updated_at__lte=running_before)
    ).order_by("updated_at", "created_at", "id")
    if feature_type:
        queryset = queryset.filter(feature_type=feature_type)
    return list(queryset[: max(int(limit or 0), 1)])


def recover_stale_runs(
    *,
    feature_type: Optional[str] = None,
    limit: int = 100,
    dispatch: bool = True,
) -> List[Dict[str, Any]]:
    recovered: List[Dict[str, Any]] = []
    for run in list_stale_runs(feature_type=feature_type, limit=limit):
        previous_status = run.status
        note = "检测到 stale run，已重新排队恢复。"
        create_artifact(
            run,
            artifact_type="runtime_event",
            artifact_key="stale_recovery",
            title="失活任务恢复",
            payload={"previous_status": previous_status, "stale": True, "note": note},
            summary=note,
        )
        run.status = "queued"
        run.status_text = "排队中"
        run.finished_at = None
        run.error_message = ""
        run.retryable = True
        run.save(update_fields=["status", "status_text", "finished_at", "error_message", "retryable", "updated_at"])
        if dispatch:
            dispatch_agent_run(run)
        recovered.append(
            {
                "run_id": run.public_id,
                "feature_type": run.feature_type,
                "previous_status": previous_status,
                "status": run.status,
                "queue_name": run.queue_name,
            }
        )
    return recovered


def _next_step_index(run: AIAsyncRun) -> int:
    last = run.steps.order_by("-step_index", "-id").only("step_index").first()
    return int(last.step_index or 0) + 1 if last else 1


@transaction.atomic
def start_step(
    run: AIAsyncRun,
    *,
    step_key: str,
    step_kind: str,
    agent_name: str,
    title: str,
    input_payload: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> AIAgentStep:
    step = AIAgentStep.objects.create(
        run=run,
        step_index=_next_step_index(run),
        step_key=fit_model_char_value(step_key, AIAgentStep._meta.get_field("step_key").max_length),
        step_kind=step_kind,
        agent_name=fit_model_char_value(agent_name, AIAgentStep._meta.get_field("agent_name").max_length),
        title=fit_model_char_value(title, AIAgentStep._meta.get_field("title").max_length),
        status="running",
        input_payload=normalize_payload(input_payload),
        metadata=normalize_payload(metadata),
        started_at=timezone.now(),
    )
    AIAsyncRun.objects.filter(id=run.id).update(current_agent=step.agent_name, status="running", status_text="运行中", started_at=run.started_at or timezone.now())
    run.current_agent = step.agent_name
    run.status = "running"
    run.status_text = "运行中"
    if not run.started_at:
        run.started_at = timezone.now()
    return step


def finish_step(step: AIAgentStep, result: AgentStepResult, started_at_value: float) -> AIAgentStep:
    latency_ms = int((monotonic() - started_at_value) * 1000)
    step.status = result.status
    step.output_payload = normalize_payload({"summary": result.summary, **(result.output_payload or {})})
    step.metadata = normalize_payload({**(step.metadata or {}), **(result.metadata or {})})
    step.error_message = str(result.error_message or "")[:2000]
    step.latency_ms = max(latency_ms, 0)
    step.finished_at = timezone.now()
    step.save(update_fields=["status", "output_payload", "metadata", "error_message", "latency_ms", "finished_at", "updated_at"])
    for artifact in result.artifacts:
        create_artifact(
            step.run,
            artifact_type=artifact.get("artifact_type", "debug"),
            payload=artifact.get("payload", {}),
            step=step,
            artifact_key=artifact.get("artifact_key", ""),
            title=artifact.get("title", ""),
            summary=artifact.get("summary", ""),
        )
    return step


def fail_step(step: AIAgentStep, error_message: str, started_at_value: float) -> AIAgentStep:
    return finish_step(
        step,
        AgentStepResult(status="failed", error_message=error_message, summary=str(error_message or "")),
        started_at_value,
    )


def create_artifact(
    run: AIAsyncRun,
    *,
    artifact_type: str,
    payload: Dict[str, Any],
    step: Optional[AIAgentStep] = None,
    artifact_key: str = "",
    title: str = "",
    summary: str = "",
) -> AIAgentArtifact:
    return AIAgentArtifact.objects.create(
        run=run,
        step=step,
        artifact_type=fit_model_char_value(artifact_type, AIAgentArtifact._meta.get_field("artifact_type").max_length),
        artifact_key=fit_model_char_value(artifact_key, AIAgentArtifact._meta.get_field("artifact_key").max_length),
        title=fit_model_char_value(title, AIAgentArtifact._meta.get_field("title").max_length),
        payload=normalize_payload(payload),
        summary=str(summary or "")[:2000],
    )


def create_approval(
    run: AIAsyncRun,
    *,
    feature_type: str,
    action_type: str,
    request_payload: Dict[str, Any],
    step: Optional[AIAgentStep] = None,
    title: str = "",
) -> AIAgentApproval:
    approval = AIAgentApproval.objects.create(
        run=run,
        step=step,
        approval_key=uuid4().hex[:24],
        feature_type=fit_model_char_value(feature_type, AIAgentApproval._meta.get_field("feature_type").max_length),
        action_type=fit_model_char_value(action_type, AIAgentApproval._meta.get_field("action_type").max_length),
        title=fit_model_char_value(title or "待确认操作", AIAgentApproval._meta.get_field("title").max_length),
        request_payload=normalize_payload(request_payload),
        status="pending",
    )
    AIAsyncRun.objects.filter(id=run.id).update(approval_state="pending", status="waiting_approval", status_text="等待审批")
    run.approval_state = "pending"
    run.status = "waiting_approval"
    run.status_text = "等待审批"
    return approval


def apply_approval_decision(run: AIAsyncRun, approval: AIAgentApproval, *, approved: bool, user=None, note: str = "") -> AIAgentApproval:
    approval.status = "approved" if approved else "rejected"
    approval.decision_note = str(note or "")[:2000]
    approval.decision_payload = normalize_payload({"approved": approved, "note": note})
    approval.approved_by = user
    approval.approved_at = timezone.now()
    approval.save(update_fields=["status", "decision_note", "decision_payload", "approved_by", "approved_at", "updated_at"])
    run.approval_state = approval.status
    run.status = "queued" if approved else "cancelled"
    run.status_text = "排队中" if approved else "已取消"
    run.retryable = bool(approved)
    if not approved:
        run.finished_at = timezone.now()
        run.current_agent = ""
    run.save(update_fields=["approval_state", "status", "status_text", "retryable", "finished_at", "current_agent", "updated_at"])
    return approval


def complete_run(run: AIAsyncRun, result: AgentRunResult, *, request_payload: Optional[Dict[str, Any]] = None) -> AIAsyncRun:
    payload = normalize_payload(result.result_payload)
    run.status = "succeeded"
    run.status_text = result.status_text
    run.degraded = bool(result.degraded)
    run.retryable = bool(result.retryable)
    run.error_message = str(result.error_message or "")[:2000]
    run.finished_at = timezone.now()
    if run.started_at:
        run.latency_ms = max(int((run.finished_at - run.started_at).total_seconds() * 1000), 0)
    payload["runtime_summary"] = build_agent_runtime_summary(run, payload)
    run.result_payload = payload
    run.save(
        update_fields=[
            "result_payload",
            "status",
            "status_text",
            "degraded",
            "retryable",
            "error_message",
            "finished_at",
            "latency_ms",
            "updated_at",
        ]
    )
    log_ai_request(
        user=run.user,
        feature_type=run.feature_type,
        endpoint=run.endpoint,
        request_payload=request_payload or run.request_payload,
        response_payload=payload,
        status="success",
        cache_key=run.request_hash,
        cache_hit=False,
        latency_ms=run.latency_ms,
        prompt_version=(payload.get("ai_strategy") or {}).get("prompt_version", ""),
        model_name=(payload.get("ai_strategy") or {}).get("model_name", ""),
    )
    return run


def fail_run(run: AIAsyncRun, error_message: str, *, request_payload: Optional[Dict[str, Any]] = None, retryable: bool = True) -> AIAsyncRun:
    run.status = "failed"
    run.status_text = "执行失败"
    run.error_message = str(error_message or "")[:2000]
    run.retryable = bool(retryable)
    run.finished_at = timezone.now()
    if run.started_at:
        run.latency_ms = max(int((run.finished_at - run.started_at).total_seconds() * 1000), 0)
    run.save(update_fields=["status", "status_text", "error_message", "retryable", "finished_at", "latency_ms", "updated_at"])
    log_ai_request(
        user=run.user,
        feature_type=run.feature_type,
        endpoint=run.endpoint,
        request_payload=request_payload or run.request_payload,
        response_payload={},
        status="failed",
        cache_key=run.request_hash,
        cache_hit=False,
        latency_ms=run.latency_ms,
        error_message=error_message,
    )
    return run


def execute_run_steps(
    run: AIAsyncRun,
    steps: Iterable[Callable[[AIAsyncRun], AgentStepResult]],
    *,
    finalize: Callable[[AIAsyncRun], AgentRunResult],
    request_payload: Optional[Dict[str, Any]] = None,
) -> AIAsyncRun:
    for func in steps:
        func(run)
        run.refresh_from_db()
        if run.status in {"failed", "cancelled", "waiting_approval"}:
            return run
    final_result = finalize(run)
    return complete_run(run, final_result, request_payload=request_payload)


def ensure_feature_runtime_payload(feature_type: str, payload: Dict[str, Any], run: Optional[AIAsyncRun] = None) -> Dict[str, Any]:
    normalized = normalize_feature_contract(feature_type, payload)
    if run:
        runtime_summary = normalized.get("runtime_summary") or {}
        runtime_summary.update(
            {
                "run_id": run.public_id,
                "active_agent": run.current_agent,
                "step_count": run.steps.count(),
                "approval_required": run.approval_state == "pending",
                "resumable": run.status not in RUN_STATUS_TERMINAL,
            }
        )
        normalized["runtime_summary"] = runtime_summary
    return normalized


def list_run_steps(user, run_id: str) -> List[Dict[str, Any]]:
    run = AIAsyncRun.objects.select_related("user").filter(user=user, public_id=run_id).first()
    if not run:
        return []
    return [serialize_agent_step(step) for step in run.steps.order_by("step_index", "id")]


def list_run_artifacts(user, run_id: str) -> List[Dict[str, Any]]:
    run = AIAsyncRun.objects.select_related("user").filter(user=user, public_id=run_id).first()
    if not run:
        return []
    return [serialize_agent_artifact(item) for item in run.artifacts.order_by("id")]


def get_run_for_user(user, run_id: str) -> Optional[AIAsyncRun]:
    queryset = AIAsyncRun.objects.filter(public_id=run_id)
    if user is not None:
        queryset = queryset.filter(user=user)
    return queryset.first()


def execute_inline_agent_run(
    *,
    user,
    feature_type: str,
    endpoint: str,
    request_payload: Dict[str, Any],
    conversation=None,
    parent_run=None,
    existing_run: Optional[AIAsyncRun] = None,
) -> tuple[AIAsyncRun, Dict[str, Any]]:
    from .runtime_registry import execute_registered_run, get_runtime_handler

    if not get_runtime_handler(feature_type):
        raise ValueError(f"runtime not registered for feature: {feature_type}")
    run = existing_run or create_agent_run(
        user=user,
        feature_type=feature_type,
        endpoint=endpoint,
        request_payload=request_payload,
        conversation=conversation,
        parent_run=parent_run,
        runtime_kind="inline",
        status="queued",
        status_text="排队中",
    )
    try:
        execute_registered_run(run)
    except Exception as exc:
        fail_run(run, str(exc), request_payload=request_payload, retryable=True)
        raise
    run.refresh_from_db()
    if run.status == "waiting_approval":
        return run, {}
    if run.status != "succeeded" and not run.result_payload:
        raise RuntimeError(run.error_message or "agent run did not complete successfully")
    return run, normalize_payload(run.result_payload)


def mark_run_cancelled(run: AIAsyncRun) -> AIAsyncRun:
    run.status = "cancelled"
    run.status_text = "已取消"
    run.finished_at = timezone.now()
    run.retryable = True
    run.save(update_fields=["status", "status_text", "finished_at", "retryable", "updated_at"])
    return run


def dispatch_agent_run(run: AIAsyncRun) -> AIAsyncRun:
    from .runtime_registry import execute_registered_run

    runtime_kind = (run.runtime_kind or build_runtime_kind()).strip().lower()
    if runtime_kind == "celery":
        assert_runtime_available_for_feature(run.feature_type)
    if run.feature_type == "plan_replan":
        from .async_runs import launch_async_plan_replan

        if runtime_kind == "celery":
            launch_async_plan_replan(run)
            return run
        execute_registered_run(run)
        run.refresh_from_db()
        return run
    if runtime_kind == "celery":
        from .tasks import execute_agent_run_task

        execute_agent_run_task.delay(run.public_id)
        return run
    execute_registered_run(run)
    run.refresh_from_db()
    return run


def wait_for_run_terminal_state(
    run: AIAsyncRun,
    *,
    timeout_ms: Optional[int] = None,
    include_waiting_approval: bool = True,
) -> AIAsyncRun:
    wait_timeout_ms = SYNC_WAIT_TIMEOUT_MS if timeout_ms is None else max(int(timeout_ms), 0)
    if wait_timeout_ms <= 0:
        run.refresh_from_db()
        return run

    deadline = monotonic() + (wait_timeout_ms / 1000.0)
    wait_statuses = set(RUN_STATUS_TERMINAL)
    if include_waiting_approval:
        wait_statuses.add("waiting_approval")

    while monotonic() < deadline:
        run.refresh_from_db()
        if run.status in wait_statuses:
            return run
        sleep(max(SYNC_WAIT_INTERVAL_MS, 25) / 1000.0)

    run.refresh_from_db()
    return run


def dispatch_agent_run_and_wait(
    run: AIAsyncRun,
    *,
    timeout_ms: Optional[int] = None,
) -> tuple[AIAsyncRun, Dict[str, Any]]:
    dispatch_agent_run(run)
    run = wait_for_run_terminal_state(run, timeout_ms=timeout_ms)
    if run.status == "failed":
        raise RuntimeError(run.error_message or "agent run failed")
    return run, normalize_payload(run.result_payload or {})


def resume_agent_run(run: AIAsyncRun) -> AIAsyncRun:
    if run.status == "waiting_approval" and run.approval_state == "pending":
        raise ValueError("run approval is still pending")
    if run.status in RUN_STATUS_TERMINAL and run.approval_state != "approved":
        raise ValueError("run already finished")
    if run.status == "running" and not is_run_stale(run):
        return run
    note = "检测到运行已失活，系统准备恢复执行。" if is_run_stale(run) else "恢复执行智能体任务。"
    create_artifact(
        run,
        artifact_type="runtime_event",
        artifact_key="resume",
        title="恢复执行",
        payload={"stale": is_run_stale(run), "status": run.status, "note": note},
        summary=note,
    )
    run.status = "queued"
    run.status_text = "排队中"
    run.finished_at = None
    run.error_message = ""
    run.retryable = True
    run.save(update_fields=["status", "status_text", "finished_at", "error_message", "retryable", "updated_at"])
    return dispatch_agent_run(run)


def maybe_require_approval(action_type: str) -> bool:
    if not getattr(settings, "AI_AGENT_REQUIRE_APPROVAL_FOR_MUTATIONS", True):
        return False
    return action_type in APPROVAL_MUTATING_ACTIONS


def build_step_trace_payload(run: AIAsyncRun) -> Dict[str, Any]:
    steps = [serialize_agent_step(step) for step in run.steps.order_by("step_index", "id")]
    return {
        "run_id": run.public_id,
        "step_count": len(steps),
        "steps": steps,
        "artifacts": [
            {
                "artifact_type": item.artifact_type,
                "artifact_key": item.artifact_key,
                "title": item.title,
                "summary": item.summary,
            }
            for item in run.artifacts.order_by("id")
        ],
    }
