from __future__ import annotations

from typing import Callable, Dict

from .models import AIAsyncRun


RuntimeHandler = Callable[[AIAsyncRun], AIAsyncRun]

_REGISTRY: Dict[str, RuntimeHandler] = {}


def register_runtime(feature_type: str, handler: RuntimeHandler) -> None:
    _REGISTRY[feature_type] = handler


def get_runtime_handler(feature_type: str) -> RuntimeHandler | None:
    return _REGISTRY.get(feature_type)


def execute_registered_run(run: AIAsyncRun) -> AIAsyncRun:
    handler = get_runtime_handler(run.feature_type)
    if not handler:
        raise ValueError(f"unsupported runtime feature: {run.feature_type}")
    return handler(run)


def bootstrap_runtime_registry() -> None:
    from .runtime_features import (
        execute_conversation_run,
        execute_grammar_guide_run,
        execute_grammar_tutor_run,
        execute_mcp_tool_call_run,
        execute_plan_replan_run,
        execute_rag_search_run,
        execute_retrieval_orchestrator_run,
        execute_scenario_dialogue_run,
        execute_study_coach_run,
        execute_study_report_run,
        execute_translation_evaluate_run,
        execute_vector_rag_run,
        execute_word_tutor_run,
        execute_writing_prompt_run,
        execute_writing_correct_run,
        execute_wrong_words_review_run,
    )

    register_runtime("plan_replan", execute_plan_replan_run)
    register_runtime("conversation", execute_conversation_run)
    register_runtime("rag_search", execute_rag_search_run)
    register_runtime("vector_rag", execute_vector_rag_run)
    register_runtime("retrieval_orchestrator", execute_retrieval_orchestrator_run)
    register_runtime("study_coach", execute_study_coach_run)
    register_runtime("word_tutor", execute_word_tutor_run)
    register_runtime("wrong_words_review", execute_wrong_words_review_run)
    register_runtime("grammar_tutor", execute_grammar_tutor_run)
    register_runtime("writing_correct", execute_writing_correct_run)
    register_runtime("writing_prompt", execute_writing_prompt_run)
    register_runtime("translation_evaluate", execute_translation_evaluate_run)
    register_runtime("scenario_dialogue", execute_scenario_dialogue_run)
    register_runtime("grammar_guide", execute_grammar_guide_run)
    register_runtime("study_report", execute_study_report_run)
    register_runtime("mcp_tool_call", execute_mcp_tool_call_run)
