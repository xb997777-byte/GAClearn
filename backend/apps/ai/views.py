from rest_framework.views import APIView

from common.permissions import IsWxAuthenticated
from common.responses import error_response, success_response

from .compat import build_runtime_capabilities
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
from .graphs.plan_replanner import build_plan_replan_detail
from .graphs.retrieval_orchestrator import build_retrieval_orchestrator_detail
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
    run_rag_search,
    run_scenario_dialogue,
    run_vector_rag_search,
    summarize_ai_quality,
)
from .learning_reports import generate_study_report, list_study_reports
from .mcp.server_http import build_mcp_blueprint, call_mcp_tool, read_mcp_resource
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
        runtime = build_runtime_capabilities()
        langchain_caps = build_langchain_capabilities()
        mcp_blueprint = build_mcp_blueprint()
        return success_response(
            {
                **runtime,
                **langchain_caps,
                "mcp_stdio_available": mcp_blueprint.get("mcp_stdio_available", False),
                "mcp_stdio_command": mcp_blueprint.get("stdio_command", ""),
                "mcp_transport_modes": mcp_blueprint.get("transport_modes", []),
                "mcp_tool_count": mcp_blueprint.get("tool_count", 0),
                "mcp_resource_count": mcp_blueprint.get("resource_count", 0),
                "mcp_prompt_count": mcp_blueprint.get("prompt_count", 0),
                "rag_runtime": get_chroma_runtime(),
                "mcp_blueprint": mcp_blueprint,
                "ai_modules": {
                    "profile_memory": True,
                    "plan_history": True,
                    "evaluation": True,
                    "trace_timeline": True,
                    "vector_runtime": True,
                    "personalized_rag": True,
                },
            }
        )


def _finalize_feature_payload(feature_type, payload):
    attach_feature_evidence(feature_type, payload)
    normalize_feature_contract(feature_type, payload)
    return payload


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
            data = run_observed_feature(
                user=request.user,
                feature_type="grammar_tutor",
                endpoint="/api/v1/ai/grammar/tutor",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "grammar_tutor",
                    build_grammar_tutor_answer(request.user, sentence, question)
                    if question
                    else build_grammar_tutor_detail(request.user, sentence),
                ),
                use_cache=True,
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


class AIWordTutorView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIWordExplainSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        payload = {"word_id": serializer.validated_data["word_id"]}
        try:
            data = run_observed_feature(
                user=request.user,
                feature_type="word_tutor",
                endpoint="/api/v1/ai/words/explain",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "word_tutor",
                    build_word_tutor_detail(request.user, payload["word_id"]),
                ),
                use_cache=True,
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


class AIStudyCoachView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIStudyCoachSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        payload = {"trend_days": serializer.validated_data.get("trend_days", 7)}
        try:
            data = run_observed_feature(
                user=request.user,
                feature_type="study_coach",
                endpoint="/api/v1/ai/study-coach",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "study_coach",
                    build_study_coach_detail(request.user, payload["trend_days"]),
                ),
                use_cache=True,
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


class AIPlanReplanView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIPlanReplanSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        payload = {"trend_days": serializer.validated_data.get("trend_days", 7)}
        try:
            data = run_observed_feature(
                user=request.user,
                feature_type="plan_replan",
                endpoint="/api/v1/ai/plans/replan",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "plan_replan",
                    build_plan_replan_detail(request.user, payload["trend_days"]),
                ),
                use_cache=True,
            )
        except ValueError as exc:
            return error_response(str(exc), code=42901, status_code=429)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


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
            data = run_observed_feature(
                user=request.user,
                feature_type="retrieval_orchestrator",
                endpoint="/api/v1/ai/agents/retrieval-orchestrator",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "retrieval_orchestrator",
                    build_retrieval_orchestrator_detail(
                        request.user,
                        payload["query"],
                        payload["limit"],
                    ),
                ),
                use_cache=True,
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


class AIWrongWordsReviewView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIWrongWordsReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)

        payload = {"limit": serializer.validated_data.get("limit", 12)}
        try:
            data = run_observed_feature(
                user=request.user,
                feature_type="wrong_words_review",
                endpoint="/api/v1/ai/wrong-words/review",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "wrong_words_review",
                    build_wrong_words_review_detail(request.user, payload["limit"]),
                ),
                use_cache=True,
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


class AIMCPToolCallView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIMCPToolCallSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        try:
            result = call_mcp_tool(
                request.user,
                serializer.validated_data["tool_name"],
                serializer.validated_data.get("args", {}),
            )
        except ValueError as exc:
            return error_response(str(exc), code=40004)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(
            {
                "tool_name": serializer.validated_data["tool_name"],
                "result": result,
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
            data = run_observed_feature(
                user=request.user,
                feature_type="writing_correct",
                endpoint="/api/v1/ai/writing/correct",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "writing_correct",
                    correct_writing(
                        request.user,
                        payload["text"],
                        payload["level"],
                    ),
                ),
                use_cache=False,
            )
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


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
            data = run_observed_feature(
                user=request.user,
                feature_type="writing_prompt",
                endpoint="/api/v1/ai/writing/prompt",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "writing_prompt",
                    generate_writing_prompt(
                        request.user,
                        payload["level"],
                        payload["topic"],
                        payload["genre"],
                    ),
                ),
                use_cache=True,
            )
        except ValueError as exc:
            return error_response(str(exc), code=42901, status_code=429)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


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
            data = run_observed_feature(
                user=request.user,
                feature_type="translation_evaluate",
                endpoint="/api/v1/ai/translation/evaluate",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "translation_evaluate",
                    evaluate_translation(
                        request.user,
                        payload["source_text"],
                        payload["user_translation"],
                        payload["direction"],
                    ),
                ),
                use_cache=False,
            )
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


class AIGrammarGuideView(APIView):
    permission_classes = [IsWxAuthenticated]

    def get(self, request):
        data = run_observed_feature(
            user=request.user,
            feature_type="grammar_guide",
            endpoint="/api/v1/ai/grammar/guide",
            request_payload={},
            producer=lambda: _finalize_feature_payload("grammar_guide", build_grammar_guide(request.user)),
            use_cache=True,
        )
        return success_response(data)


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
        data = run_observed_feature(
            user=request.user,
            feature_type="rag_search",
            endpoint="/api/v1/ai/rag/search",
            request_payload=payload,
            producer=lambda: _finalize_feature_payload("rag_search", run_rag_search(payload["query"], payload["limit"])),
            use_cache=True,
        )
        return success_response(data)


class AIVectorRAGSearchView(APIView):
    permission_classes = [IsWxAuthenticated]

    def post(self, request):
        serializer = AIVectorRAGSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("invalid params", code=40001, data=serializer.errors)
        payload = {
            "query": serializer.validated_data["query"],
            "limit": serializer.validated_data.get("limit", 8),
            "retrieval_mode": serializer.validated_data.get("retrieval_mode", "auto"),
        }
        try:
            data = run_observed_feature(
                user=request.user,
                feature_type="vector_rag",
                endpoint="/api/v1/ai/rag/vector-search",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "vector_rag",
                    run_vector_rag_search(
                        payload["query"],
                        payload["limit"],
                        retrieval_mode=payload["retrieval_mode"],
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
            data = run_observed_feature(
                user=request.user,
                feature_type="scenario_dialogue",
                endpoint="/api/v1/ai/scenario/dialogue",
                request_payload=payload,
                producer=lambda: _finalize_feature_payload(
                    "scenario_dialogue",
                    run_scenario_dialogue(
                        request.user,
                        payload["scenario"],
                        payload["user_message"],
                        payload.get("conversation_id"),
                    ),
                ),
                use_cache=False,
            )
        except ValueError as exc:
            return error_response(str(exc), code=42901, status_code=429)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


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
            data = generate_study_report(request.user, serializer.validated_data.get("report_type", "weekly"))
            _finalize_feature_payload("study_report", data)
        except Exception as exc:
            return error_response(str(exc), code=40005)
        return success_response(data)


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
