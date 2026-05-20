from __future__ import annotations

from time import monotonic
from typing import Any, Dict, Tuple
from uuid import uuid4

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from datetime import timedelta

from .agent_runtime import build_agent_runtime_summary, build_runtime_kind, create_agent_run, get_run_for_user, serialize_agent_run
from .compat import build_runtime_capabilities
from .graphs.plan_replanner import build_emergency_replan, build_plan_replan_detail
from .models import AIAsyncRun
from .observability import log_ai_request, make_cache_key, normalize_payload
from .response_contracts import normalize_feature_contract
from .runtime_registry import execute_registered_run
from .tasks import execute_agent_run_task


PLAN_REPLAN_ENDPOINT = "/api/v1/ai/plans/replan"
STALE_QUEUE_SECONDS = 30
STALE_RUNNING_SECONDS = 180


def _finalize_feature_payload(feature_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    from .evidence import attach_feature_evidence

    attach_feature_evidence(feature_type, payload)
    normalize_feature_contract(feature_type, payload)
    return payload


def _build_plan_replan_fallback(trend_days: int, error_message: str) -> Dict[str, Any]:
    return _finalize_feature_payload(
        "plan_replan",
        {
            **build_emergency_replan(trend_days),
            "knowledge": {},
            "tool_trace": [],
            "agent_flow": {
                "title": "AI 重规划学习计划 Emergency API Fallback",
                "inputs": [],
                "steps": [{"name": "fallback", "detail": "主请求异常，接口已自动返回应急结果。"}],
                "decision_highlights": ["已避免请求失败，先保证页面有结果。"],
            },
            "context_bundle": {},
            "profile_memory": {},
            "multi_agent": {"roles": [], "handoffs": [], "selected_tools": []},
            "langchain_trace": [],
            "runtime_stack": {
                "stack_name": "plan_replan_async_fallback",
                "fallback": True,
            },
            "ai_strategy": {
                "engine": "async_api_fallback",
                "rag_enabled": False,
                "ai_enabled": False,
                "prompt_version": "plan_replan_v2_multi_agent",
                "model_name": "",
            },
            "runtime": build_runtime_capabilities(),
            "degraded_notice": {
                "enabled": True,
                "reason": error_message,
                "message": "AI 自适应计划主链路异常，已自动返回保底自适应计划。",
            },
        },
    )


def _build_runtime_summary(run: AIAsyncRun, result_payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return build_agent_runtime_summary(run, result_payload)


def _serialize_async_run(run: AIAsyncRun, include_result: bool = True) -> Dict[str, Any]:
    return serialize_agent_run(run, include_result=include_result)


def _update_run_status(run_id: int, **fields) -> AIAsyncRun:
    AIAsyncRun.objects.filter(id=run_id).update(**fields, updated_at=timezone.now())
    return AIAsyncRun.objects.get(id=run_id)


def _execute_plan_replan_run(run_id: int) -> None:
    close_old_connections()
    started_at = monotonic()
    try:
        run = AIAsyncRun.objects.select_related("user").get(id=run_id)
        execute_registered_run(run)
    except Exception as exc:
        close_old_connections()
        run = AIAsyncRun.objects.select_related("user").get(id=run_id)
        payload = dict(run.request_payload or {})
        trend_days = int(payload.get("trend_days") or 7)
        fallback = _build_plan_replan_fallback(trend_days, str(exc))
        latency_ms = int((monotonic() - started_at) * 1000)
        fallback["runtime_summary"] = {
            **(fallback.get("runtime_summary") or {}),
            "run_id": run.public_id,
            "status": "succeeded",
        }
        _update_run_status(
            run_id,
            status="succeeded",
            status_text="已完成，当前结果为降级模式",
            result_payload=normalize_payload(fallback),
            latency_ms=latency_ms,
            degraded=True,
            retryable=True,
            finished_at=timezone.now(),
            error_message=str(exc)[:2000],
        )
        log_ai_request(
            user=run.user,
            feature_type="plan_replan",
            endpoint=PLAN_REPLAN_ENDPOINT,
            request_payload=payload,
            response_payload=fallback,
            status="success",
            cache_key=run.request_hash,
            cache_hit=False,
            latency_ms=latency_ms,
            error_message=str(exc),
        )
    finally:
        close_old_connections()


def launch_async_plan_replan(run: AIAsyncRun) -> None:
    runtime_kind = build_runtime_kind()
    if runtime_kind == "celery":
        execute_agent_run_task.delay(run.public_id)
        return
    _execute_plan_replan_run(run.id)


def _is_stale_async_run(run: AIAsyncRun) -> bool:
    now = timezone.now()
    if run.status == "queued":
        return run.created_at <= now - timedelta(seconds=STALE_QUEUE_SECONDS)
    if run.status == "running":
        reference = run.started_at or run.updated_at or run.created_at
        return reference <= now - timedelta(seconds=STALE_RUNNING_SECONDS)
    return False


def get_or_create_plan_replan_run(user, payload: Dict[str, Any]) -> Tuple[AIAsyncRun, bool]:
    normalized_payload = normalize_payload(
        {
            "trend_days": int(payload.get("trend_days") or 7),
            "force_refresh": bool(payload.get("force_refresh", False)),
            "prefer_fast": False,
        }
    )
    request_hash = make_cache_key("plan_replan_async", normalized_payload, user_id=getattr(user, "id", None))
    active = (
        AIAsyncRun.objects.filter(
            user=user,
            feature_type="plan_replan",
            request_hash=request_hash,
            status__in=["queued", "running"],
        )
        .order_by("-id")
        .first()
    )
    if active:
        if _is_stale_async_run(active):
            active.status = "failed"
            active.status_text = "任务已失活"
            active.retryable = True
            active.error_message = "检测到旧的异步任务已失活，系统已自动重建任务。"
            active.finished_at = timezone.now()
            active.save(update_fields=["status", "status_text", "retryable", "error_message", "finished_at", "updated_at"])
        else:
            if active.status == "queued" and not active.started_at:
                launch_async_plan_replan(active)
            return active, False
    if not normalized_payload.get("force_refresh"):
        existing = (
            AIAsyncRun.objects.filter(
                user=user,
                feature_type="plan_replan",
                request_hash=request_hash,
                status="succeeded",
            )
            .order_by("-id")
            .first()
        )
        if existing:
            return existing, False
    run = create_agent_run(
        user=user,
        feature_type="plan_replan",
        endpoint=PLAN_REPLAN_ENDPOINT,
        request_payload=normalized_payload,
        request_hash=request_hash,
        runtime_kind=build_runtime_kind(),
        status="queued",
        status_text="排队中",
    )
    return run, True


def get_plan_replan_run_or_raise(user, public_id: str) -> AIAsyncRun | None:
    run = get_run_for_user(user, public_id)
    if run and run.feature_type == "plan_replan":
        return run
    return None


def serialize_plan_replan_run(run: AIAsyncRun) -> Dict[str, Any]:
    return _serialize_async_run(run)
