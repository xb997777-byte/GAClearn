from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable, Dict, List

from django.db.models import Q
from django.utils import timezone

from apps.books.models import Word
from apps.grammar.models import GrammarPoint
from apps.grammar.services import get_sentence_detail
from apps.learn.models import WordProgress
from apps.learn.services import get_word_detail
from apps.plans.services import build_today_task_payload, get_manageable_plan, serialize_plan
from apps.review.services import list_wrong_words
from apps.stats.services import build_overview, build_trend
from apps.users.models import WxUser

from ..learning_assistant import (
    build_grammar_guide,
    build_multi_agent_brief,
    evaluate_rag_recall,
    generate_writing_prompt,
    list_scenario_templates,
    run_rag_search,
    run_vector_rag_search,
    summarize_ai_quality,
)
from ..learning_reports import list_study_reports
from ..observability import build_observability_summary
from ..profile_memory import get_or_refresh_profile_memory, serialize_profile_memory
from ..rag.sync_service import sync_rag_index


@dataclass(frozen=True)
class MCPToolDef:
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass(frozen=True)
class MCPResourceDef:
    uri: str
    name: str
    mime_type: str
    description: str = ""
    user_bound: bool = False
    example_uri: str = ""


@dataclass(frozen=True)
class MCPPromptDef:
    name: str
    description: str
    arguments: List[Dict[str, Any]]


RESOURCE_URI_PATTERN = re.compile(r"^(?P<scheme>[a-z_]+)://(?P<kind>[a-z\-]+)/(?P<value>.+)$")


def _serialize_grammar_point(point: GrammarPoint) -> Dict[str, Any]:
    return {
        "id": point.id,
        "code": point.code,
        "title": point.title,
        "category": point.category,
        "difficulty": point.difficulty,
        "description": point.description,
        "learning_tip": point.learning_tip,
        "practice_prompt": point.practice_prompt,
    }


def _serialize_due_progress(progress: WordProgress) -> Dict[str, Any]:
    word = progress.word
    return {
        "word_id": word.id,
        "word": word.word,
        "meaning_cn": word.meaning_cn,
        "part_of_speech": word.part_of_speech,
        "mastery_level": progress.mastery_level,
        "wrong_count": progress.wrong_count,
        "review_due_at": progress.review_due_at,
    }


def _search_words(args: Dict[str, Any]) -> Dict[str, Any]:
    keyword = str((args or {}).get("keyword") or "").strip()
    limit = min(max(int((args or {}).get("limit") or 10), 1), 30)
    queryset = Word.objects.select_related("book").all()
    if keyword:
        queryset = queryset.filter(word__icontains=keyword)
    return {
        "list": [
            {
                "id": item.id,
                "word": item.word,
                "meaning_cn": item.meaning_cn,
                "part_of_speech": item.part_of_speech,
                "book": {"id": item.book_id, "name": item.book.name},
            }
            for item in queryset.order_by("word", "id")[:limit]
        ]
    }


def _search_grammar_points(args: Dict[str, Any]) -> Dict[str, Any]:
    keyword = str((args or {}).get("keyword") or "").strip()
    limit = min(max(int((args or {}).get("limit") or 10), 1), 30)
    queryset = GrammarPoint.objects.filter(status="active")
    if keyword:
        queryset = queryset.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))
    return {
        "list": [
            {
                "id": item.id,
                "code": item.code,
                "title": item.title,
                "category": item.category,
                "difficulty": item.difficulty,
                "description": item.description,
                "learning_tip": item.learning_tip,
            }
            for item in queryset.order_by("sort_order", "id")[:limit]
        ]
    }


def _tool_get_user_plan(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return {"plan": serialize_plan(get_manageable_plan(user))}


def _tool_get_today_task(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return build_today_task_payload(user)


def _tool_get_due_reviews(user, args: Dict[str, Any]) -> Dict[str, Any]:
    limit = min(max(int(args.get("limit") or 10), 1), 30)
    queryset = (
        WordProgress.objects.select_related("word")
        .filter(user=user, review_due_at__isnull=False, review_due_at__lte=timezone.now())
        .order_by("review_due_at", "-wrong_count", "id")[:limit]
    )
    return {"list": [_serialize_due_progress(item) for item in queryset]}


def _tool_get_wrong_words(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return {"list": list_wrong_words(user)}


def _tool_search_words(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return _search_words(args)


def _tool_get_word_detail(user, args: Dict[str, Any]) -> Dict[str, Any]:
    word_id = int(args.get("word_id") or args.get("id") or 0)
    if word_id <= 0:
        raise ValueError("word_id is required")
    return get_word_detail(user, word_id)


def _tool_get_study_snapshot(user, args: Dict[str, Any]) -> Dict[str, Any]:
    days = min(max(int(args.get("days") or 7), 3), 30)
    return {
        "overview": build_overview(user),
        "trend": build_trend(user, days=days),
        "today": build_today_task_payload(user),
    }


def _tool_search_grammar_points(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return _search_grammar_points(args)


def _tool_get_sentence_detail(user, args: Dict[str, Any]) -> Dict[str, Any]:
    sentence_id = int(args.get("sentence_id") or args.get("id") or 0)
    if sentence_id <= 0:
        raise ValueError("sentence_id is required")
    return get_sentence_detail(user, sentence_id)


def _tool_rag_search(user, args: Dict[str, Any]) -> Dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    return run_rag_search(query, limit=min(max(int(args.get("limit") or 6), 1), 12))


def _tool_vector_rag_search(user, args: Dict[str, Any]) -> Dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    return run_vector_rag_search(
        query,
        limit=min(max(int(args.get("limit") or 8), 1), 12),
        retrieval_mode=str(args.get("retrieval_mode") or "auto"),
        user=user,
    )


def _tool_sync_rag_index(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return sync_rag_index(
        limit=(min(max(int(args.get("limit") or 0), 1), 5000) if args.get("limit") else None),
        batch_size=min(max(int(args.get("batch_size") or 64), 1), 128),
        delete_missing=bool(args.get("delete_missing", False)),
    ).to_dict()


def _tool_evaluate_rag_recall(user, args: Dict[str, Any]) -> Dict[str, Any]:
    query = str(args.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")
    return evaluate_rag_recall(
        query,
        args.get("expected_keywords") or [],
        str(args.get("preferred_source_type") or ""),
        min(max(int(args.get("limit") or 6), 1), 12),
        user=user,
    )


def _tool_generate_writing_prompt(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return generate_writing_prompt(
        user,
        str(args.get("level") or "cet4"),
        str(args.get("topic") or ""),
        str(args.get("genre") or "essay"),
    )


def _tool_get_grammar_guide(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return build_grammar_guide(user)


def _tool_list_scenario_templates(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return {"list": list_scenario_templates()}


def _tool_get_learning_reports(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "list": list_study_reports(
            user,
            args.get("report_type", ""),
            args.get("limit", 10),
            include_compare=bool(args.get("include_compare", False)),
        )
    }


def _tool_get_multi_agent_brief(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return build_multi_agent_brief(user)


def _tool_plan_replanner(user, args: Dict[str, Any]) -> Dict[str, Any]:
    from ..graphs.plan_replanner import build_plan_replan_detail

    return build_plan_replan_detail(user, min(max(int(args.get("trend_days") or 7), 3), 14))


def _tool_get_ai_quality(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return summarize_ai_quality(user)


def _tool_get_ai_observability(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return build_observability_summary(user)


def _tool_get_profile_memory(user, args: Dict[str, Any]) -> Dict[str, Any]:
    return serialize_profile_memory(get_or_refresh_profile_memory(user))


TOOL_DEFS: List[MCPToolDef] = [
    MCPToolDef("get_user_plan", "读取当前用户学习计划。", {"type": "object", "properties": {}}),
    MCPToolDef("get_today_task", "读取今日学习任务。", {"type": "object", "properties": {}}),
    MCPToolDef(
        "get_due_reviews",
        "读取到期复习词。",
        {"type": "object", "properties": {"limit": {"type": "integer"}}},
    ),
    MCPToolDef("get_wrong_words", "读取错词本。", {"type": "object", "properties": {}}),
    MCPToolDef(
        "search_words",
        "按关键词搜索词库。",
        {"type": "object", "properties": {"keyword": {"type": "string"}, "limit": {"type": "integer"}}},
    ),
    MCPToolDef(
        "get_word_detail",
        "读取单词详情。",
        {"type": "object", "properties": {"word_id": {"type": "integer"}}, "required": ["word_id"]},
    ),
    MCPToolDef(
        "get_study_snapshot",
        "读取学习统计快照。",
        {"type": "object", "properties": {"days": {"type": "integer"}}},
    ),
    MCPToolDef(
        "search_grammar_points",
        "搜索语法点。",
        {"type": "object", "properties": {"keyword": {"type": "string"}, "limit": {"type": "integer"}}},
    ),
    MCPToolDef(
        "get_sentence_detail",
        "读取语法句子详情。",
        {"type": "object", "properties": {"sentence_id": {"type": "integer"}}, "required": ["sentence_id"]},
    ),
    MCPToolDef(
        "rag_search",
        "结构化 RAG 学习问答。",
        {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}}, "required": ["query"]},
    ),
    MCPToolDef(
        "vector_rag_search",
        "向量 / hybrid RAG 检索问答。",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer"},
                "retrieval_mode": {"type": "string", "enum": ["auto", "vector_only", "structured_only", "hybrid"]},
            },
            "required": ["query"],
        },
    ),
    MCPToolDef(
        "sync_rag_index",
        "增量同步 RAG 索引，更新新增或变更的知识 chunk。",
        {
            "type": "object",
            "properties": {
                "limit": {"type": "integer"},
                "batch_size": {"type": "integer"},
                "delete_missing": {"type": "boolean"},
            },
        },
    ),
    MCPToolDef(
        "evaluate_rag_recall",
        "评测结构化检索与轻量向量检索的召回覆盖情况。",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "expected_keywords": {"type": "array", "items": {"type": "string"}},
                "preferred_source_type": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["query"],
        },
    ),
    MCPToolDef(
        "generate_writing_prompt",
        "生成写作题、提纲、范文和评分维度。",
        {"type": "object", "properties": {"level": {"type": "string"}, "topic": {"type": "string"}, "genre": {"type": "string"}}},
    ),
    MCPToolDef("get_grammar_guide", "生成语法导学建议。", {"type": "object", "properties": {}}),
    MCPToolDef("list_scenario_templates", "读取文本情景对话任务模板。", {"type": "object", "properties": {}}),
    MCPToolDef(
        "get_learning_reports",
        "读取 AI 学习报告历史。",
        {
            "type": "object",
            "properties": {
                "report_type": {"type": "string"},
                "limit": {"type": "integer"},
                "include_compare": {"type": "boolean"},
            },
        },
    ),
    MCPToolDef("get_multi_agent_brief", "读取多老师协作简报。", {"type": "object", "properties": {}}),
    MCPToolDef(
        "plan_replanner",
        "AI plan replanner agent for today's study plan.",
        {"type": "object", "properties": {"trend_days": {"type": "integer"}}},
    ),
    MCPToolDef("get_ai_quality", "读取 AI 质量摘要。", {"type": "object", "properties": {}}),
    MCPToolDef("get_ai_observability", "读取 AI 运行日志、缓存和限流摘要。", {"type": "object", "properties": {}}),
    MCPToolDef("get_profile_memory", "Read AI long-term learner profile memory.", {"type": "object", "properties": {}}),
]

RESOURCE_DEFS: List[MCPResourceDef] = [
    MCPResourceDef(
        "grammar://point/{id}",
        "语法点",
        "application/json",
        description="读取单个语法点详情，用于规则解释、例句关联与教学展示。",
        example_uri="grammar://point/1",
    ),
    MCPResourceDef(
        "grammar://sentence/{id}",
        "语法句子",
        "application/json",
        description="读取单条语法句子详情，包括句子、翻译、分析和归属语法点。",
        example_uri="grammar://sentence/1",
    ),
    MCPResourceDef(
        "word://detail/{id}",
        "单词详情",
        "application/json",
        description="读取单词详情，用于词义、例句、学习状态与词书归属展示。",
        example_uri="word://detail/1",
    ),
    MCPResourceDef(
        "user://profile/{user_id}",
        "用户画像",
        "application/json",
        description="读取用户学习画像、概览与趋势摘要。",
        user_bound=True,
        example_uri="user://profile/self",
    ),
    MCPResourceDef(
        "user://weak-points/{user_id}",
        "用户薄弱点",
        "application/json",
        description="读取用户近期薄弱点，包括错词模式、复习压力和薄弱词类。",
        user_bound=True,
        example_uri="user://weak-points/self",
    ),
    MCPResourceDef(
        "ai://observability/{user_id}",
        "AI观测摘要",
        "application/json",
        description="读取当前用户的 AI 请求日志、缓存命中和近期运行摘要。",
        user_bound=True,
        example_uri="ai://observability/self",
    ),
    MCPResourceDef(
        "ai://profile-memory/{user_id}",
        "AI Profile Memory",
        "application/json",
        description="读取 AI 长期记忆中的学习画像、偏好模式和近期重点词。",
        user_bound=True,
        example_uri="ai://profile-memory/self",
    ),
]

PROMPT_DEFS: List[MCPPromptDef] = [
    MCPPromptDef("grammar_tutor", "基于句子、语法点和相似例句生成讲解。", [{"name": "sentence", "required": True}, {"name": "question", "required": False}]),
    MCPPromptDef("word_tutor", "基于词库和学习状态生成 AI 讲词。", [{"name": "word_id", "required": True}]),
    MCPPromptDef("study_coach", "基于计划、统计、错词和复习压力生成学习建议。", [{"name": "trend_days", "required": False}]),
    MCPPromptDef("wrong_word_review", "对错词本进行归因和复习建议。", [{"name": "limit", "required": False}]),
    MCPPromptDef("writing_prompt", "生成写作题、范文和评分维度。", [{"name": "level", "required": False}, {"name": "topic", "required": False}]),
    MCPPromptDef("scenario_dialogue", "文本情景对话陪练，不包含发音评分。", [{"name": "scenario", "required": False}, {"name": "user_message", "required": True}]),
    MCPPromptDef("plan_replanner", "AI study plan replanner agent prompt.", [{"name": "trend_days", "required": False}]),
]

TOOL_EXECUTORS: Dict[str, Callable[[Any, Dict[str, Any]], Dict[str, Any]]] = {
    "get_user_plan": _tool_get_user_plan,
    "get_today_task": _tool_get_today_task,
    "get_due_reviews": _tool_get_due_reviews,
    "get_wrong_words": _tool_get_wrong_words,
    "search_words": _tool_search_words,
    "get_word_detail": _tool_get_word_detail,
    "get_study_snapshot": _tool_get_study_snapshot,
    "search_grammar_points": _tool_search_grammar_points,
    "get_sentence_detail": _tool_get_sentence_detail,
    "rag_search": _tool_rag_search,
    "vector_rag_search": _tool_vector_rag_search,
    "sync_rag_index": _tool_sync_rag_index,
    "evaluate_rag_recall": _tool_evaluate_rag_recall,
    "generate_writing_prompt": _tool_generate_writing_prompt,
    "get_grammar_guide": _tool_get_grammar_guide,
    "list_scenario_templates": _tool_list_scenario_templates,
    "get_learning_reports": _tool_get_learning_reports,
    "get_multi_agent_brief": _tool_get_multi_agent_brief,
    "plan_replanner": _tool_plan_replanner,
    "get_ai_quality": _tool_get_ai_quality,
    "get_ai_observability": _tool_get_ai_observability,
    "get_profile_memory": _tool_get_profile_memory,
}


def _resolve_user_resource_target(user, raw_value: str) -> int:
    value = str(raw_value or "").strip().lower()
    if value in {"self", "me", "current"}:
        if not getattr(user, "id", None):
            raise ValueError("user context is required for this resource")
        return int(user.id)
    target = int(raw_value)
    if getattr(user, "id", None) and int(user.id) != target and not getattr(user, "is_mcp_stdio", False):
        raise ValueError("resource access denied for another user")
    return target


def _read_grammar_point_resource(_user, raw_value: str) -> Dict[str, Any]:
    point = GrammarPoint.objects.filter(id=int(raw_value), status="active").first()
    if not point:
        raise ValueError("grammar point not found")
    return {
        "resource_type": "grammar_point",
        "item": _serialize_grammar_point(point),
    }


def _read_grammar_sentence_resource(user, raw_value: str) -> Dict[str, Any]:
    return {
        "resource_type": "grammar_sentence",
        "item": get_sentence_detail(user, int(raw_value)),
    }


def _read_word_detail_resource(user, raw_value: str) -> Dict[str, Any]:
    return {
        "resource_type": "word_detail",
        "item": get_word_detail(user, int(raw_value)),
    }


def _read_user_profile_resource(user, raw_value: str) -> Dict[str, Any]:
    user_id = _resolve_user_resource_target(user, raw_value)
    target_user = WxUser.objects.filter(id=user_id).first()
    if not target_user:
        raise ValueError("user not found")
    return {
        "resource_type": "user_profile",
        "item": {
            "user_id": target_user.id,
            "nickname": target_user.nickname,
            "overview": build_overview(target_user),
            "trend": build_trend(target_user, days=7),
            "today_task": build_today_task_payload(target_user),
        },
    }


def _read_user_weak_points_resource(user, raw_value: str) -> Dict[str, Any]:
    user_id = _resolve_user_resource_target(user, raw_value)
    target_user = WxUser.objects.filter(id=user_id).first()
    if not target_user:
        raise ValueError("user not found")
    bundle = build_multi_agent_brief(target_user).get("snapshot") or {}
    return {
        "resource_type": "user_weak_points",
        "item": {
            "user_id": target_user.id,
            "wrong_patterns": bundle.get("wrong_patterns") or [],
            "priority_wrong_words": bundle.get("priority_wrong_words") or [],
            "due_review_words": bundle.get("due_review_words") or [],
            "adaptive": bundle.get("adaptive") or {},
        },
    }


def _read_ai_observability_resource(user, raw_value: str) -> Dict[str, Any]:
    user_id = _resolve_user_resource_target(user, raw_value)
    target_user = WxUser.objects.filter(id=user_id).first()
    if not target_user:
        raise ValueError("user not found")
    return {
        "resource_type": "ai_observability",
        "item": build_observability_summary(target_user),
    }


def _read_profile_memory_resource(user, raw_value: str) -> Dict[str, Any]:
    user_id = _resolve_user_resource_target(user, raw_value)
    target_user = WxUser.objects.filter(id=user_id).first()
    if not target_user:
        raise ValueError("user not found")
    return {
        "resource_type": "profile_memory",
        "item": serialize_profile_memory(get_or_refresh_profile_memory(target_user)),
    }


RESOURCE_READERS: Dict[str, Callable[[Any, str], Dict[str, Any]]] = {
    "grammar://point/{id}": _read_grammar_point_resource,
    "grammar://sentence/{id}": _read_grammar_sentence_resource,
    "word://detail/{id}": _read_word_detail_resource,
    "user://profile/{user_id}": _read_user_profile_resource,
    "user://weak-points/{user_id}": _read_user_weak_points_resource,
    "ai://observability/{user_id}": _read_ai_observability_resource,
    "ai://profile-memory/{user_id}": _read_profile_memory_resource,
}


def list_tool_defs() -> List[Dict[str, Any]]:
    return [
        {"name": item.name, "description": item.description, "input_schema": item.input_schema}
        for item in TOOL_DEFS
    ]


def list_resource_defs() -> List[Dict[str, Any]]:
    return [
        {
            "uri": item.uri,
            "name": item.name,
            "mime_type": item.mime_type,
            "description": item.description,
            "user_bound": item.user_bound,
            "example_uri": item.example_uri,
        }
        for item in RESOURCE_DEFS
    ]


def list_prompt_defs() -> List[Dict[str, Any]]:
    return [{"name": item.name, "description": item.description, "arguments": item.arguments} for item in PROMPT_DEFS]


def execute_tool(user, tool_name: str, args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    executor = TOOL_EXECUTORS.get(tool_name)
    if not executor:
        raise ValueError(f"unsupported mcp tool: {tool_name}")
    return executor(user, args or {})


def read_resource(user, resource_uri: str) -> Dict[str, Any]:
    resource_uri = str(resource_uri or "").strip()
    if not resource_uri:
        raise ValueError("resource_uri is required")

    for resource in RESOURCE_DEFS:
        template = resource.uri
        pattern = re.escape(template).replace(r"\{id\}", r"(?P<id>[^/]+)").replace(r"\{user_id\}", r"(?P<user_id>[^/]+)")
        matched = re.match(f"^{pattern}$", resource_uri)
        if not matched:
            continue
        reader = RESOURCE_READERS.get(template)
        if not reader:
            raise ValueError(f"resource reader not implemented: {template}")
        value = matched.groupdict().get("id") or matched.groupdict().get("user_id") or ""
        return {
            "uri": resource_uri,
            "template": template,
            "name": resource.name,
            "mime_type": resource.mime_type,
            "description": resource.description,
            "data": reader(user, value),
        }
    raise ValueError(f"unsupported resource uri: {resource_uri}")
