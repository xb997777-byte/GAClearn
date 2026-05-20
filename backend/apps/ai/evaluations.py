from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Any, Callable, Dict, Tuple

from .compat import build_runtime_capabilities
from .evidence import attach_feature_evidence
from .graphs.grammar_tutor import build_grammar_tutor_detail
from .graphs.plan_replanner import build_plan_replan_detail
from .graphs.retrieval_orchestrator import build_retrieval_orchestrator_detail
from .graphs.study_coach import build_study_coach_detail
from .graphs.vocab_tutor import build_word_tutor_detail
from .graphs.wrong_word_review import build_wrong_words_review_detail
from .learning_assistant import evaluate_rag_recall, run_vector_rag_search
from .models import AIEvaluationCase, AIEvaluationRun
from .response_contracts import normalize_feature_contract


RunnerType = Callable[[Any, Dict[str, Any], AIEvaluationCase], Dict[str, Any]]


def _ensure_default_cases():
    defaults = [
        {
            "name": "RAG Recall Baseline",
            "case_type": "rag_recall",
            "description": "Check keyword coverage for structured recall and vector recall.",
            "input_payload": {
                "query": "important and significant difference",
                "expected_keywords": ["important", "significant", "example"],
                "preferred_source_type": "word",
                "limit": 6,
            },
            "expected_signals": {"min_coverage_rate": 50},
        },
        {
            "name": "Vector RAG Baseline",
            "case_type": "vector_rag",
            "description": "Check vector or hybrid retrieval returns grounded answer and documents.",
            "input_payload": {
                "query": "important synonyms and examples",
                "limit": 6,
                "retrieval_mode": "hybrid",
            },
            "expected_signals": {"min_documents": 1},
        },
        {
            "name": "Plan Replan",
            "case_type": "plan_replan",
            "description": "Check plan replanner returns plan patch or study order.",
            "input_payload": {"trend_days": 7},
            "expected_signals": {"require_patch_or_order": True},
        },
        {
            "name": "Retrieval Orchestrator",
            "case_type": "retrieval_orchestrator",
            "description": "Check retrieval orchestrator returns selection and final answer.",
            "input_payload": {"query": "important and significant difference", "limit": 6},
            "expected_signals": {"require_selection": True},
        },
        {
            "name": "Study Coach",
            "case_type": "study_coach",
            "description": "Check study coach returns strategy and next action.",
            "input_payload": {"trend_days": 7},
            "expected_signals": {"require_strategy": True},
        },
        {
            "name": "Word Tutor",
            "case_type": "word_tutor",
            "description": "Check word tutor returns explanation and micro quiz.",
            "input_payload": {"word_id": 1},
            "expected_signals": {"require_tutor": True},
        },
        {
            "name": "Wrong Words Review",
            "case_type": "wrong_words_review",
            "description": "Check wrong words review returns action plan.",
            "input_payload": {"limit": 12},
            "expected_signals": {"require_action_plan": True},
        },
        {
            "name": "Grammar Tutor",
            "case_type": "grammar_tutor",
            "description": "Check grammar tutor returns explanation and references.",
            "input_payload": {"sentence": "The teacher who checks our essays every week offers clear advice before class."},
            "expected_signals": {"require_tutor": True},
        },
    ]
    for item in defaults:
        AIEvaluationCase.objects.get_or_create(name=item["name"], defaults=item)


def _serialize_payload(feature_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    attach_feature_evidence(feature_type, payload)
    normalize_feature_contract(feature_type, payload)
    return payload


def _score_bool(passed: bool, pass_score: str = "100.00", fail_score: str = "40.00") -> Decimal:
    return Decimal(pass_score if passed else fail_score)


def _run_rag_case(_user, payload: Dict[str, Any], case: AIEvaluationCase) -> Dict[str, Any]:
    result = evaluate_rag_recall(
        payload.get("query", ""),
        payload.get("expected_keywords") or [],
        payload.get("preferred_source_type", ""),
        payload.get("limit", 6),
    )
    result = _serialize_payload("rag_recall_eval", result)
    coverage = max(
        float((result.get("structured_recall") or {}).get("coverage_rate") or 0),
        float((result.get("vector_recall") or {}).get("coverage_rate") or 0),
    )
    threshold = float((case.expected_signals or {}).get("min_coverage_rate") or 50)
    passed = coverage >= threshold
    return {
        "status": "passed" if passed else "failed",
        "score": Decimal(str(round(coverage, 2))),
        "result_payload": result,
        "trace_payload": result.get("evidence") or {},
        "failure_reason": "" if passed else f"coverage too low: {coverage}",
        "feature_type": "rag_recall_eval",
    }


def _run_vector_rag_case(user, payload: Dict[str, Any], case: AIEvaluationCase) -> Dict[str, Any]:
    result = run_vector_rag_search(
        payload.get("query", ""),
        payload.get("limit", 6),
        retrieval_mode=payload.get("retrieval_mode", "hybrid"),
        user=user,
    )
    result = _serialize_payload("vector_rag", result)
    documents = result.get("documents") or []
    summary = ((result.get("answer") or {}).get("summary") or "").strip()
    min_documents = int((case.expected_signals or {}).get("min_documents") or 1)
    passed = len(documents) >= min_documents and bool(summary)
    score = Decimal(str(min(len(documents) * 20, 100))) if documents else Decimal("0")
    return {
        "status": "passed" if passed else "failed",
        "score": score,
        "result_payload": result,
        "trace_payload": result.get("evidence") or {},
        "failure_reason": "" if passed else "missing vector documents or grounded summary",
        "feature_type": "vector_rag",
    }


def _run_plan_case(user, payload: Dict[str, Any], _case: AIEvaluationCase) -> Dict[str, Any]:
    result = build_plan_replan_detail(user, payload.get("trend_days", 7))
    result = _serialize_payload("plan_replan", result)
    has_order = bool(((result.get("new_plan") or {}).get("study_order") or []))
    has_patch = bool(result.get("plan_patch") or {})
    passed = has_order or has_patch
    return {
        "status": "passed" if passed else "failed",
        "score": _score_bool(passed, "100.00", "40.00"),
        "result_payload": result,
        "trace_payload": result.get("evidence") or {},
        "failure_reason": "" if passed else "missing patch and study order",
        "feature_type": "plan_replan",
    }


def _run_retrieval_orchestrator_case(user, payload: Dict[str, Any], _case: AIEvaluationCase) -> Dict[str, Any]:
    result = build_retrieval_orchestrator_detail(user, payload.get("query", ""), payload.get("limit", 6))
    result = _serialize_payload("retrieval_orchestrator", result)
    passed = bool(result.get("selection")) and bool(result.get("final_answer"))
    return {
        "status": "passed" if passed else "failed",
        "score": _score_bool(passed, "100.00", "45.00"),
        "result_payload": result,
        "trace_payload": result.get("evidence") or {},
        "failure_reason": "" if passed else "missing selection or final_answer",
        "feature_type": "retrieval_orchestrator",
    }


def _run_study_coach_case(user, payload: Dict[str, Any], _case: AIEvaluationCase) -> Dict[str, Any]:
    result = build_study_coach_detail(user, payload.get("trend_days", 7))
    result = _serialize_payload("study_coach", result)
    coach = result.get("coach") or {}
    passed = bool(coach.get("today_strategy")) and bool(coach.get("next_action"))
    return {
        "status": "passed" if passed else "failed",
        "score": _score_bool(passed, "100.00", "50.00"),
        "result_payload": result,
        "trace_payload": result.get("evidence") or {},
        "failure_reason": "" if passed else "missing today_strategy or next_action",
        "feature_type": "study_coach",
    }


def _run_word_tutor_case(user, payload: Dict[str, Any], _case: AIEvaluationCase) -> Dict[str, Any]:
    result = build_word_tutor_detail(user, payload.get("word_id", 1))
    result = _serialize_payload("word_tutor", result)
    tutor = result.get("tutor") or {}
    passed = bool(tutor.get("simple_explanation_cn")) and bool(tutor.get("mini_quiz"))
    return {
        "status": "passed" if passed else "failed",
        "score": _score_bool(passed, "100.00", "55.00"),
        "result_payload": result,
        "trace_payload": result.get("evidence") or {},
        "failure_reason": "" if passed else "missing tutor explanation or mini quiz",
        "feature_type": "word_tutor",
    }


def _run_wrong_words_review_case(user, payload: Dict[str, Any], _case: AIEvaluationCase) -> Dict[str, Any]:
    result = build_wrong_words_review_detail(user, payload.get("limit", 12))
    result = _serialize_payload("wrong_words_review", result)
    review = result.get("review") or {}
    passed = bool(review.get("summary")) and bool(review.get("action_plan"))
    return {
        "status": "passed" if passed else "failed",
        "score": _score_bool(passed, "100.00", "55.00"),
        "result_payload": result,
        "trace_payload": result.get("evidence") or {},
        "failure_reason": "" if passed else "missing review summary or action plan",
        "feature_type": "wrong_words_review",
    }


def _run_grammar_tutor_case(user, payload: Dict[str, Any], _case: AIEvaluationCase) -> Dict[str, Any]:
    result = build_grammar_tutor_detail(user, payload.get("sentence", "This is a sample sentence."))
    result = _serialize_payload("grammar_tutor", result)
    tutor = result.get("tutor") or {}
    passed = bool(tutor.get("explanation_cn")) and bool(result.get("retrieval"))
    return {
        "status": "passed" if passed else "failed",
        "score": _score_bool(passed, "100.00", "55.00"),
        "result_payload": result,
        "trace_payload": result.get("evidence") or {},
        "failure_reason": "" if passed else "missing grammar tutor explanation or retrieval context",
        "feature_type": "grammar_tutor",
    }


CASE_RUNNERS: Dict[str, RunnerType] = {
    "rag_recall": _run_rag_case,
    "vector_rag": _run_vector_rag_case,
    "plan_replan": _run_plan_case,
    "retrieval_orchestrator": _run_retrieval_orchestrator_case,
    "study_coach": _run_study_coach_case,
    "word_tutor": _run_word_tutor_case,
    "wrong_words_review": _run_wrong_words_review_case,
    "grammar_tutor": _run_grammar_tutor_case,
}


def serialize_eval_case(item: AIEvaluationCase) -> Dict[str, Any]:
    return {
        "id": item.id,
        "name": item.name,
        "case_type": item.case_type,
        "enabled": item.enabled,
        "description": item.description,
        "input_payload": item.input_payload,
        "expected_signals": item.expected_signals,
        "case_group": item.case_type,
    }


def serialize_eval_run(item: AIEvaluationRun) -> Dict[str, Any]:
    trace_payload = item.trace_payload or {}
    result_payload = item.result_payload or {}
    ai_strategy = result_payload.get("ai_strategy") or {}
    feature_runtime = result_payload.get("feature_runtime") or {}
    return {
        "id": item.id,
        "case_id": item.case_id,
        "case_name": item.case.name,
        "case_type": item.case.case_type,
        "feature_type": item.feature_type,
        "status": item.status,
        "score": float(item.score),
        "request_payload": item.request_payload,
        "result_payload": item.result_payload,
        "trace_payload": item.trace_payload,
        "failure_reason": item.failure_reason,
        "runtime_snapshot": item.runtime_snapshot,
        "prompt_version": ai_strategy.get("prompt_version", ""),
        "model_name": ai_strategy.get("model_name", ""),
        "trace_steps": len(trace_payload.get("trace_timeline") or []),
        "feature_runtime": feature_runtime,
        "runtime_stack": result_payload.get("runtime_stack") or {},
        "replay_payload": {
            "case_id": item.case_id,
            "case_type": item.case.case_type,
            "request_payload": item.request_payload,
        },
        "created_at": item.created_at,
    }


def list_eval_cases(case_type: str = ""):
    _ensure_default_cases()
    queryset = AIEvaluationCase.objects.filter(enabled=True)
    if case_type:
        queryset = queryset.filter(case_type=case_type)
    return [serialize_eval_case(item) for item in queryset.order_by("id")]


def list_eval_runs(case_type: str = "", failed_only: bool = False, limit=10):
    queryset = AIEvaluationRun.objects.select_related("case")
    if case_type:
        queryset = queryset.filter(case__case_type=case_type)
    if failed_only:
        queryset = queryset.exclude(status="passed")
    queryset = queryset.order_by("-id")[: min(max(int(limit or 10), 1), 50)]
    return [serialize_eval_run(item) for item in queryset]


def _runtime_path_summary(runs):
    counter = defaultdict(int)
    for item in runs:
        feature_runtime = item.get("feature_runtime") or {}
        tags = feature_runtime.get("tags") or []
        for tag in tags:
            counter[tag] += 1
    keys = ["langgraph", "langchain_explicit", "mcp_tool", "chroma", "personalized_rag", "fallback"]
    return [{"path": key, "total": counter.get(key, 0)} for key in keys]


def build_eval_summary(case_type: str = "", limit=30):
    runs = list_eval_runs(case_type=case_type, failed_only=False, limit=limit)
    grouped = defaultdict(list)
    for item in runs:
        grouped[item["case_name"]].append(item)

    regression_rows = []
    prompt_versions = defaultdict(set)
    for case_name, case_runs in grouped.items():
        ordered_runs = sorted(case_runs, key=lambda item: item["id"], reverse=True)
        latest = ordered_runs[0]
        previous = ordered_runs[1] if len(ordered_runs) > 1 else None
        regression_rows.append(
            {
                "case_name": case_name,
                "latest_status": latest["status"],
                "latest_score": latest["score"],
                "previous_status": previous["status"] if previous else "",
                "previous_score": previous["score"] if previous else None,
                "delta_score": round(latest["score"] - previous["score"], 2) if previous else None,
                "regression": bool(previous and latest["score"] < previous["score"]),
                "latest_prompt_version": latest.get("prompt_version", ""),
                "previous_prompt_version": previous.get("prompt_version", "") if previous else "",
            }
        )
        for run in case_runs:
            if run.get("prompt_version"):
                prompt_versions[case_name].add(run["prompt_version"])

    failed_samples = [item for item in runs if item["status"] != "passed"][:8]
    passed_count = sum(1 for item in runs if item["status"] == "passed")
    return {
        "run_count": len(runs),
        "pass_rate": round((passed_count / len(runs)) * 100, 2) if runs else 0,
        "regression_report": regression_rows,
        "failed_replays": failed_samples,
        "prompt_version_compare": [
            {"case_name": case_name, "versions": sorted(list(versions))}
            for case_name, versions in prompt_versions.items()
        ],
        "runtime_path_summary": _runtime_path_summary(runs),
    }


def _select_runner(case_type: str) -> Tuple[str, RunnerType | None]:
    return case_type, CASE_RUNNERS.get(case_type)


def _run_case_for_user(user, case: AIEvaluationCase, request_payload: Dict[str, Any] | None = None):
    payload = dict(case.input_payload or {})
    if request_payload:
        payload.update(request_payload)
    case_type, runner = _select_runner(case.case_type)
    if not runner:
        return {
            "status": "error",
            "score": Decimal("0"),
            "result_payload": {},
            "trace_payload": {},
            "failure_reason": f"unsupported case type: {case_type}",
            "feature_type": case_type,
            "request_payload": payload,
        }
    outcome = runner(user, payload, case)
    outcome["request_payload"] = payload
    return outcome


def _create_run(user, case: AIEvaluationCase, outcome: Dict[str, Any]) -> AIEvaluationRun:
    return AIEvaluationRun.objects.create(
        user=user,
        case=case,
        feature_type=outcome["feature_type"],
        status=outcome["status"],
        score=outcome["score"],
        request_payload=outcome.get("request_payload") or case.input_payload or {},
        result_payload=outcome["result_payload"],
        trace_payload=outcome["trace_payload"],
        failure_reason=outcome["failure_reason"],
        runtime_snapshot=build_runtime_capabilities(),
    )


def run_evaluations_for_user(user, case_id=None, case_type="", replay_failed_only=False, limit=5):
    _ensure_default_cases()
    queryset = AIEvaluationCase.objects.filter(enabled=True)
    if case_id:
        queryset = queryset.filter(id=case_id)
    if case_type:
        queryset = queryset.filter(case_type=case_type)
    if replay_failed_only:
        failed_case_ids = list(
            AIEvaluationRun.objects.exclude(status="passed").values_list("case_id", flat=True).distinct()
        )
        queryset = queryset.filter(id__in=failed_case_ids)
    queryset = queryset.order_by("id")[: min(max(int(limit or 5), 1), 20)]

    created_runs = []
    for case in queryset:
        outcome = _run_case_for_user(user, case)
        run = _create_run(user, case, outcome)
        created_runs.append(serialize_eval_run(run))
    return created_runs


def get_eval_run_detail(user, run_id):
    run = AIEvaluationRun.objects.select_related("case").filter(user=user, id=run_id).first()
    if not run:
        raise ValueError("evaluation run not found")
    data = serialize_eval_run(run)
    data["case"] = serialize_eval_case(run.case)
    return data


def replay_eval_run(user, run_id, override_request_payload=None):
    run = AIEvaluationRun.objects.select_related("case").filter(user=user, id=run_id).first()
    if not run:
        raise ValueError("evaluation run not found")
    request_payload = dict(run.request_payload or {})
    if override_request_payload:
        request_payload.update(override_request_payload)
    outcome = _run_case_for_user(user, run.case, request_payload=request_payload)
    new_run = _create_run(user, run.case, outcome)
    return serialize_eval_run(new_run)
