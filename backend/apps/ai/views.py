from datetime import datetime

from rest_framework.views import APIView
from django.core.cache import cache
from django.utils import timezone

from common.permissions import IsWxAuthenticated
from common.responses import error_response, success_response

from .compat import build_runtime_capabilities
from .async_runs import (
    get_or_create_plan_replan_run,
    get_plan_replan_run_or_raise,
    launch_async_plan_replan,
    serialize_plan_replan_run,
)
from .agent_runtime import (
    apply_approval_decision,
    dispatch_agent_run,
    dispatch_agent_run_and_wait,
    reset_agent_run_for_retry,
    get_run_for_user,
    list_run_artifacts,
    list_run_steps,
    mark_run_cancelled,
    resume_agent_run,
    runtime_capability_flags,
    serialize_agent_run,
    execute_inline_agent_run,
)
from .runtime_registry import get_runtime_handler
from .langchain_runtime import build_langchain_capabilities
from .conversation_services import (
    ask_conversation,
    create_ai_feedback,
    create_conversation,
    get_conversation_detail,
    list_conversations,
)
from .evidence import attach_feature_evidence
from .evaluations import build_eval_summary, list_eval_cases, list_eval_runs, run_evaluations_for_user
from .graphs.grammar_tutor import build_grammar_tutor_answer, build_grammar_tutor_detail
from .graphs.study_coach import build_study_coach_detail
from .graphs.vocab_tutor import build_word_tutor_detail
from .graphs.wrong_word_review import build_wrong_words_review_detail
from .learning_assistant import (
    build_grammar_guide,
    build_multi_agent_brief,
    correct_writing,
    evaluate_rag_recall,
    evaluate_translation,
    generate_writing_prompt,
    list_scenario_templates,
    run_scenario_dialogue,
    summarize_ai_quality,
)
from .learning_reports import generate_study_report, list_study_reports
from .mcp.server_http import build_mcp_blueprint, call_mcp_tool_with_guard, read_mcp_resource
from .observability import build_observability_summary, run_observed_feature
from .profile_memory import get_or_refresh_profile_memory, refresh_profile_memory, serialize_profile_memory
from .rag.chroma_runtime import get_chroma_runtime
from .rag.index_status import build_rag_index_status
from .rag.sync_service import sync_rag_index
from .response_contracts import normalize_feature_contract
from .serializers import (
    AIConversationAskSerializer,
    AIConversationCreateSerializer,
    AIEvaluationReplaySerializer,
    AIEvaluationRunSerializer,
    AIFeedbackSerializer,
    AIGrammarTutorSerializer,
    AIPlanReplanSerializer,
    AIProfileRefreshSerializer,
    AIRAGRecallEvaluateSerializer,
    AIRAGIndexSyncSerializer,
    AIRetrievalOrchestratorSerializer,
    AIRunActionSerializer,
    AIRunApprovalSerializer,
    AIRunResumeSerializer,
    AIScenarioDialogueSerializer,
    AIVectorRAGSearchSerializer,
    AIRAGSearchSerializer,
    AIReportGenerateSerializer,
    AIStudyCoachSerializer,
    AITranslationEvaluateSerializer,
    AIWordExplainSerializer,
    AIWritingCorrectSerializer,
    AIWritingPromptSerializer,
    AIWrongWordsReviewSerializer,
    AIMCPToolCallSerializer,
    AIMCPResourceReadSerializer,
)


class AICapabilityView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        cache_key = "ai:capabilities_snapshot:v2"
        cached = cache.get(cache_key)
        if cached:
            payload = dict(cached)
            cached_at = payload.get("capabilities_cached_at", "")
            if cached_at:
                try:
                    snapshot_time = datetime.fromisoformat(cached_at)
                    payload["health_snapshot_age_ms"] = max(int((timezone.now().replace(tzinfo=None) - snapshot_time).total_seconds() * 1000), 0)
                except Exception:
                    payload["health_snapshot_age_ms"] = int(payload.get("health_snapshot_age_ms") or 0)
            payload["deep_health_stale"] = False
            return success_response(payload)

        runtime = build_runtime_capabilities()
        langchain_caps = build_langchain_capabilities()
        mcp_blueprint = build_mcp_blueprint()
        runtime_health = runtime_capability_flags()
        rag_runtime = get_chroma_runtime()
        payload = {
            **runtime,
            **runtime_health,
            **langchain_caps,
            "mcp_stdio_available": mcp_blueprint.get("mcp_stdio_available", False),
            "mcp_stdio_command": mcp_blueprint.get("stdio_command", ""),
            "mcp_transport_modes": mcp_blueprint.get("transport_modes", []),
            "mcp_tool_count": mcp_blueprint.get("tool_count", 0),
            "mcp_resource_count": mcp_blueprint.get("resource_count", 0),
            "mcp_prompt_count": mcp_blueprint.get("prompt_count", 0),
            "rag_runtime": rag_runtime,
            "mcp_blueprint": mcp_blueprint,
            "capabilities_cached_at": timezone.now().replace(microsecond=0).isoformat(),
            "health_snapshot_age_ms": int(runtime_health.get("health_snapshot_age_ms") or 0),
            "deep_health_stale": False,
            "ai_modules": {
                "profile_memory": True,
                "plan_history": True,
                "evaluation": True,
                "trace_timeline": True,
                "vector_runtime": True,
                "personalized_rag": True,
            },
        }
        cache.set(cache_key, payload, 6)
        return success_response(payload)


def _finalize_feature_payload(feature_type, payload):
    attach_feature_evidence(feature_type, payload)
    normalize_feature_contract(feature_type, payload)
    return payload


def _run_runtime_feature_with_sync_window(*, user, feature_type, endpoint, request_payload, conversation=None, timeout_ms=None):
    from .agent_runtime import AgentRunResult, complete_run, create_agent_run, ensure_feature_runtime_payload, serialize_agent_run

    run = create_agent_run(
        user=user,
        feature_type=feature_type,
        endpoint=endpoint,
        request_payload=request_payload,
        conversation=conversation,
        runtime_kind="celery",
        status="queued",
        status_text="排队中",
    )
    try:
        run, data = dispatch_agent_run_and_wait(run, timeout_ms=timeout_ms)
        if run.status == "succeeded":
            return run, data, False
        return run, serialize_agent_run(run), True
    except RuntimeError as exc:
        if feature_type == "vector_rag":
            from .learning_assistant import run_vector_rag_search

            degraded_payload = run_vector_rag_search(
                str(request_payload.get("query") or "").strip(),
                int(request_payload.get("limit") or 8),
                retrieval_mode=str(request_payload.get("retrieval_mode") or "hybrid").strip() or "hybrid",
                user=user,
            )
            degraded_payload["degraded_notice"] = {
                "enabled": True,
                "reason": str(exc),
                "message": "标准 Agent 运行时不可用，已自动回退到可用的向量检索链路。",
            }
            degraded_payload = ensure_feature_runtime_payload("vector_rag", degraded_payload, run)
            run = complete_run(
                run,
                AgentRunResult(
                    feature_type="vector_rag",
                    result_payload=degraded_payload,
                    degraded=True,
                    retryable=True,
                    status_text="已完成，当前结果为降级模式",
                    error_message=str(exc),
                ),
                request_payload=request_payload,
            )
            return run, run.result_payload or degraded_payload, False
        if feature_type == "plan_replan":
            from .graphs.plan_replanner import build_fast_plan_replan_detail

            degraded_payload = build_fast_plan_replan_detail(user, int(request_payload.get("trend_days") or 7))
            degraded_payload["degraded_notice"] = {
                "enabled": True,
                "reason": str(exc),
                "message": "标准 Agent 运行时不可用，已自动回退到保底 AI 计划。",
            }
            degraded_payload = ensure_feature_runtime_payload("plan_replan", degraded_payload, run)
            run = complete_run(
                run,
                AgentRunResult(
                    feature_type="plan_replan",
                    result_payload=degraded_payload,
                    degraded=True,
                    retryable=True,
                    status_text="已完成，当前结果为降级模式",
                    error_message=str(exc),
                ),
                request_payload=request_payload,
            )
            return run, run.result_payload or degraded_payload, False
        if feature_type == "conversation":
            data = ask_conversation(
                user,
                str(request_payload.get("question") or "").strip(),
                request_payload.get("conversation_id"),
                str(request_payload.get("feature_type") or "rag").strip() or "rag",
            )
            data["degraded_notice"] = {
                "enabled": True,
                "reason": str(exc),
                "message": "标准 Agent 运行时不可用，已自动回退到同步对话链路。",
            }
            data = ensure_feature_runtime_payload("conversation", data, run)
            run = complete_run(
                run,
                AgentRunResult(
                    feature_type="conversation",
                    result_payload=data,
                    degraded=True,
                    retryable=True,
                    status_text="已完成，当前结果为降级模式",
                    error_message=str(exc),
                ),
                request_payload=request_payload,
            )
            return run, run.result_payload or data, False
        raise


class AIRAGIndexStatusView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(build_rag_index_status())


class AIRAGIndexSyncView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIRAGIndexSyncSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            result = sync_rag_index(
                limit=serializer.validated_data.get("limit"),
                batch_size=serializer.validated_data.get("batch_size", 64),
                delete_missing=serializer.validated_data.get("delete_missing", False),
            )
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(result.to_dict(), message="rag index sync finished")


class AIGrammarTutorView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIGrammarTutorSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        sentence = serializer.validated_data["sentence"]
        question = serializer.validated_data.get("question", "").strip()
        payload = {
            "sentence": sentence,
            "question": question,
        }

        try:
            run, data = execute_inline_agent_run(
                user=request.user,
                feature_type="grammar_tutor",
                endpoint="/api/v1/ai/grammar/tutor",
                request_payload=payload,
            )
            data = _finalize_feature_payload("grammar_tutor", data)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIWordTutorView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIWordExplainSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        payload = {"word_id": serializer.validated_data["word_id"]}
        try:
            run, data = execute_inline_agent_run(
                user=request.user,
                feature_type="word_tutor",
                endpoint="/api/v1/ai/words/explain",
                request_payload=payload,
            )
            data = _finalize_feature_payload("word_tutor", data)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIStudyCoachView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIStudyCoachSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        payload = {
            "trend_days": serializer.validated_data.get("trend_days", 7),
            "force_refresh": serializer.validated_data.get("force_refresh", False),
        }
        try:
            run, data = execute_inline_agent_run(
                user=request.user,
                feature_type="study_coach",
                endpoint="/api/v1/ai/study-coach",
                request_payload=payload,
            )
            data = _finalize_feature_payload("study_coach", data)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIPlanReplanView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIPlanReplanSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        payload = {
            "trend_days": serializer.validated_data.get("trend_days", 7),
            "force_refresh": serializer.validated_data.get("force_refresh", False),
            "prefer_fast": False,
        }
        run, created = get_or_create_plan_replan_run(request.user, payload)
        if created:
            launch_async_plan_replan(run)
            run = get_plan_replan_run_or_raise(request.user, run.public_id)
        serialized = serialize_plan_replan_run(run)
        message = "plan replan started" if created else "plan replan run ready"
        return success_response(serialized, message=message)


class AIPlanReplanRunDetailView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request, run_id):
        run = get_plan_replan_run_or_raise(request.user, run_id)
        if not run:
            return error_response("run not found", code=40404, status_code=404)
        return success_response(serialize_plan_replan_run(run))


class AIRunDetailView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request, run_id):
        run = get_run_for_user(request.user, run_id)
        if not run:
            return error_response("run not found", code=40404, status_code=404)
        return success_response(serialize_agent_run(run))


class AIRunStepsView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request, run_id):
        run = get_run_for_user(request.user, run_id)
        if not run:
            return error_response("run not found", code=40404, status_code=404)
        return success_response({"run_id": run.public_id, "steps": list_run_steps(request.user, run_id)})


class AIRunArtifactsView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request, run_id):
        run = get_run_for_user(request.user, run_id)
        if not run:
            return error_response("run not found", code=40404, status_code=404)
        return success_response({"run_id": run.public_id, "artifacts": list_run_artifacts(request.user, run_id)})


class AIRunRetryView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request, run_id):
        serializer = AIRunActionSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        run = get_run_for_user(request.user, run_id)
        if not run:
            return error_response("run not found", code=40404, status_code=404)
        if not run.retryable:
            return error_response("run not retryable", code=40004)
        if run.feature_type == "plan_replan":
            run.retry_count = int(run.retry_count or 0) + 1
            run = reset_agent_run_for_retry(run)
            run.retry_count = 1 if run.retry_count <= 0 else run.retry_count
            run.save(update_fields=["retry_count", "updated_at"])
            launch_async_plan_replan(run)
            run.refresh_from_db()
            return success_response(serialize_agent_run(run), message="run retried")
        if run.feature_type in {"rag_search", "vector_rag", "retrieval_orchestrator"}:
            request_payload = dict(run.request_payload or {})
            next_retry_count = int(run.retry_count or 0) + 1
            run = reset_agent_run_for_retry(run)
            run.retry_count = next_retry_count
            run.save(update_fields=["retry_count", "updated_at"])
            _, _data = execute_inline_agent_run(
                user=request.user,
                feature_type=run.feature_type,
                endpoint=run.endpoint,
                request_payload=request_payload,
                conversation=run.conversation,
                parent_run=run.parent_run,
                existing_run=run,
            )
            run.refresh_from_db()
            return success_response(serialize_agent_run(run), message="run retried")
        if get_runtime_handler(run.feature_type):
            next_retry_count = int(run.retry_count or 0) + 1
            request_payload = dict(run.request_payload or {})
            run = reset_agent_run_for_retry(run)
            run.retry_count = next_retry_count
            run.save(update_fields=["retry_count", "updated_at"])
            dispatch_agent_run(run)
            run.refresh_from_db()
            return success_response(serialize_agent_run(run), message="run retried")
        return error_response("retry not supported for this feature", code=40005)


class AIRunResumeView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request, run_id):
        serializer = AIRunResumeSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        run = get_run_for_user(request.user, run_id)
        if not run:
            return error_response("run not found", code=40404, status_code=404)
        try:
            run = resume_agent_run(run)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response(serialize_agent_run(run), message="run resumed")


class AIRunCancelView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request, run_id):
        serializer = AIRunActionSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        run = get_run_for_user(request.user, run_id)
        if not run:
            return error_response("run not found", code=40404, status_code=404)
        if run.status in {"succeeded", "failed", "cancelled"}:
            return success_response(serialize_agent_run(run), message="run already finished")
        run = mark_run_cancelled(run)
        return success_response(serialize_agent_run(run), message="run cancelled")


class AIRunApproveView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request, run_id):
        serializer = AIRunApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        run = get_run_for_user(request.user, run_id)
        if not run:
            return error_response("run not found", code=40404, status_code=404)
        approval = run.approvals.filter(status="pending").order_by("-id").first()
        if not approval:
            return error_response("approval not found", code=40404, status_code=404)
        approved = serializer.validated_data.get("approved", False)
        apply_approval_decision(run, approval, approved=approved, user=request.user, note=serializer.validated_data.get("note", ""))
        if approved:
            dispatch_agent_run(run)
            run.refresh_from_db()
        return success_response(serialize_agent_run(run), message="approval applied")


class AIRetrievalOrchestratorView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIRetrievalOrchestratorSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        payload = {
            "query": serializer.validated_data["query"],
            "limit": serializer.validated_data.get("limit", 6),
        }
        try:
            run, data, pending = _run_runtime_feature_with_sync_window(
                user=request.user,
                feature_type="retrieval_orchestrator",
                endpoint="/api/v1/ai/agents/retrieval-orchestrator",
                request_payload=payload,
            )
            if pending:
                return success_response(data, message="run queued")
            data = _finalize_feature_payload("retrieval_orchestrator", data)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIWrongWordsReviewView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIWrongWordsReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        payload = {"limit": serializer.validated_data.get("limit", 12)}
        try:
            run, data = execute_inline_agent_run(
                user=request.user,
                feature_type="wrong_words_review",
                endpoint="/api/v1/ai/wrong-words/review",
                request_payload=payload,
            )
            data = _finalize_feature_payload("wrong_words_review", data)
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIMCPToolCallView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIMCPToolCallSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        payload = {
            "tool_name": serializer.validated_data["tool_name"],
            "args": serializer.validated_data.get("args", {}),
        }
        try:
            run, data = execute_inline_agent_run(
                user=request.user,
                feature_type="mcp_tool_call",
                endpoint="/api/v1/ai/mcp/tools/call",
                request_payload=payload,
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        result = data.get("result") if isinstance(data, dict) else {}
        runtime_summary = data.get("runtime_summary", {}) if isinstance(data, dict) else {}
        if run.status == "waiting_approval":
            result = call_mcp_tool_with_guard(
                request.user,
                payload["tool_name"],
                payload["args"],
                run=run,
                feature_type="mcp_tool_call",
            )
            runtime_summary = serialize_agent_run(run, include_result=False).get("runtime_summary", {})
        return success_response(
            {
                "tool_name": payload["tool_name"],
                "run_id": run.public_id,
                "result": result,
                "runtime_summary": runtime_summary,
            }
        )


class AIMCPResourceReadView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIMCPResourceReadSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            result = read_mcp_resource(request.user, serializer.validated_data["resource_uri"])
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(result)


class AIWritingCorrectView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIWritingCorrectSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        payload = {
            "text": serializer.validated_data["text"],
            "level": serializer.validated_data.get("level", "cet4"),
        }
        try:
            run, data = execute_inline_agent_run(
                user=request.user,
                feature_type="writing_correct",
                endpoint="/api/v1/ai/writing/correct",
                request_payload=payload,
            )
            data = _finalize_feature_payload("writing_correct", data)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIWritingPromptView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIWritingPromptSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        payload = {
            "level": serializer.validated_data.get("level", "cet4") or "cet4",
            "topic": serializer.validated_data.get("topic", ""),
            "genre": serializer.validated_data.get("genre", "essay") or "essay",
        }
        try:
            run, data = execute_inline_agent_run(
                user=request.user,
                feature_type="writing_prompt",
                endpoint="/api/v1/ai/writing/prompt",
                request_payload=payload,
            )
            data = _finalize_feature_payload("writing_prompt", data)
        except ValueError as exc:
            return error_response(str(exc), code=42901, status_code=429)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AITranslationEvaluateView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AITranslationEvaluateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        payload = {
            "source_text": serializer.validated_data["source_text"],
            "user_translation": serializer.validated_data.get("user_translation", ""),
            "direction": serializer.validated_data.get("direction", "auto"),
        }
        try:
            run, data = execute_inline_agent_run(
                user=request.user,
                feature_type="translation_evaluate",
                endpoint="/api/v1/ai/translation/evaluate",
                request_payload=payload,
            )
            data = _finalize_feature_payload("translation_evaluate", data)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIGrammarGuideView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        try:
            run, data = execute_inline_agent_run(
                user=request.user,
                feature_type="grammar_guide",
                endpoint="/api/v1/ai/grammar/guide",
                request_payload={},
            )
            data = _finalize_feature_payload("grammar_guide", data)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIRAGSearchView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIRAGSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        payload = {
            "query": serializer.validated_data["query"],
            "limit": serializer.validated_data.get("limit", 6),
        }
        try:
            run, data, pending = _run_runtime_feature_with_sync_window(
                user=request.user,
                feature_type="rag_search",
                endpoint="/api/v1/ai/rag/search",
                request_payload=payload,
            )
            if pending:
                return success_response(data, message="run queued")
            data = _finalize_feature_payload("rag_search", data)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIVectorRAGSearchView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIVectorRAGSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        payload = {
            "query": serializer.validated_data["query"],
            "limit": serializer.validated_data.get("limit", 8),
            "retrieval_mode": serializer.validated_data.get("retrieval_mode", "hybrid"),
        }
        try:
            run, data, pending = _run_runtime_feature_with_sync_window(
                user=request.user,
                feature_type="vector_rag",
                endpoint="/api/v1/ai/rag/vector-search",
                request_payload=payload,
            )
            if pending:
                return success_response(data, message="run queued")
            data = _finalize_feature_payload("vector_rag", data)
        except ValueError as exc:
            return error_response(str(exc), code=42901, status_code=429)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIRAGRecallEvaluateView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIRAGRecallEvaluateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        payload = {
            "query": serializer.validated_data["query"],
            "expected_keywords": serializer.validated_data.get("expected_keywords", []),
            "preferred_source_type": serializer.validated_data.get("preferred_source_type", ""),
            "limit": serializer.validated_data.get("limit", 6),
        }
        try:
            data = run_observed_feature(
                user=request.user,
                feature_type="rag_recall_eval",
                endpoint="/api/v1/ai/rag/recall-evaluate",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "rag_recall_eval",
                    evaluate_rag_recall(
                        payload["query"],
                        payload["expected_keywords"],
                        payload["preferred_source_type"],
                        payload["limit"],
                        user=request.user,
                    ),
                ),
                use_cache=True,
            )
        except ValueError as exc:
            return error_response(str(exc), code=42901, status_code=429)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


class AIScenarioTemplateListView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response({"list": list_scenario_templates()})


class AIScenarioDialogueView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIScenarioDialogueSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        payload = {
            "scenario": serializer.validated_data.get("scenario", "daily"),
            "user_message": serializer.validated_data["user_message"],
            "conversation_id": serializer.validated_data.get("conversation_id"),
        }
        try:
            run, data = execute_inline_agent_run(
                user=request.user,
                feature_type="scenario_dialogue",
                endpoint="/api/v1/ai/scenario/dialogue",
                request_payload=payload,
            )
            data = _finalize_feature_payload("scenario_dialogue", data)
        except ValueError as exc:
            return error_response(str(exc), code=42901, status_code=429)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIMultiAgentBriefView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        data = run_observed_feature(
            user=request.user,
            feature_type="multi_agent_brief",
            endpoint="/api/v1/ai/agents/brief",
            request_payload={},
            producer=lambda: _finalize_feature_payload("multi_agent_brief", build_multi_agent_brief(request.user)),
            use_cache=True,
        )
        return success_response(data)


class AIQualityView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(summarize_ai_quality(request.user))


class AIObservabilityView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(build_observability_summary(request.user))


class AIProfileMemoryView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        memory = get_or_refresh_profile_memory(request.user)
        return success_response(serialize_profile_memory(memory))

    def post(self, request):
        serializer = AIProfileRefreshSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        memory = refresh_profile_memory(request.user, source=serializer.validated_data.get("source", "manual"))
        return success_response(serialize_profile_memory(memory), message="profile memory refreshed")


class AIEvaluationView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        case_type = request.query_params.get("case_type", "")
        failed_only = request.query_params.get("failed_only", "").lower() in {"1", "true", "yes"}
        limit = request.query_params.get("limit", 10)
        return success_response(
            {
                "cases": list_eval_cases(case_type=case_type),
                "runs": list_eval_runs(case_type=case_type, failed_only=failed_only, limit=limit),
                "summary": build_eval_summary(case_type=case_type, limit=limit),
            }
        )

    def post(self, request):
        serializer = AIEvaluationRunSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        runs = run_evaluations_for_user(
            request.user,
            case_id=serializer.validated_data.get("case_id"),
            case_type=serializer.validated_data.get("case_type", ""),
            replay_failed_only=serializer.validated_data.get("replay_failed_only", False),
            limit=serializer.validated_data.get("limit", 5),
        )
        return success_response({"runs": runs}, message="evaluation finished")


class AIEvaluationRunDetailView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request, run_id):
        from .evaluations import get_eval_run_detail

        try:
            return success_response(get_eval_run_detail(request.user, run_id))
        except ValueError as exc:
            return error_response(str(exc), code=40004)


class AIEvaluationRunReplayView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request, run_id):
        from .evaluations import replay_eval_run

        serializer = AIEvaluationReplaySerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            run = replay_eval_run(
                request.user,
                run_id,
                override_request_payload=serializer.validated_data.get("request_payload", {}),
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        return success_response(run, message="evaluation replay finished")


class AIMCPManifestView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(build_mcp_blueprint())


class AIMCPResourcesView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response({"resources": build_mcp_blueprint().get("resources", [])})


class AIMCPPromptsView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response({"prompts": build_mcp_blueprint().get("prompts", [])})


class AIStudyReportView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        include_compare = request.query_params.get("include_compare", "").lower() in {"1", "true", "yes"}
        data = {
            "list": list_study_reports(
                request.user,
                request.query_params.get("report_type", ""),
                request.query_params.get("limit", 10),
                include_compare=include_compare,
            ),
            "history_compare_enabled": include_compare,
        }
        for item in data["list"]:
            _finalize_feature_payload("study_report", item)
        return success_response(data)

    def post(self, request):
        serializer = AIReportGenerateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            payload = {"report_type": serializer.validated_data.get("report_type", "weekly")}
            run, data, pending = _run_runtime_feature_with_sync_window(
                user=request.user,
                feature_type="study_report",
                endpoint="/api/v1/ai/reports",
                request_payload=payload,
            )
            if pending:
                return success_response(data, message="run queued")
            data = _finalize_feature_payload("study_report", data)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response({"run_id": run.public_id, **data})


class AIConversationListCreateView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        return success_response(
            {
                "list": list_conversations(
                    request.user,
                    request.query_params.get("feature_type", ""),
                    request.query_params.get("limit", 20),
                )
            }
        )

    def post(self, request):
        serializer = AIConversationCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        return success_response(
            create_conversation(
                request.user,
                serializer.validated_data.get("feature_type", "rag") or "rag",
                serializer.validated_data.get("title", ""),
                serializer.validated_data.get("context", {}),
            )
        )


class AIConversationDetailView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request, conversation_id):
        return success_response(get_conversation_detail(request.user, conversation_id))


class AIConversationAskView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIConversationAskSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            data = ask_conversation(
                request.user,
                serializer.validated_data["question"],
                serializer.validated_data.get("conversation_id"),
                serializer.validated_data.get("feature_type", "rag") or "rag",
            )
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


class AIFeedbackView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIFeedbackSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        return success_response(create_ai_feedback(request.user, serializer.validated_data))
