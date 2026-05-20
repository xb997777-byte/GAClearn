from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List


@dataclass(frozen=True)
class WorkflowDefinition:
    feature_type: str
    required_roles: List[str] = field(default_factory=list)
    optional_roles: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    planner: str = ""
    output_validator: Callable[[Dict[str, object]], Dict[str, object]] | None = None


WORKFLOW_DEFINITIONS: Dict[str, WorkflowDefinition] = {
    "plan_replan": WorkflowDefinition(
        feature_type="plan_replan",
        required_roles=["planner", "domain_tutor", "critic"],
        optional_roles=["retriever", "tool_router"],
        allowed_tools=["get_user_plan", "get_today_task", "get_due_reviews", "get_wrong_words", "get_study_snapshot"],
        planner="planner -> tool_router -> domain_tutor -> critic",
    ),
    "rag_search": WorkflowDefinition(
        feature_type="rag_search",
        required_roles=["planner", "retriever", "domain_tutor", "critic"],
        allowed_tools=["rag_search"],
        planner="planner -> retriever -> domain_tutor -> critic",
    ),
    "vector_rag": WorkflowDefinition(
        feature_type="vector_rag",
        required_roles=["planner", "retriever", "domain_tutor", "critic"],
        allowed_tools=["vector_rag_search"],
        planner="planner -> retriever -> domain_tutor -> critic",
    ),
    "retrieval_orchestrator": WorkflowDefinition(
        feature_type="retrieval_orchestrator",
        required_roles=["planner", "retriever", "tool_router", "domain_tutor", "critic"],
        allowed_tools=["rag_search", "vector_rag_search", "structured_lookup"],
        planner="planner -> retriever -> tool_router -> domain_tutor -> critic",
    ),
    "conversation": WorkflowDefinition(
        feature_type="conversation",
        required_roles=["coordinator", "planner", "domain_tutor", "critic"],
        optional_roles=["retriever", "tool_router"],
        allowed_tools=["rag_search", "vector_rag_search", "grammar_tutor", "writing_correct", "translation_evaluate", "scenario_dialogue"],
        planner="coordinator -> planner -> retriever/tool_router -> domain_tutor -> critic",
    ),
    "study_coach": WorkflowDefinition(
        feature_type="study_coach",
        required_roles=["planner", "tool_router", "coach", "critic"],
        allowed_tools=["get_user_plan", "get_today_task", "get_due_reviews", "get_wrong_words", "get_study_snapshot"],
        planner="planner -> tool_router -> coach -> critic",
    ),
    "word_tutor": WorkflowDefinition(
        feature_type="word_tutor",
        required_roles=["planner", "tool_router", "domain_tutor", "critic"],
        allowed_tools=["word_lookup", "related_words_lookup"],
        planner="planner -> tool_router -> domain_tutor -> critic",
    ),
    "wrong_words_review": WorkflowDefinition(
        feature_type="wrong_words_review",
        required_roles=["planner", "tool_router", "coach", "critic"],
        allowed_tools=["get_wrong_words", "get_study_snapshot"],
        planner="planner -> tool_router -> coach -> critic",
    ),
    "grammar_tutor": WorkflowDefinition(
        feature_type="grammar_tutor",
        required_roles=["planner", "tool_router", "domain_tutor", "critic"],
        allowed_tools=["grammar_sentence_lookup", "grammar_point_lookup"],
        planner="planner -> tool_router -> domain_tutor -> critic",
    ),
    "writing_correct": WorkflowDefinition(
        feature_type="writing_correct",
        required_roles=["planner", "tool_router", "domain_tutor", "critic"],
        allowed_tools=["internal_tools"],
        planner="planner -> tool_router -> domain_tutor -> critic",
    ),
    "writing_prompt": WorkflowDefinition(
        feature_type="writing_prompt",
        required_roles=["planner", "tool_router", "domain_tutor", "critic"],
        allowed_tools=["internal_tools"],
        planner="planner -> tool_router -> domain_tutor -> critic",
    ),
    "translation_evaluate": WorkflowDefinition(
        feature_type="translation_evaluate",
        required_roles=["planner", "tool_router", "domain_tutor", "critic"],
        allowed_tools=["internal_tools"],
        planner="planner -> tool_router -> domain_tutor -> critic",
    ),
    "scenario_dialogue": WorkflowDefinition(
        feature_type="scenario_dialogue",
        required_roles=["planner", "tool_router", "coach", "critic"],
        allowed_tools=["internal_tools"],
        planner="planner -> tool_router -> coach -> critic",
    ),
    "grammar_guide": WorkflowDefinition(
        feature_type="grammar_guide",
        required_roles=["planner", "tool_router", "coach", "critic"],
        allowed_tools=["grammar_catalog_lookup"],
        planner="planner -> tool_router -> coach -> critic",
    ),
    "study_report": WorkflowDefinition(
        feature_type="study_report",
        required_roles=["planner", "tool_router", "coach", "critic"],
        allowed_tools=["get_study_snapshot", "get_progress_stats", "get_wrong_words"],
        planner="planner -> tool_router -> coach -> critic",
    ),
}


def get_workflow_definition(feature_type: str) -> WorkflowDefinition:
    return WORKFLOW_DEFINITIONS.get(feature_type, WorkflowDefinition(feature_type=feature_type))
