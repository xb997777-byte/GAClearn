from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
import json

from django.test import TestCase

from apps.ai.observability import make_cache_key
from apps.ai.compat import build_runtime_capabilities
from apps.ai.langchain_runtime import build_langchain_capabilities, TraceCollector
from apps.ai.graphs.retrieval_orchestrator import _build_query_analysis, _build_selection
from apps.ai.graphs.plan_replanner import _build_fallback_replan
from apps.ai.rag.chroma_runtime import _select_embedding_backend
from apps.ai.rag.index_status import _extract_progress, _read_tail_lines, build_rag_index_status
from apps.ai.rag.sync_service import RagSyncResult
from apps.ai.mcp.registry import list_tool_defs, read_resource
from apps.ai.mcp.server_http import build_mcp_blueprint
from apps.ai.mcp.stdio_server import create_stdio_server
from apps.ai.graphs.plan_replanner import build_plan_replan_detail
from apps.ai.graphs.retrieval_orchestrator import build_retrieval_orchestrator_detail
from apps.ai.conversation_services import ask_conversation
from apps.ai.evaluations import build_eval_summary, get_eval_run_detail, replay_eval_run
from apps.ai.models import AIEvaluationCase, AIEvaluationRun
from apps.ai.response_contracts import normalize_feature_contract
from apps.users.models import LoginToken, WxUser
from rest_framework.test import APIClient


def _json_safe(payload):
    return json.loads(json.dumps(payload, ensure_ascii=False, default=str))


class AIObservabilityTests(TestCase):
    def test_cache_key_isolated_by_user(self):
        payload = {"trend_days": 7}
        key_a = make_cache_key("plan_replan", payload, user_id=1)
        key_b = make_cache_key("plan_replan", payload, user_id=2)

        self.assertNotEqual(key_a, key_b)


class AIRagRuntimeTests(TestCase):
    def test_embedding_backend_is_valid(self):
        self.assertIn(_select_embedding_backend(), {"online", "sentence_transformers", "hash"})


class AIRagIndexStatusTests(TestCase):
    def test_extract_progress_from_log_lines(self):
        rows = [
            "Building RAG index with backend=online model=text-embedding-v4",
            "Inserted batch 1-64 / 25623",
            "Inserted batch 65-128 / 25623",
        ]
        result = _extract_progress(rows)
        self.assertEqual(result["inserted_count"], 128)
        self.assertEqual(result["total_count"], 25623)
        self.assertEqual(result["last_progress_line"], "Inserted batch 65-128 / 25623")

    def test_read_tail_lines_keeps_latest_rows(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "sample.log"
            path.write_text("a\nb\nc\nd\n", encoding="utf-8")
            self.assertEqual(_read_tail_lines(path, limit=2), ["c", "d"])

    def test_build_rag_index_status_uses_runtime_and_logs(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_log = temp_path / "rag.out.log"
            err_log = temp_path / "rag.err.log"
            status_file = temp_path / "rag.status.json"
            out_log.write_text("Inserted batch 129-192 / 999\n", encoding="utf-8")
            err_log.write_text("", encoding="utf-8")

            with mock.patch("apps.ai.rag.index_status.RAG_REBUILD_OUT_LOG", out_log), \
                mock.patch("apps.ai.rag.index_status.RAG_REBUILD_ERR_LOG", err_log), \
                mock.patch("apps.ai.rag.index_status.RAG_REBUILD_STATUS_FILE", status_file), \
                mock.patch("apps.ai.rag.index_status.list_rag_rebuild_processes", return_value=[{"pid": 5188, "command_line": "python manage.py rebuild_rag_index"}]), \
                mock.patch(
                    "apps.ai.rag.index_status.get_chroma_runtime",
                    return_value={
                        "embedding_backend": "online",
                        "embedding_provider": "openai_compatible",
                        "embedding_model": "text-embedding-v4",
                        "chunk_count": 256,
                        "indexed": True,
                        "available": True,
                        "knowledge_source_catalog": [
                            {"record_count": 10},
                            {"record_count": 20},
                        ],
                    },
                ):
                result = build_rag_index_status()

            self.assertTrue(result["running"])
            self.assertEqual(result["state"], "running")
            self.assertEqual(result["inserted_count"], 192)
            self.assertEqual(result["total_count"], 999)
            self.assertEqual(result["pid_list"], [5188])


class AIRagSyncTests(TestCase):
    def test_sync_result_to_dict(self):
        result = RagSyncResult(
            mode="incremental_sync",
            total_chunks=10,
            upserted_count=3,
            skipped_count=6,
            deleted_count=1,
            indexed_count_after_sync=10,
        )
        self.assertEqual(
            result.to_dict(),
            {
                "mode": "incremental_sync",
                "total_chunks": 10,
                "upserted_count": 3,
                "skipped_count": 6,
                "deleted_count": 1,
                "indexed_count_after_sync": 10,
            },
        )


class AICapabilityAndRuntimeTests(TestCase):
    def test_runtime_capabilities_include_mcp_and_langchain_flags(self):
        runtime = build_runtime_capabilities()
        self.assertIn("mcp_available", runtime)
        self.assertIn("langchain_available", runtime)

    def test_langchain_capabilities_expose_trace_flags(self):
        caps = build_langchain_capabilities()
        self.assertIn("langchain_explicit_available", caps)
        self.assertIn("langchain_tool_calling_available", caps)
        self.assertIn("langchain_trace_available", caps)

    def test_mcp_blueprint_and_stdio_share_registry(self):
        blueprint = build_mcp_blueprint()
        self.assertEqual(blueprint["tool_count"], len(list_tool_defs()))
        self.assertIn("stdio_command", blueprint)
        self.assertIn("http", blueprint["transport_modes"])
        self.assertIn("stdio", blueprint["transport_modes"])

    def test_stdio_server_constructs(self):
        server = create_stdio_server()
        self.assertIsNotNone(server)

    def test_trace_collector_captures_events(self):
        trace = TraceCollector("demo")
        trace.add("chain_start", "demo", detail="start")
        trace.add("tool_start", "demo_tool", detail="call", args={"a": 1})
        self.assertEqual(len(trace.events), 2)

    def test_mcp_resource_defs_can_be_read(self):
        user = WxUser.objects.create(openid="mcp-resource-user", nickname="MCP User")
        result = read_resource(user, "ai://profile-memory/self")
        self.assertEqual(result["template"], "ai://profile-memory/{user_id}")
        self.assertIn("data", result)


class AIRetrievalOrchestratorTests(TestCase):
    def test_query_analysis_prefers_hybrid_for_difference_questions(self):
        result = _build_query_analysis("important 和 significant 的区别")
        self.assertEqual(result["preferred_mode"], "hybrid")

    def test_selection_prefers_structured_for_rule_like_queries(self):
        result = _build_selection(
            {
                "query_analysis": {"preferred_mode": "structured"},
                "knowledge": {
                    "structured_rag": {
                        "retrieval": {
                            "words": [{"id": 1}],
                            "grammar_points": [{"id": 2}],
                            "sentences": [],
                        }
                    },
                    "hybrid_rag": {"documents": [{"retrieval_sources": ["vector"]}]},
                },
            }
        )
        self.assertEqual(result["selected_path"], "structured_rag")

    @mock.patch("apps.ai.graphs.plan_replanner.is_provider_ready", return_value=False)
    def test_plan_replan_detail_exposes_multi_agent_and_trace(self, _mock_ready):
        user = WxUser.objects.create(openid="ai-plan-test", nickname="AI Plan Test")
        result = build_plan_replan_detail(user, trend_days=7)
        self.assertIn("multi_agent", result)
        self.assertIn("langchain_trace", result)
        self.assertIn("runtime_stack", result)

    @mock.patch("apps.ai.graphs.retrieval_orchestrator.is_provider_ready", return_value=False)
    def test_retrieval_orchestrator_exposes_multi_agent_and_trace(self, _mock_ready):
        user = WxUser.objects.create(openid="ai-rag-test", nickname="AI RAG Test")
        result = build_retrieval_orchestrator_detail(user, "important 和 significant 的区别", 6)
        self.assertIn("multi_agent", result)
        self.assertIn("langchain_trace", result)
        self.assertIn("runtime_stack", result)


class AIEvaluationSummaryTests(TestCase):
    @mock.patch("apps.ai.graphs.plan_replanner.is_provider_ready", return_value=False)
    def test_eval_summary_contains_regression_report(self, _mock_ready):
        user = WxUser.objects.create(openid="eval-user", nickname="Eval User")
        result = build_plan_replan_detail(user, trend_days=7)
        from apps.ai.models import AIEvaluationCase, AIEvaluationRun

        case = AIEvaluationCase.objects.create(
            name="plan eval",
            case_type="plan_replan",
            input_payload={"trend_days": 7},
            expected_signals={},
        )
        AIEvaluationRun.objects.create(
            user=user,
            case=case,
            feature_type="plan_replan",
            status="passed",
            score="90.00",
            request_payload={"trend_days": 7},
            result_payload=_json_safe(result),
            trace_payload={},
            runtime_snapshot=build_runtime_capabilities(),
        )
        summary = build_eval_summary(case_type="plan_replan", limit=10)
        self.assertIn("regression_report", summary)
        self.assertGreaterEqual(summary["run_count"], 1)

    def test_eval_run_detail_and_replay_work(self):
        user = WxUser.objects.create(openid="eval-detail-user", nickname="Eval Detail User")
        case = AIEvaluationCase.objects.create(
            name="detail eval",
            case_type="plan_replan",
            input_payload={"trend_days": 7},
            expected_signals={},
        )
        run = AIEvaluationRun.objects.create(
            user=user,
            case=case,
            feature_type="plan_replan",
            status="passed",
            score="88.00",
            request_payload={"trend_days": 7},
            result_payload={"headline": "AI plan", "summary": "done"},
            trace_payload={"trace_timeline": [{"step": "done"}]},
            runtime_snapshot=build_runtime_capabilities(),
        )

        detail = get_eval_run_detail(user, run.id)
        self.assertEqual(detail["id"], run.id)
        self.assertEqual(detail["case"]["name"], "detail eval")
        self.assertIn("replay_payload", detail)

        with mock.patch("apps.ai.evaluations._run_case_for_user") as mocked_run_case:
            mocked_run_case.return_value = {
                "status": "passed",
                "score": 91,
                "result_payload": {"headline": "replayed"},
                "trace_payload": {"trace_timeline": []},
                "failure_reason": "",
                "feature_type": "plan_replan",
                "request_payload": {"trend_days": 9},
            }
            replayed = replay_eval_run(user, run.id, override_request_payload={"trend_days": 9})

        self.assertNotEqual(replayed["id"], run.id)
        self.assertEqual(replayed["request_payload"]["trend_days"], 9)


class AIResponseContractTests(TestCase):
    def test_normalize_feature_contract_promotes_context_sources(self):
        payload = normalize_feature_contract(
            "study_coach",
            {
                "coach": {"headline": "AI 教练", "today_strategy": "先复习再学新词"},
                "snapshot": {
                    "overview": {"learned_word_count": 18},
                    "today_task": {"plan": {"book": {"name": "CET4 核心词"}}},
                    "priority_wrong_words": [{"word": "important"}],
                },
                "profile_memory": {"profile_summary": "最近更适合先复习后新学"},
                "ai_strategy": {"ai_enabled": False},
                "runtime": {"langgraph_available": False},
            },
        )

        self.assertIn("context_sources", payload)
        self.assertTrue(payload["context_sources"])
        self.assertEqual(payload["feature_runtime"]["context_sources"], payload["context_sources"])


class AIConversationServiceTests(TestCase):
    def test_grammar_conversation_followup_reuses_last_sentence(self):
        user = WxUser.objects.create(openid="conversation-grammar", nickname="Conversation Grammar")
        first = ask_conversation(
            user,
            "The teacher who checks our essays every week offers clear advice before class.",
            feature_type="grammar",
        )

        second = ask_conversation(
            user,
            "为什么这里用 who？",
            conversation_id=first["conversation"]["id"],
            feature_type="grammar",
        )

        self.assertEqual(second["conversation"]["feature_type"], "grammar")
        self.assertEqual(second["answer"]["sentence"], "The teacher who checks our essays every week offers clear advice before class.")
        self.assertEqual(second["answer"]["question"], "为什么这里用 who？")
        self.assertEqual(second["answer"]["feature_runtime"]["feature_type"], "grammar_tutor")

    def test_writing_conversation_routes_to_writing_correct(self):
        user = WxUser.objects.create(openid="conversation-writing", nickname="Conversation Writing")
        result = ask_conversation(
            user,
            "I think learning English every day is helpful because it can make me keep progress.",
            feature_type="writing",
        )

        self.assertEqual(result["conversation"]["feature_type"], "writing")
        self.assertEqual(result["answer"]["feature_runtime"]["feature_type"], "writing_correct")
        self.assertTrue(result["answer"]["summary"])


class AIEvaluationApiTests(TestCase):
    def setUp(self):
        self.user = WxUser.objects.create(openid="eval-api-user", nickname="Eval API User")
        self.token = LoginToken.issue_for_user(self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.token}")
        self.case = AIEvaluationCase.objects.create(
            name="api eval",
            case_type="plan_replan",
            input_payload={"trend_days": 7},
            expected_signals={},
        )
        self.run = AIEvaluationRun.objects.create(
            user=self.user,
            case=self.case,
            feature_type="plan_replan",
            status="failed",
            score="33.00",
            request_payload={"trend_days": 7},
            result_payload={"headline": "bad", "summary": "failed"},
            trace_payload={"trace_timeline": [{"step": "failed"}]},
            failure_reason="demo failure",
            runtime_snapshot=build_runtime_capabilities(),
        )

    def test_get_evaluation_run_detail_endpoint(self):
        response = self.client.get(f"/api/v1/ai/evaluations/runs/{self.run.id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["id"], self.run.id)
        self.assertEqual(payload["case"]["name"], self.case.name)

    @mock.patch("apps.ai.evaluations.replay_eval_run")
    def test_replay_evaluation_run_endpoint(self, mocked_replay):
        mocked_replay.return_value = {
            "id": self.run.id + 1,
            "case_id": self.case.id,
            "case_name": self.case.name,
            "case_type": self.case.case_type,
            "feature_type": "plan_replan",
            "status": "passed",
            "score": 95.0,
            "request_payload": {"trend_days": 9},
            "result_payload": {"headline": "ok"},
            "trace_payload": {},
            "failure_reason": "",
            "runtime_snapshot": {},
            "prompt_version": "",
            "model_name": "",
            "trace_steps": 0,
            "feature_runtime": {},
            "runtime_stack": {},
            "replay_payload": {"case_id": self.case.id},
            "created_at": "",
        }

        response = self.client.post(
            f"/api/v1/ai/evaluations/runs/{self.run.id}/replay",
            data={"request_payload": {"trend_days": 9}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["id"], self.run.id + 1)
        mocked_replay.assert_called_once()
