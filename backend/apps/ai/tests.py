from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
import json
from datetime import timedelta
import importlib
from io import StringIO

from django.core.management import call_command
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.ai.observability import make_cache_key
from apps.ai.compat import build_runtime_capabilities
from apps.ai.langchain_runtime import build_langchain_capabilities, TraceCollector
from apps.ai.graphs.retrieval_orchestrator import _build_query_analysis, _build_selection
from apps.ai.graphs.plan_replanner import _build_fallback_replan, build_fast_plan_replan_detail
from apps.ai.learning_assistant import (
    _rank_vector_documents,
    classify_query_intent,
    normalize_learning_query,
    retrieve_learning_context,
    run_vector_rag_search,
)
from apps.ai.rag.retrieval_runtime import merge_documents
from apps.ai.rag.chroma_runtime import _select_embedding_backend, get_collection_fingerprint
from apps.ai.rag.index_status import _extract_progress, _read_tail_lines, build_rag_index_status
from apps.ai.rag.project_docs import build_project_document_catalog, chunk_document_text
from apps.ai.rag.sync_service import RagSyncResult
from apps.ai.mcp.registry import list_tool_defs, read_resource
from apps.ai.mcp.server_http import build_mcp_blueprint
from apps.ai.mcp.stdio_server import create_stdio_server
from apps.ai.graphs.plan_replanner import build_plan_replan_detail
from apps.ai.graphs.retrieval_orchestrator import build_retrieval_orchestrator_detail
from apps.ai.conversation_services import ask_conversation, get_conversation_detail
from apps.ai.evaluations import build_eval_summary, get_eval_run_detail, replay_eval_run
from apps.ai.models import AIAgentApproval, AIAgentArtifact, AIAgentStep, AIAsyncRun, AIEvaluationCase, AIEvaluationRun
from apps.ai.runtime_health import get_runtime_health
from apps.ai.agent_runtime import create_agent_run, dispatch_agent_run_and_wait, list_stale_runs, recover_stale_runs
from apps.ai.response_contracts import normalize_feature_contract
from apps.ai.graphs.grammar_tutor import build_grammar_tutor_answer
from apps.ai.runtime_registry import execute_registered_run
from apps.users.models import LoginToken, WxUser
from apps.books.models import Book, Word
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
    def setUp(self):
        self.book = Book.objects.create(
            name="CET4 Test Book",
            category="cet4",
            level="cet4",
            description="test",
            word_count=2,
        )
        Word.objects.create(
            book=self.book,
            word="important",
            meaning_cn="重要的",
            part_of_speech="adj.",
            synonyms="significant crucial",
            example_sentence="It is important to keep practicing every day.",
            example_translation="每天坚持练习很重要。",
            order_in_book=1,
        )
        Word.objects.create(
            book=self.book,
            word="significant",
            meaning_cn="显著的；意义重大的",
            part_of_speech="adj.",
            synonyms="important meaningful notable",
            example_sentence="The data shows a significant improvement this month.",
            example_translation="数据显示这个月有显著提升。",
            order_in_book=2,
        )

    def test_embedding_backend_is_valid(self):
        self.assertIn(_select_embedding_backend(), {"online", "sentence_transformers", "hash"})

    def test_collection_fingerprint_is_stable_string(self):
        fingerprint = get_collection_fingerprint()
        self.assertEqual(len(fingerprint), 12)
        self.assertTrue(isinstance(fingerprint, str))

    def test_project_doc_catalog_contains_chunks(self):
        catalog = build_project_document_catalog()
        self.assertTrue(catalog)
        self.assertGreaterEqual(int(catalog[0]["chunk_count"]), 1)

    def test_chunk_document_text_splits_long_text(self):
        text = "A" * 300 + "\n\n" + "B" * 300 + "\n\n" + "C" * 300
        chunks = chunk_document_text(text, target_size=450, overlap=80)
        self.assertGreaterEqual(len(chunks), 2)

    def test_query_intent_prefers_learning_for_vocab_question(self):
        result = classify_query_intent("important 和 significant 怎么区分？")
        self.assertEqual(result["intent"], "learning")

    def test_query_intent_prefers_tech_for_rebuild_question(self):
        result = classify_query_intent("Mac 上怎么 rebuild rag index 和 conda 环境？")
        self.assertEqual(result["intent"], "tech")

    def test_query_intent_prefers_tech_for_mcp_manifest_question(self):
        result = classify_query_intent("MCP manifest 和 tools/call 这两个接口怎么配合？")
        self.assertEqual(result["intent"], "tech")
        self.assertEqual(result["allowed_audiences"], ["dev", "migration", "product"])

    def test_query_intent_prefers_tech_for_plan_apply_question(self):
        result = classify_query_intent("AI 自适应计划生成后怎么应用到今天的学习计划？")
        self.assertEqual(result["intent"], "tech")
        self.assertEqual(result["allowed_audiences"], ["dev", "migration", "product"])

    def test_normalize_learning_query_expands_difference_question(self):
        result = normalize_learning_query("important 和 significant 怎么区分？")
        self.assertIn("例句", result["normalized_query"])
        self.assertIn("difference", result["query_expansions"])

    def test_retrieve_learning_context_prioritizes_exact_words_for_difference_question(self):
        context = retrieve_learning_context("important 和 significant 怎么区分？请给词义区别、常见搭配和例句。", limit=8)
        top_words = [item["word"] for item in context["words"][:4]]
        self.assertIn("important", top_words)
        self.assertIn("significant", top_words)

    def test_merge_documents_keeps_primary_vector_origin(self):
        merged = merge_documents(
            [
                {
                    "source_type": "word",
                    "source_id": 1,
                    "title": "important",
                    "content": "important 重要的",
                    "score": 0.4,
                }
            ],
            [],
            secondary_origin="personalized",
            limit=4,
        )
        self.assertEqual(merged[0]["retrieval_sources"], ["vector"])

    def test_rank_vector_documents_prioritizes_exact_words_for_difference_question(self):
        docs, structured_context, using_chroma, retrieval_runtime = _rank_vector_documents(
            "important 和 significant 怎么区分？请给词义区别、常见搭配和例句。",
            limit=8,
            retrieval_mode="hybrid",
        )
        top_titles = [item["title"] for item in docs[:4]]
        self.assertIn("important", top_titles)
        self.assertIn("significant", top_titles)
        self.assertIsNotNone(structured_context)
        self.assertEqual((retrieval_runtime.get("query_intent") or {}).get("intent"), "learning")

    def test_vector_rag_search_returns_exact_word_sources_for_difference_question(self):
        result = run_vector_rag_search("important 和 significant 怎么区分？", limit=8, retrieval_mode="hybrid")
        top_titles = [item["title"] for item in (result.get("documents") or [])[:4]]
        self.assertIn("important", top_titles)
        self.assertIn("significant", top_titles)
        self.assertNotIn("没有找到", result.get("answer_brief", {}).get("summary", ""))


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

    def test_build_rag_index_status_marks_runtime_unavailable_when_logs_completed_but_runtime_is_down(self):
        with TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            out_log = temp_path / "rag.out.log"
            err_log = temp_path / "rag.err.log"
            status_file = temp_path / "rag.status.json"
            out_log.write_text("Rebuilt Chroma RAG index with 26083 chunks\n", encoding="utf-8")
            err_log.write_text("", encoding="utf-8")

            with mock.patch("apps.ai.rag.index_status.RAG_REBUILD_OUT_LOG", out_log), \
                mock.patch("apps.ai.rag.index_status.RAG_REBUILD_ERR_LOG", err_log), \
                mock.patch("apps.ai.rag.index_status.RAG_REBUILD_STATUS_FILE", status_file), \
                mock.patch("apps.ai.rag.index_status.list_rag_rebuild_processes", return_value=[]), \
                mock.patch(
                    "apps.ai.rag.index_status.get_chroma_runtime",
                    return_value={
                        "backend": "chromadb_persistent_local",
                        "fallback_runtime": "local_hash_vector",
                        "collection_health": "missing_dependency",
                        "available": False,
                        "indexed": False,
                        "chunk_count": 0,
                        "expected_chunk_count": 26128,
                        "knowledge_source_catalog": [{"record_count": 26128, "chunk_count": 26128}],
                        "runtime_degraded_reason": "缺少 chromadb 依赖，标准向量运行时不可用。",
                    },
                ):
                result = build_rag_index_status()

            self.assertEqual(result["rebuild_state"], "completed")
            self.assertEqual(result["runtime_state"], "runtime_unavailable")
            self.assertEqual(result["state"], "runtime_unavailable")
            self.assertTrue(result["runtime_degraded"])
            self.assertEqual(result["active_retrieval_backend"], "local_hash_vector")
            self.assertIn("标准向量运行时不可用", result["runtime_degraded_reason"])


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
    def setUp(self):
        cache.clear()

    def test_runtime_capabilities_include_mcp_and_langchain_flags(self):
        runtime = build_runtime_capabilities()
        self.assertIn("mcp_available", runtime)
        self.assertIn("langchain_available", runtime)

    def test_mcp_available_does_not_depend_on_module_version_attr(self):
        compat = importlib.import_module("apps.ai.compat")
        with mock.patch.dict("sys.modules", {"mcp": mock.Mock()}):
            with mock.patch("importlib.metadata.version", return_value="1.27.1"):
                reloaded = importlib.reload(compat)
                self.assertTrue(reloaded.MCP_AVAILABLE)
                self.assertEqual(reloaded.MCP_VERSION, "1.27.1")
        importlib.reload(compat)

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
        self.assertTrue(blueprint["advanced_available"])

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

    def test_mcp_tool_defs_expose_ui_meta(self):
        tools = list_tool_defs()
        vector_tool = next(item for item in tools if item["name"] == "vector_rag_search")
        self.assertEqual(vector_tool["display_name"], "智能资料问答")
        self.assertEqual(vector_tool["category"], "RAG 问答")
        self.assertIn("example_args", vector_tool)
        self.assertEqual(vector_tool["example_args"]["retrieval_mode"], "hybrid")
        self.assertTrue(vector_tool["skill_id"])
        self.assertTrue(vector_tool["version"])
        self.assertIn("permissions", vector_tool)
        self.assertIn("agent_enabled", vector_tool)
        self.assertIn("safe_for_agent", vector_tool)
        self.assertIn("mutation", vector_tool)
        self.assertIn("requires_approval", vector_tool)
        self.assertIn("tool_timeout_ms", vector_tool)

    def test_mcp_blueprint_exposes_capability_flags(self):
        blueprint = build_mcp_blueprint()
        self.assertIn("capability_flags", blueprint)
        self.assertIn("tool_form_mode", blueprint["capability_flags"])

    def test_capability_endpoint_exposes_agent_runtime_fields(self):
        user = WxUser.objects.create(openid="capability-api-user", nickname="Capability API User")
        token = LoginToken.issue_for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.token}")
        response = client.get("/api/v1/ai/capabilities")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("agent_runtime", payload)
        self.assertIn("worker_backend", payload)
        self.assertIn("redis_reachable", payload)
        self.assertIn("queued_features", payload)
        self.assertIn("resume_available", payload)
        self.assertIn("approval_available", payload)
        self.assertIn("strict_runtime", payload)
        self.assertIn("worker_healthy", payload)
        self.assertIn("queue_health", payload)
        self.assertIn("capabilities_cached_at", payload)
        self.assertIn("health_snapshot_age_ms", payload)
        self.assertIn("deep_health_stale", payload)

    @mock.patch("apps.ai.views.build_runtime_capabilities")
    @mock.patch("apps.ai.views.runtime_capability_flags")
    @mock.patch("apps.ai.views.build_langchain_capabilities")
    @mock.patch("apps.ai.views.build_mcp_blueprint")
    @mock.patch("apps.ai.views.get_chroma_runtime")
    def test_capability_endpoint_reuses_cached_snapshot(
        self,
        mocked_chroma,
        mocked_mcp,
        mocked_langchain,
        mocked_health,
        mocked_runtime,
    ):
        mocked_runtime.return_value = {"mcp_available": True, "langchain_available": True, "ai_model_env_ready": True}
        mocked_health.return_value = {"healthy": True, "worker_healthy": True, "strict_runtime": True, "queue_health": {}}
        mocked_langchain.return_value = {"langchain_explicit_available": True}
        mocked_mcp.return_value = {"mcp_stdio_available": True, "tool_count": 1, "resource_count": 0, "prompt_count": 0}
        mocked_chroma.return_value = {"available": False, "collection_health": "missing_dependency"}

        user = WxUser.objects.create(openid="capability-cache-user", nickname="Capability Cache User")
        token = LoginToken.issue_for_user(user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.token}")

        first = client.get("/api/v1/ai/capabilities")
        second = client.get("/api/v1/ai/capabilities")

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(mocked_runtime.call_count, 1)
        self.assertEqual(mocked_health.call_count, 1)
        self.assertEqual(mocked_langchain.call_count, 1)
        self.assertEqual(mocked_mcp.call_count, 1)
        self.assertEqual(mocked_chroma.call_count, 1)

    @mock.patch("apps.ai.agent_runtime.redis_reachable", return_value=False)
    def test_runtime_health_reports_unhealthy_when_redis_is_down(self, _mock_redis):
        health = get_runtime_health()
        if health["strict_runtime"]:
            self.assertFalse(health["healthy"])
            self.assertIn("Redis", health["degraded_reason"])

    @mock.patch("apps.ai.runtime_health.MigrationExecutor")
    def test_runtime_health_reports_pending_ai_migrations(self, mocked_executor):
        migration = mock.Mock()
        migration.app_label = "ai"
        migration.name = "0007_aimessage_runtime_run"
        executor = mock.Mock()
        executor.loader.graph.leaf_nodes.return_value = [("ai", "0007_aimessage_runtime_run")]
        executor.migration_plan.return_value = [(migration, False)]
        mocked_executor.return_value = executor

        payload = get_runtime_health()
        self.assertFalse(payload["healthy"])
        self.assertFalse(payload["schema_healthy"])
        self.assertIn("ai.0007_aimessage_runtime_run", payload["pending_migrations"])

    @mock.patch("apps.ai.runtime_health.inspect_celery_runtime")
    @mock.patch("apps.ai.agent_runtime.redis_reachable", return_value=True)
    def test_runtime_health_exposes_workers_and_observed_queues(self, _mock_redis, mocked_inspect):
        mocked_inspect.return_value = {
            "worker_healthy": True,
            "workers": ["celery@local"],
            "observed_queues": ["ai_short", "ai_long", "ai_tools"],
        }
        health = get_runtime_health()
        if health["strict_runtime"]:
            self.assertEqual(health["workers"], ["celery@local"])
            self.assertIn("ai_short", health["observed_queues"])
            self.assertTrue(health["queue_health"]["ai_short"])

    @mock.patch("apps.ai.agent_runtime.assert_runtime_available_for_feature", side_effect=RuntimeError("Celery Worker 不可达，标准 Agent 运行时不可用。"))
    def test_dispatch_agent_run_and_wait_raises_when_strict_runtime_is_unhealthy(self, _mock_health):
        user = WxUser.objects.create(openid="strict-runtime-user", nickname="Strict Runtime User")
        run = create_agent_run(
            user=user,
            feature_type="vector_rag",
            endpoint="/api/v1/ai/rag/vector-search",
            request_payload={"query": "important", "limit": 6, "retrieval_mode": "hybrid"},
            runtime_kind="celery",
        )
        with self.assertRaises(RuntimeError):
            dispatch_agent_run_and_wait(run, timeout_ms=100)


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

    def test_fast_plan_replan_detail_returns_fallback_without_langchain(self):
        user = WxUser.objects.create(openid="ai-plan-fast-test", nickname="AI Plan Fast Test")
        result = build_fast_plan_replan_detail(user, trend_days=7)
        self.assertEqual((result.get("ai_strategy") or {}).get("engine"), "fast_fallback")
        self.assertIn("multi_agent", result)
        self.assertIn("tool_trace", result)
        self.assertEqual(result.get("langchain_trace"), [])

    @mock.patch("apps.ai.graphs.plan_replanner._run_graph", side_effect=RuntimeError("deep path failed"))
    def test_plan_replan_detail_falls_back_when_deep_pipeline_fails(self, _mock_run_graph):
        user = WxUser.objects.create(openid="ai-plan-fallback-test", nickname="AI Plan Fallback Test")
        result = build_plan_replan_detail(user, trend_days=7)
        self.assertEqual((result.get("ai_strategy") or {}).get("engine"), "deep_replan_fallback")
        self.assertTrue((result.get("degraded_notice") or {}).get("enabled"))
        self.assertIn("保底自适应计划", (result.get("degraded_notice") or {}).get("message", ""))

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

    def test_normalize_feature_contract_adds_runtime_summary(self):
        payload = normalize_feature_contract(
            "vector_rag",
            {
                "answer": {"summary": "ok"},
                "answer_brief": {"summary": "ok"},
                "ai_strategy": {"ai_enabled": False},
                "retrieval_strategy": {"backend": "in_process_counter_cosine", "degraded": True},
                "ai_observability": {"run_id": "abc123", "latency_ms": 25, "status": "success"},
                "runtime": {"ai_model_env_ready": False},
            },
        )
        self.assertIn("runtime_summary", payload)
        self.assertEqual(payload["runtime_summary"]["run_id"], "abc123")
        self.assertTrue(payload["runtime_summary"]["degraded"])


class AIApiContractTests(TestCase):
    def setUp(self):
        self.user = WxUser.objects.create(openid="ai-api-user", nickname="AI API User")
        self.token = LoginToken.issue_for_user(self.user)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.token}")

    @mock.patch("apps.ai.views._run_runtime_feature_with_sync_window")
    def test_vector_rag_endpoint_keeps_old_fields_and_adds_runtime_summary(self, mocked_runtime):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="vector_rag",
            public_id="vectorragrun1234567890",
            runtime_kind="celery",
            endpoint="/api/v1/ai/rag/vector-search",
            request_hash="vector-rag-hash",
            request_payload={"query": "important 和 significant 怎么区分？", "limit": 8, "retrieval_mode": "hybrid"},
            status="succeeded",
            status_text="已完成",
        )
        mocked_runtime.return_value = (
            run,
            {
                "query": "important 和 significant 怎么区分？",
                "answer": {"summary": "直接答案", "grounded_points": ["要点1"], "next_questions": ["继续问1"]},
                "answer_brief": {"summary": "直接答案", "points": ["要点1"], "next_questions": ["继续问1"]},
                "source_pills": [{"label": "important", "source_type": "word", "audience": "learning"}],
                "advanced_debug": {"query_intent": {"intent": "learning", "label": "学习问题"}},
                "documents": [{"title": "important", "source_type": "word", "score": 0.9, "metadata": {}}],
                "retrieval_explain": {"query_intent": {"label": "学习问题"}},
                "structured_context": {},
                "retrieval_strategy": {"backend": "chromadb_persistent_local", "retrieval_mode": "hybrid"},
                "ai_strategy": {"ai_enabled": True, "prompt_version": "assistant_v1", "model_name": "demo"},
                "runtime_summary": {"run_id": run.public_id},
            },
            False,
        )
        response = self.client.post(
            "/api/v1/ai/rag/vector-search",
            data={"query": "important 和 significant 怎么区分？", "retrieval_mode": "hybrid"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("run_id", payload)
        self.assertIn("documents", payload)
        self.assertIn("retrieval_strategy", payload)
        self.assertIn("answer_brief", payload)
        self.assertIn("source_pills", payload)
        self.assertIn("runtime_summary", payload)
        self.assertTrue(AIAsyncRun.objects.filter(public_id=payload["run_id"], user=self.user, feature_type="vector_rag").exists())

    def test_study_coach_endpoint_returns_run_id_under_runtime(self):
        response = self.client.post("/api/v1/ai/study-coach", data={"trend_days": 7}, format="json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("run_id", payload)
        self.assertTrue(AIAsyncRun.objects.filter(public_id=payload["run_id"], user=self.user, feature_type="study_coach").exists())

    def test_word_tutor_endpoint_returns_run_id_under_runtime(self):
        from apps.books.models import Book, Word

        book = Book.objects.create(name="Test Book", description="desc")
        word = Word.objects.create(
            book=book,
            word="important",
            meaning_cn="重要的",
            phonetic="/imˈpɔːtənt/",
            part_of_speech="adj.",
            order_in_book=1,
        )
        response = self.client.post("/api/v1/ai/words/explain", data={"word_id": word.id}, format="json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("run_id", payload)
        self.assertTrue(AIAsyncRun.objects.filter(public_id=payload["run_id"], user=self.user, feature_type="word_tutor").exists())

    @mock.patch("apps.ai.views._run_runtime_feature_with_sync_window")
    def test_retrieval_orchestrator_endpoint_returns_run_id(self, mocked_runtime):
        user = self.user
        run = AIAsyncRun.objects.create(
            user=user,
            feature_type="retrieval_orchestrator",
            public_id="retrievalrun1234567890",
            runtime_kind="celery",
            endpoint="/api/v1/ai/agents/retrieval-orchestrator",
            request_hash="retrieval-hash",
            request_payload={"query": "important 和 significant 的区别", "limit": 6},
            status="succeeded",
            status_text="已完成",
            result_payload={"headline": "编排结果", "summary": "已完成", "runtime_summary": {"run_id": "retrievalrun1234567890"}},
        )
        mocked_runtime.return_value = (
            run,
            {
                "headline": "编排结果",
                "summary": "已完成",
                "multi_agent": {},
                "agent_flow": {},
                "selection": {},
                "knowledge": {},
                "runtime_summary": {"run_id": run.public_id},
            },
            False,
        )
        response = self.client.post(
            "/api/v1/ai/agents/retrieval-orchestrator",
            data={"query": "important 和 significant 的区别", "limit": 6},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["run_id"], run.public_id)
        self.assertIn("runtime_summary", payload)

    @mock.patch("apps.ai.views._run_runtime_feature_with_sync_window", side_effect=RuntimeError("Celery Worker 不可达，标准 Agent 运行时不可用。"))
    def test_vector_rag_endpoint_returns_runtime_health_error_when_strict_worker_is_down(self, _mock_runtime):
        response = self.client.post(
            "/api/v1/ai/rag/vector-search",
            data={"query": "important 和 significant 怎么区分？", "retrieval_mode": "hybrid"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertNotEqual(body["code"], 0)
        self.assertIn("Worker", body["message"])

    @mock.patch("apps.ai.views.launch_async_plan_replan")
    def test_plan_replan_endpoint_creates_async_run(self, mocked_launch):
        response = self.client.post("/api/v1/ai/plans/replan", data={"trend_days": 7}, format="json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("run_id", payload)
        self.assertIn(payload["status"], {"queued", "running"})
        self.assertTrue(AIAsyncRun.objects.filter(public_id=payload["run_id"], user=self.user).exists())
        mocked_launch.assert_called_once()

    def test_plan_replan_run_detail_returns_completed_result(self):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="plan_replan",
            public_id="runplan123456",
            runtime_kind="celery",
            endpoint="/api/v1/ai/plans/replan",
            request_hash="hash-demo",
            request_payload={"trend_days": 7, "force_refresh": False, "prefer_fast": False},
            result_payload={
                "headline": "AI plan",
                "summary": "done",
                "new_plan": {"suggested_daily_target": 18},
                "plan_patch": {"daily_target": 18},
                "decision": {"reasons": ["原因1"]},
                "knowledge": {},
                "tool_trace": [],
                "agent_flow": {},
                "context_bundle": {},
                "profile_memory": {},
                "multi_agent": {},
                "langchain_trace": [],
                "runtime_stack": {},
                "degraded_notice": {"enabled": False, "reason": "", "message": ""},
                "ai_strategy": {
                    "engine": "langgraph",
                    "rag_enabled": True,
                    "ai_enabled": True,
                    "prompt_version": "plan_replan_v2_multi_agent",
                    "model_name": "demo",
                },
                "runtime": {},
            },
            status="succeeded",
            status_text="已完成",
            latency_ms=1234,
            degraded=False,
            retryable=False,
        )
        response = self.client.get(f"/api/v1/ai/plans/replan/runs/{run.public_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["run_id"], run.public_id)
        self.assertEqual(payload["status"], "succeeded")
        self.assertEqual(payload["result"]["headline"], "AI plan")
        self.assertEqual(payload["result"]["runtime_summary"]["run_id"], run.public_id)
        self.assertEqual(payload["runtime_kind"], "celery")

    @mock.patch("apps.ai.views.launch_async_plan_replan")
    def test_plan_replan_endpoint_reuses_running_run(self, mocked_launch):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="plan_replan",
            public_id="runningplan1234",
            runtime_kind="celery",
            endpoint="/api/v1/ai/plans/replan",
            request_hash=make_cache_key(
                "plan_replan_async",
                {"trend_days": 7, "force_refresh": False, "prefer_fast": False},
                user_id=self.user.id,
            ),
            request_payload={"trend_days": 7, "force_refresh": False, "prefer_fast": False},
            status="running",
            status_text="生成中",
        )
        response = self.client.post("/api/v1/ai/plans/replan", data={"trend_days": 7}, format="json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["run_id"], run.public_id)
        mocked_launch.assert_not_called()

    @mock.patch("apps.ai.views.launch_async_plan_replan")
    def test_plan_replan_endpoint_rebuilds_stale_queued_run(self, mocked_launch):
        stale_run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="plan_replan",
            public_id="stalequeuedrun123",
            runtime_kind="celery",
            endpoint="/api/v1/ai/plans/replan",
            request_hash=make_cache_key(
                "plan_replan_async",
                {"trend_days": 7, "force_refresh": True, "prefer_fast": False},
                user_id=self.user.id,
            ),
            request_payload={"trend_days": 7, "force_refresh": True, "prefer_fast": False},
            status="queued",
            status_text="排队中",
        )
        AIAsyncRun.objects.filter(id=stale_run.id).update(created_at=timezone.now() - timedelta(minutes=5))

        response = self.client.post(
            "/api/v1/ai/plans/replan",
            data={"trend_days": 7, "force_refresh": True, "prefer_fast": False},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertNotEqual(payload["run_id"], stale_run.public_id)
        stale_run.refresh_from_db()
        self.assertEqual(stale_run.status, "failed")
        mocked_launch.assert_called_once()

    def test_generic_run_detail_and_steps_endpoint(self):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="plan_replan",
            public_id="genericrun123456",
            runtime_kind="celery",
            endpoint="/api/v1/ai/plans/replan",
            request_hash="generic-hash",
            request_payload={"trend_days": 7},
            status="running",
            status_text="运行中",
            current_agent="coordinator",
        )
        AIAgentStep.objects.create(
            run=run,
            step_index=1,
            step_key="plan_replanner",
            step_kind="agent",
            agent_name="coordinator",
            title="生成 AI 自适应计划",
            status="succeeded",
            input_payload={"trend_days": 7},
            output_payload={"summary": "已完成"},
        )
        detail_response = self.client.get(f"/api/v1/ai/runs/{run.public_id}")
        self.assertEqual(detail_response.status_code, 200)
        detail = detail_response.json()["data"]
        self.assertEqual(detail["run_id"], run.public_id)
        self.assertEqual(detail["current_agent"], "coordinator")
        self.assertIn("runtime_summary", detail)

        steps_response = self.client.get(f"/api/v1/ai/runs/{run.public_id}/steps")
        self.assertEqual(steps_response.status_code, 200)
        steps_payload = steps_response.json()["data"]
        self.assertEqual(steps_payload["run_id"], run.public_id)
        self.assertEqual(len(steps_payload["steps"]), 1)
        self.assertEqual(steps_payload["steps"][0]["agent_name"], "coordinator")

    def test_generic_run_artifacts_endpoint(self):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="vector_rag",
            public_id="artifactrun123456",
            runtime_kind="inline",
            endpoint="/api/v1/ai/rag/vector-search",
            request_hash="artifact-hash",
            request_payload={"query": "important"},
            status="succeeded",
            status_text="已完成",
            result_payload={"answer": {"summary": "ok"}, "runtime_summary": {"run_id": "artifactrun123456"}},
        )
        step = AIAgentStep.objects.create(
            run=run,
            step_index=1,
            step_key="retriever",
            step_kind="agent",
            agent_name="retriever",
            title="执行检索",
            status="succeeded",
        )
        AIAgentArtifact.objects.create(
            run=run,
            step=step,
            artifact_type="retrieval_documents",
            artifact_key="documents",
            title="检索结果",
            summary="命中 3 条文档",
            payload={"documents": [{"title": "important"}]},
        )
        response = self.client.get(f"/api/v1/ai/runs/{run.public_id}/artifacts")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["run_id"], run.public_id)
        self.assertEqual(len(payload["artifacts"]), 1)
        self.assertEqual(payload["artifacts"][0]["artifact_key"], "documents")

    @mock.patch("apps.ai.views.launch_async_plan_replan")
    def test_generic_run_retry_endpoint_requeues_plan_run(self, mocked_launch):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="plan_replan",
            public_id="retryrun123456",
            runtime_kind="celery",
            endpoint="/api/v1/ai/plans/replan",
            request_hash="retry-hash",
            request_payload={"trend_days": 7},
            status="failed",
            status_text="执行失败",
            retryable=True,
        )
        response = self.client.post(f"/api/v1/ai/runs/{run.public_id}/retry", data={}, format="json")
        self.assertEqual(response.status_code, 200)
        run.refresh_from_db()
        self.assertEqual(run.status, "queued")
        self.assertEqual(run.retry_count, 1)
        mocked_launch.assert_called_once()

    @mock.patch("apps.ai.views.execute_inline_agent_run")
    def test_generic_run_retry_endpoint_supports_vector_rag(self, mocked_runtime):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="vector_rag",
            public_id="retryvector123456",
            runtime_kind="inline",
            endpoint="/api/v1/ai/rag/vector-search",
            request_hash="retry-vector-hash",
            request_payload={"query": "important", "limit": 8, "retrieval_mode": "hybrid"},
            status="failed",
            status_text="执行失败",
            retryable=True,
        )
        mocked_runtime.return_value = (
            run,
            {
                "query": "important",
                "answer": {"summary": "ok"},
                "answer_brief": {"summary": "ok", "points": [], "next_questions": []},
                "documents": [],
                "retrieval_strategy": {"backend": "chromadb_persistent_local"},
                "runtime_summary": {"run_id": run.public_id},
            },
        )
        response = self.client.post(f"/api/v1/ai/runs/{run.public_id}/retry", data={}, format="json")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["run_id"], run.public_id)
        mocked_runtime.assert_called_once()

    @mock.patch("apps.ai.views.dispatch_agent_run")
    def test_generic_run_retry_endpoint_supports_mcp_tool_call(self, mocked_dispatch):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="mcp_tool_call",
            public_id="retrymcp12345678",
            runtime_kind="inline",
            endpoint="/api/v1/ai/mcp/tools/call",
            request_hash="retry-mcp-hash",
            request_payload={"tool_name": "plan_replanner", "args": {"trend_days": 7}},
            status="failed",
            status_text="执行失败",
            retryable=True,
        )
        response = self.client.post(f"/api/v1/ai/runs/{run.public_id}/retry", data={}, format="json")
        self.assertEqual(response.status_code, 200)
        run.refresh_from_db()
        self.assertEqual(run.status, "queued")
        self.assertEqual(run.retry_count, 1)
        mocked_dispatch.assert_called_once()

    def test_generic_run_cancel_endpoint_marks_cancelled(self):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="plan_replan",
            public_id="cancelrun12345",
            runtime_kind="celery",
            endpoint="/api/v1/ai/plans/replan",
            request_hash="cancel-hash",
            request_payload={"trend_days": 7},
            status="running",
            status_text="运行中",
        )
        response = self.client.post(f"/api/v1/ai/runs/{run.public_id}/cancel", data={}, format="json")
        self.assertEqual(response.status_code, 200)
        run.refresh_from_db()
        self.assertEqual(run.status, "cancelled")

    @mock.patch("apps.ai.agent_runtime.dispatch_agent_run")
    def test_generic_run_resume_endpoint_requeues_stale_running_run(self, mocked_dispatch):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="vector_rag",
            public_id="resumerun12345",
            runtime_kind="celery",
            endpoint="/api/v1/ai/rag/vector-search",
            request_hash="resume-hash",
            request_payload={"query": "important", "limit": 8, "retrieval_mode": "hybrid"},
            status="running",
            status_text="运行中",
        )
        AIAsyncRun.objects.filter(id=run.id).update(started_at=timezone.now() - timedelta(minutes=10))
        mocked_dispatch.side_effect = lambda current_run: current_run
        response = self.client.post(f"/api/v1/ai/runs/{run.public_id}/resume", data={}, format="json")
        self.assertEqual(response.status_code, 200)
        run.refresh_from_db()
        self.assertEqual(run.status, "queued")
        mocked_dispatch.assert_called_once()

    def test_generic_run_resume_rejects_pending_approval_run(self):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="plan_replan",
            public_id="resumeapproval12",
            runtime_kind="celery",
            endpoint="/api/v1/ai/plans/replan",
            request_hash="resume-approval-hash",
            request_payload={"trend_days": 7},
            status="waiting_approval",
            status_text="等待审批",
            approval_state="pending",
        )
        response = self.client.post(f"/api/v1/ai/runs/{run.public_id}/resume", data={}, format="json")
        self.assertEqual(response.status_code, 400)
        body = response.json()
        self.assertNotEqual(body["code"], 0)

    @mock.patch("apps.ai.views.dispatch_agent_run")
    def test_generic_run_approve_endpoint_resumes_pending_run(self, mocked_dispatch):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="plan_replan",
            public_id="approverun1234",
            runtime_kind="celery",
            endpoint="/api/v1/ai/plans/replan",
            request_hash="approve-hash",
            request_payload={"trend_days": 7},
            status="waiting_approval",
            status_text="等待审批",
            approval_state="pending",
        )
        AIAgentApproval.objects.create(
            run=run,
            approval_key="approvalkey123456",
            feature_type="plan_replan",
            action_type="plan_apply",
            title="应用计划调整",
            request_payload={"daily_target": 18},
            status="pending",
        )
        mocked_dispatch.side_effect = lambda current_run: current_run
        response = self.client.post(
            f"/api/v1/ai/runs/{run.public_id}/approve",
            data={"approved": True, "note": "ok"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        run.refresh_from_db()
        self.assertEqual(run.approval_state, "approved")
        self.assertEqual(run.status, "queued")
        mocked_dispatch.assert_called_once()

    def test_run_detail_marks_stale_running_run(self):
        run = AIAsyncRun.objects.create(
            user=self.user,
            feature_type="vector_rag",
            public_id="stalerun7654321",
            runtime_kind="celery",
            endpoint="/api/v1/ai/rag/vector-search",
            request_hash="stale-hash",
            request_payload={"query": "important"},
            status="running",
            status_text="运行中",
        )
        AIAsyncRun.objects.filter(id=run.id).update(started_at=timezone.now() - timedelta(minutes=10))
        response = self.client.get(f"/api/v1/ai/runs/{run.public_id}")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertTrue(payload["stale"])
        self.assertTrue(payload["runtime_summary"]["stale"])

    def test_mcp_manifest_endpoint_exposes_skill_metadata(self):
        response = self.client.get("/api/v1/ai/mcp/manifest")
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertIn("capability_flags", payload)
        self.assertTrue(payload["advanced_available"])
        vector_tool = next(item for item in payload["tools"] if item["name"] == "vector_rag_search")
        self.assertIn("skill_id", vector_tool)
        self.assertIn("version", vector_tool)
        self.assertIn("permissions", vector_tool)
        self.assertIn("agent_enabled", vector_tool)
        self.assertIn("safe_for_agent", vector_tool)
        self.assertIn("mutation", vector_tool)
        self.assertIn("requires_approval", vector_tool)
        self.assertIn("tool_timeout_ms", vector_tool)

    def test_mcp_tool_call_returns_pending_approval_for_mutating_tool(self):
        response = self.client.post(
            "/api/v1/ai/mcp/tools/call",
            data={"tool_name": "plan_replanner", "args": {"trend_days": 7}},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(payload["tool_name"], "plan_replanner")
        self.assertEqual((payload["result"] or {}).get("status"), "pending_approval")

    def test_plan_replan_run_detail_returns_404_for_other_user(self):
        other = WxUser.objects.create(openid="other-user-plan-run", nickname="Other")
        AIAsyncRun.objects.create(
            user=other,
            feature_type="plan_replan",
            public_id="privateplanrun99",
            endpoint="/api/v1/ai/plans/replan",
            request_hash="hash-other",
            request_payload={"trend_days": 7},
            status="running",
            status_text="生成中",
        )
        response = self.client.get("/api/v1/ai/plans/replan/runs/privateplanrun99")
        self.assertEqual(response.status_code, 404)


class AIConversationServiceTests(TestCase):
    @mock.patch("apps.ai.graphs.grammar_tutor.is_provider_ready", return_value=True)
    @mock.patch("apps.ai.graphs.grammar_tutor.chat_json", side_effect=json.JSONDecodeError("bad json", "{}", 1))
    def test_grammar_tutor_answer_falls_back_when_ai_json_is_invalid(self, _mock_chat_json, _mock_ready):
        user = WxUser.objects.create(openid="grammar-fallback", nickname="Grammar Fallback")
        result = build_grammar_tutor_answer(
            user,
            "The teacher who checks our essays every week offers clear advice before class.",
            "为什么这里用 who？",
        )

        self.assertTrue(result["answer"])
        self.assertIn("followup_questions", result)
        self.assertEqual(result["headline"], "AI 语法问答")

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

    def test_rag_conversation_creates_runtime_run(self):
        user = WxUser.objects.create(openid="conversation-rag-runtime", nickname="Conversation RAG Runtime")
        result = ask_conversation(
            user,
            "important 和 significant 怎么区分？",
            feature_type="rag",
        )

        self.assertTrue(result["runtime_run"])
        self.assertEqual(result["runtime_run"]["status"], "succeeded")
        self.assertEqual(result["resolved_route"], "rag")
        self.assertTrue(AIAsyncRun.objects.filter(public_id=result["runtime_run"]["run_id"], user=user, feature_type="conversation").exists())
        detail = get_conversation_detail(user, result["conversation"]["id"])
        self.assertTrue(detail["latest_runtime_run"])
        self.assertEqual(detail["latest_runtime_run"]["run_id"], result["runtime_run"]["run_id"])
        assistant_message = next(item for item in detail["messages"] if item["role"] == "assistant")
        self.assertEqual(assistant_message["runtime_run_id"], result["runtime_run"]["run_id"])


class AIRuntimeFeatureExecutionTests(TestCase):
    def test_study_coach_runtime_records_multi_step_flow(self):
        user = WxUser.objects.create(openid="runtime-study-coach", nickname="Runtime Study Coach")
        run = create_agent_run(
            user=user,
            feature_type="study_coach",
            endpoint="/api/v1/ai/study-coach",
            request_payload={"trend_days": 7, "force_refresh": False},
            runtime_kind="inline",
        )
        execute_registered_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, "succeeded")
        steps = list(run.steps.order_by("step_index"))
        self.assertGreaterEqual(len(steps), 4)
        self.assertEqual(steps[0].agent_name, "planner")
        self.assertEqual(steps[1].agent_name, "tool_router")
        self.assertIn(steps[2].agent_name, {"coach", "domain_tutor"})
        self.assertEqual(steps[-1].agent_name, "critic")
        result = run.result_payload or {}
        self.assertIn("multi_agent", result)
        self.assertTrue((result.get("multi_agent") or {}).get("handoffs"))

    def test_writing_correct_runtime_records_multi_step_flow(self):
        user = WxUser.objects.create(openid="runtime-writing", nickname="Runtime Writing")
        run = create_agent_run(
            user=user,
            feature_type="writing_correct",
            endpoint="/api/v1/ai/writing/correct",
            request_payload={"text": "I think learn English is very useful for me.", "level": "cet4"},
            runtime_kind="inline",
        )
        execute_registered_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, "succeeded")
        steps = list(run.steps.order_by("step_index"))
        self.assertGreaterEqual(len(steps), 4)
        self.assertEqual(steps[0].agent_name, "planner")
        self.assertEqual(steps[1].agent_name, "tool_router")
        self.assertEqual(steps[-1].agent_name, "critic")
        result = run.result_payload or {}
        self.assertIn("agent_flow", result)
        self.assertEqual(((result.get("multi_agent") or {}).get("selected_tools") or []), ["internal_tools"])

    def test_translation_evaluate_runtime_records_multi_step_flow(self):
        user = WxUser.objects.create(openid="runtime-translation", nickname="Runtime Translation")
        run = create_agent_run(
            user=user,
            feature_type="translation_evaluate",
            endpoint="/api/v1/ai/translation/evaluate",
            request_payload={
                "source_text": "Learning English takes patience.",
                "user_translation": "学习英语需要耐心。",
                "direction": "en_to_zh",
            },
            runtime_kind="inline",
        )
        execute_registered_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, "succeeded")
        steps = list(run.steps.order_by("step_index"))
        self.assertGreaterEqual(len(steps), 4)
        self.assertEqual(steps[0].agent_name, "planner")
        self.assertEqual(steps[1].agent_name, "tool_router")
        self.assertEqual(steps[-1].agent_name, "critic")
        self.assertEqual(((run.result_payload or {}).get("multi_agent") or {}).get("selected_tools"), ["internal_tools"])

    def test_wrong_words_review_runtime_records_multi_step_flow(self):
        user = WxUser.objects.create(openid="runtime-wrong-review", nickname="Runtime Wrong Review")
        run = create_agent_run(
            user=user,
            feature_type="wrong_words_review",
            endpoint="/api/v1/ai/wrong-words/review",
            request_payload={"limit": 8},
            runtime_kind="inline",
        )
        execute_registered_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, "succeeded")
        steps = list(run.steps.order_by("step_index"))
        self.assertGreaterEqual(len(steps), 4)
        self.assertEqual(steps[0].agent_name, "planner")
        self.assertEqual(steps[1].agent_name, "tool_router")
        self.assertEqual(steps[-1].agent_name, "critic")
        self.assertIn("review", run.result_payload or {})

    def test_scenario_dialogue_runtime_records_multi_step_flow(self):
        user = WxUser.objects.create(openid="runtime-scenario", nickname="Runtime Scenario")
        run = create_agent_run(
            user=user,
            feature_type="scenario_dialogue",
            endpoint="/api/v1/ai/scenario/dialogue",
            request_payload={"scenario": "daily", "user_message": "Could you help me order coffee in English?"},
            runtime_kind="inline",
        )
        execute_registered_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, "succeeded")
        steps = list(run.steps.order_by("step_index"))
        self.assertGreaterEqual(len(steps), 4)
        self.assertEqual(steps[0].agent_name, "planner")
        self.assertEqual(steps[-1].agent_name, "critic")
        self.assertTrue(((run.result_payload or {}).get("multi_agent") or {}).get("handoffs"))

    def test_study_report_runtime_records_multi_step_flow(self):
        user = WxUser.objects.create(openid="runtime-study-report", nickname="Runtime Study Report")
        run = create_agent_run(
            user=user,
            feature_type="study_report",
            endpoint="/api/v1/ai/reports",
            request_payload={"report_type": "weekly"},
            runtime_kind="inline",
        )
        execute_registered_run(run)
        run.refresh_from_db()
        self.assertEqual(run.status, "succeeded")
        steps = list(run.steps.order_by("step_index"))
        self.assertGreaterEqual(len(steps), 4)
        self.assertEqual(steps[0].agent_name, "planner")
        self.assertEqual(steps[-1].agent_name, "critic")
        self.assertIn("multi_agent", run.result_payload or {})


class AIRuntimeOpsTests(TestCase):
    def test_list_stale_runs_returns_only_stale_items(self):
        user = WxUser.objects.create(openid="runtime-stale-user", nickname="Runtime Stale User")
        stale_run = AIAsyncRun.objects.create(
            user=user,
            feature_type="vector_rag",
            public_id="staleops1234567890123456",
            runtime_kind="celery",
            endpoint="/api/v1/ai/rag/vector-search",
            request_hash="stale-ops-hash",
            request_payload={"query": "important"},
            status="running",
            status_text="运行中",
            started_at=timezone.now() - timedelta(minutes=10),
        )
        fresh_run = AIAsyncRun.objects.create(
            user=user,
            feature_type="vector_rag",
            public_id="freshops1234567890123456",
            runtime_kind="celery",
            endpoint="/api/v1/ai/rag/vector-search",
            request_hash="fresh-ops-hash",
            request_payload={"query": "significant"},
            status="running",
            status_text="运行中",
            started_at=timezone.now(),
        )
        stale = list_stale_runs(limit=10)
        stale_ids = {item.public_id for item in stale}
        self.assertIn(stale_run.public_id, stale_ids)
        self.assertNotIn(fresh_run.public_id, stale_ids)

    @mock.patch("apps.ai.agent_runtime.dispatch_agent_run")
    def test_recover_stale_runs_requeues_and_dispatches(self, mocked_dispatch):
        user = WxUser.objects.create(openid="runtime-recover-user", nickname="Runtime Recover User")
        run = AIAsyncRun.objects.create(
            user=user,
            feature_type="conversation",
            public_id="recoverops12345678901234",
            runtime_kind="celery",
            endpoint="/api/v1/ai/conversations/ask",
            request_hash="recover-ops-hash",
            request_payload={"question": "important 和 significant 怎么区分？"},
            status="running",
            status_text="运行中",
            started_at=timezone.now() - timedelta(minutes=10),
        )
        mocked_dispatch.side_effect = lambda current_run: current_run
        recovered = recover_stale_runs(limit=10)
        self.assertEqual(len(recovered), 1)
        run.refresh_from_db()
        self.assertEqual(run.status, "queued")
        self.assertTrue(run.artifacts.filter(artifact_key="stale_recovery").exists())
        mocked_dispatch.assert_called_once()

    @mock.patch("apps.ai.runtime_health.get_runtime_health")
    def test_check_ai_runtime_health_command_outputs_json(self, mocked_health):
        mocked_health.return_value = {
            "healthy": False,
            "agent_runtime": "celery",
            "strict_runtime": True,
            "redis_reachable": True,
            "worker_healthy": False,
            "workers": [],
            "observed_queues": [],
            "queue_health": {"ai_short": False, "ai_long": False, "ai_tools": False},
            "degraded_reason": "Celery Worker 不可达，标准 Agent 运行时不可用。",
        }
        out = StringIO()
        call_command("check_ai_runtime_health", "--json", stdout=out)
        payload = json.loads(out.getvalue())
        self.assertFalse(payload["healthy"])
        self.assertIn("queue_health", payload)

    @mock.patch("apps.ai.agent_runtime.dispatch_agent_run")
    def test_recover_stale_ai_runs_command_dry_run_and_recover(self, mocked_dispatch):
        user = WxUser.objects.create(openid="runtime-command-user", nickname="Runtime Command User")
        run = AIAsyncRun.objects.create(
            user=user,
            feature_type="plan_replan",
            public_id="cmdrecover12345678901234",
            runtime_kind="celery",
            endpoint="/api/v1/ai/plans/replan",
            request_hash="cmd-recover-hash",
            request_payload={"trend_days": 7},
            status="queued",
            status_text="排队中",
        )
        AIAsyncRun.objects.filter(id=run.id).update(updated_at=timezone.now() - timedelta(minutes=10))
        dry_out = StringIO()
        call_command("recover_stale_ai_runs", "--dry-run", stdout=dry_out)
        self.assertIn(run.public_id, dry_out.getvalue())

        mocked_dispatch.side_effect = lambda current_run: current_run
        recover_out = StringIO()
        call_command("recover_stale_ai_runs", stdout=recover_out)
        run.refresh_from_db()
        self.assertEqual(run.status, "queued")
        mocked_dispatch.assert_called_once()


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
