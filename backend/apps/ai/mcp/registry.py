from __future__ import annotations

from dataclasses import dataclass
import re
from time import monotonic
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
from ..agent_runtime import create_approval, maybe_require_approval
from ..observability import build_observability_summary
from ..profile_memory import get_or_refresh_profile_memory, serialize_profile_memory
from ..rag.sync_service import sync_rag_index
from ..response_contracts import normalize_feature_contract
from ..evidence import attach_feature_evidence


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
TOOL_FEATURE_TYPE_MAP = {
    "rag_search": "rag_search",
    "vector_rag_search": "vector_rag",
    "evaluate_rag_recall": "rag_recall_eval",
    "generate_writing_prompt": "writing_prompt",
    "get_grammar_guide": "grammar_guide",
    "get_multi_agent_brief": "multi_agent_brief",
    "plan_replanner": "plan_replan",
}

TOOL_AGENT_META: Dict[str, Dict[str, Any]] = {
    "get_user_plan": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "get_today_task": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "get_due_reviews": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "get_wrong_words": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "search_words": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "get_word_detail": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "get_study_snapshot": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 12000},
    "search_grammar_points": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "get_sentence_detail": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "rag_search": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 30000},
    "vector_rag_search": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 45000},
    "sync_rag_index": {"agent_enabled": True, "safe_for_agent": True, "mutation": True, "requires_approval": True, "tool_timeout_ms": 120000},
    "evaluate_rag_recall": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 30000},
    "generate_writing_prompt": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 30000},
    "get_grammar_guide": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 15000},
    "list_scenario_templates": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "get_learning_reports": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 15000},
    "get_multi_agent_brief": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 15000},
    "plan_replanner": {"agent_enabled": True, "safe_for_agent": True, "mutation": True, "requires_approval": True, "tool_timeout_ms": 60000},
    "get_ai_quality": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "get_ai_observability": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
    "get_profile_memory": {"agent_enabled": True, "safe_for_agent": True, "mutation": False, "requires_approval": False, "tool_timeout_ms": 8000},
}

TOOL_UI_META: Dict[str, Dict[str, Any]] = {
    "get_user_plan": {
        "skill_id": "study_plan.current",
        "version": "1.0.0",
        "permissions": ["user:plan:read"],
        "display_name": "当前学习计划",
        "category": "学习计划",
        "summary": "读取你当前正在执行的学习计划。",
        "details": "适合先确认当前词书、每日目标、计划状态和学习节奏是否符合预期。",
        "example_args": {},
        "result_preview_hint": "返回计划概览、词书和每日学习配置。",
        "ui_order": 10,
    },
    "get_today_task": {
        "skill_id": "study_plan.today_task",
        "version": "1.0.0",
        "permissions": ["user:plan:read"],
        "display_name": "今日学习任务",
        "category": "学习计划",
        "summary": "查看今天应该学什么、复习什么。",
        "details": "适合进入学习前先快速确认今日任务量、待学词和待复习词数量。",
        "example_args": {},
        "result_preview_hint": "返回今天的新词、复习任务和整体进度。",
        "ui_order": 20,
    },
    "get_due_reviews": {
        "skill_id": "study_plan.due_reviews",
        "version": "1.0.0",
        "permissions": ["user:review:read"],
        "display_name": "到期复习词",
        "category": "学习计划",
        "summary": "列出当前已经到期、应该优先复习的单词。",
        "details": "适合复习前先拉出一批即将遗忘或已经到期的单词，集中处理。",
        "example_args": {"limit": 10},
        "result_preview_hint": "返回一组待复习单词及其掌握度、错词次数和到期时间。",
        "ui_order": 30,
    },
    "get_wrong_words": {
        "skill_id": "study_plan.wrong_words",
        "version": "1.0.0",
        "permissions": ["user:review:read"],
        "display_name": "错词本",
        "category": "学习计划",
        "summary": "查看你最近答错过的单词。",
        "details": "适合做错题回看，或给后续 AI 讲解、专项复习提供输入。",
        "example_args": {},
        "result_preview_hint": "返回错词列表与最近错误记录。",
        "ui_order": 40,
    },
    "get_study_snapshot": {
        "skill_id": "study_plan.snapshot",
        "version": "1.0.0",
        "permissions": ["user:stats:read"],
        "display_name": "学习快照",
        "category": "学习计划",
        "summary": "查看近几天学习概览、趋势和今日任务。",
        "details": "适合做学习复盘或给 AI 生成学习建议前先拉取一个整体快照。",
        "example_args": {"days": 7},
        "result_preview_hint": "返回概览统计、趋势曲线数据和今日任务。",
        "ui_order": 50,
    },
    "plan_replanner": {
        "skill_id": "study_plan.replanner",
        "version": "1.0.0",
        "permissions": ["user:plan:read", "user:review:read", "ai:plan:write_suggestion"],
        "display_name": "AI 重规划今日计划",
        "category": "学习计划",
        "summary": "让 AI 结合计划、趋势和错词本重排今天的学习节奏。",
        "details": "适合觉得今日任务太重、太轻或需要按当前状态重新安排时使用。",
        "example_args": {"trend_days": 7},
        "result_preview_hint": "返回建议的日目标、执行顺序、时间块和理由。",
        "ui_order": 60,
    },
    "search_words": {
        "skill_id": "vocab.search",
        "version": "1.0.0",
        "permissions": ["catalog:words:read"],
        "display_name": "搜索词汇",
        "category": "词汇/语法",
        "summary": "按关键词搜索词库。",
        "details": "适合先定位单词，再继续查看单词详情、例句和词书归属。",
        "example_args": {"keyword": "important", "limit": 8},
        "result_preview_hint": "返回命中的单词列表。",
        "ui_order": 110,
    },
    "get_word_detail": {
        "skill_id": "vocab.detail",
        "version": "1.0.0",
        "permissions": ["catalog:words:read"],
        "display_name": "单词详情",
        "category": "词汇/语法",
        "summary": "查看某个单词的详细信息。",
        "details": "支持输入单词 ID 或关键词，适合查询词义、例句、学习状态和词书归属。",
        "example_args": {"keyword": "important"},
        "result_preview_hint": "返回单词讲解、例句和学习状态。",
        "ui_order": 120,
    },
    "search_grammar_points": {
        "skill_id": "grammar.search",
        "version": "1.0.0",
        "permissions": ["catalog:grammar:read"],
        "display_name": "搜索语法点",
        "category": "词汇/语法",
        "summary": "按关键词搜索语法点。",
        "details": "适合先定位到相关语法规则，再继续看例句或生成语法导学。",
        "example_args": {"keyword": "定语从句", "limit": 8},
        "result_preview_hint": "返回命中的语法点列表。",
        "ui_order": 130,
    },
    "get_sentence_detail": {
        "skill_id": "grammar.sentence_detail",
        "version": "1.0.0",
        "permissions": ["catalog:grammar:read"],
        "display_name": "语法句子详情",
        "category": "词汇/语法",
        "summary": "查看某条语法例句的详细解释。",
        "details": "适合围绕具体例句理解语法点、翻译和句子分析。",
        "example_args": {"sentence_id": 1},
        "result_preview_hint": "返回例句、翻译、分析和关联语法点。",
        "ui_order": 140,
    },
    "get_grammar_guide": {
        "skill_id": "grammar.guide",
        "version": "1.0.0",
        "permissions": ["catalog:grammar:read", "user:stats:read"],
        "display_name": "语法导学建议",
        "category": "词汇/语法",
        "summary": "根据你的近期情况生成语法导学建议。",
        "details": "适合想知道最近该优先补哪些语法薄弱点时使用。",
        "example_args": {},
        "result_preview_hint": "返回语法建议、重点和学习路径。",
        "ui_order": 150,
    },
    "rag_search": {
        "skill_id": "rag.structured",
        "version": "1.0.0",
        "permissions": ["rag:query"],
        "display_name": "结构化资料问答",
        "category": "RAG 问答",
        "summary": "优先用词条、语法点和例句表回答你的问题。",
        "details": "适合查词义区别、固定规则、例句和明确的语法知识点。",
        "example_args": {"query": "important 和 significant 的区别是什么？", "limit": 6},
        "result_preview_hint": "返回基于结构化知识的答案和依据点。",
        "ui_order": 210,
    },
    "vector_rag_search": {
        "skill_id": "rag.hybrid",
        "version": "1.0.0",
        "permissions": ["rag:query"],
        "display_name": "智能资料问答",
        "category": "RAG 问答",
        "summary": "默认使用 hybrid 检索，直接给出更自然的资料型回答。",
        "details": "适合学习问答主入口。系统会结合结构化命中、向量召回、个性化资料和重排结果回答。",
        "example_args": {
            "query": "important 和 significant 怎么区分？",
            "limit": 6,
            "retrieval_mode": "hybrid",
        },
        "result_preview_hint": "返回直接答案、要点、追问建议和参考来源。",
        "ui_order": 220,
    },
    "sync_rag_index": {
        "skill_id": "rag.sync",
        "version": "1.0.0",
        "permissions": ["rag:index:write"],
        "display_name": "同步 RAG 索引",
        "category": "RAG 问答",
        "summary": "把新增或修改过的知识块增量写入索引。",
        "details": "适合更新词库、语法或项目文档后进行增量同步，不做整库重建。",
        "example_args": {"batch_size": 64, "delete_missing": False},
        "result_preview_hint": "返回同步条数、跳过条数和当前索引统计。",
        "ui_order": 230,
    },
    "evaluate_rag_recall": {
        "skill_id": "rag.eval",
        "version": "1.0.0",
        "permissions": ["rag:query", "rag:eval"],
        "display_name": "评测资料召回",
        "category": "RAG 问答",
        "summary": "比较结构化与向量检索对当前问题的覆盖效果。",
        "details": "适合做技术调试或验证当前索引质量，不建议作为普通用户主入口。",
        "example_args": {
            "query": "important 和 significant 怎么区分？",
            "expected_keywords": ["important", "significant", "example"],
            "preferred_source_type": "word",
            "limit": 6,
        },
        "result_preview_hint": "返回诊断结果、覆盖率和建议策略。",
        "ui_order": 240,
    },
    "generate_writing_prompt": {
        "skill_id": "writing.prompt",
        "version": "1.0.0",
        "permissions": ["ai:writing:generate"],
        "display_name": "生成写作任务",
        "category": "写作/场景",
        "summary": "生成写作题目、提纲、范文和评分维度。",
        "details": "适合需要作文练习主题、结构提示和写作方向时使用。",
        "example_args": {"level": "cet4", "topic": "How to build a steady English learning routine", "genre": "essay"},
        "result_preview_hint": "返回写作目标、提纲、范文和评分标准。",
        "ui_order": 310,
    },
    "list_scenario_templates": {
        "skill_id": "scenario.templates",
        "version": "1.0.0",
        "permissions": ["catalog:scenario:read"],
        "display_name": "情景对话模板",
        "category": "写作/场景",
        "summary": "查看可直接使用的英语情景对话模板。",
        "details": "适合先挑一个场景，再进入文本情景对话或口语陪练。",
        "example_args": {},
        "result_preview_hint": "返回场景列表、任务说明和起手句。",
        "ui_order": 320,
    },
    "get_learning_reports": {
        "skill_id": "ops.learning_reports",
        "version": "1.0.0",
        "permissions": ["user:reports:read"],
        "display_name": "学习报告历史",
        "category": "系统观测",
        "summary": "查看 AI 学习报告和历史记录。",
        "details": "适合回看阶段性学习总结，或比较不同时间段的变化。",
        "example_args": {"limit": 5, "include_compare": True},
        "result_preview_hint": "返回学习报告列表和对比信息。",
        "ui_order": 410,
    },
    "get_multi_agent_brief": {
        "skill_id": "ops.multi_agent_brief",
        "version": "1.0.0",
        "permissions": ["ai:demo:read"],
        "display_name": "多老师协作简报",
        "category": "系统观测",
        "summary": "查看多 Agent 协作视角下的学习简报。",
        "details": "适合做功能展示，查看多角色对你的学习状态给出的拆分建议。",
        "example_args": {},
        "result_preview_hint": "返回角色职责、协作流和简报结果。",
        "ui_order": 420,
    },
    "get_ai_quality": {
        "skill_id": "ops.ai_quality",
        "version": "1.0.0",
        "permissions": ["ai:ops:read"],
        "display_name": "AI 质量摘要",
        "category": "系统观测",
        "summary": "查看近期 AI 请求与缓存质量摘要。",
        "details": "适合观察系统是否稳定、缓存是否生效，以及近期整体使用情况。",
        "example_args": {},
        "result_preview_hint": "返回请求量、缓存命中和质量摘要。",
        "ui_order": 430,
    },
    "get_ai_observability": {
        "skill_id": "ops.ai_observability",
        "version": "1.0.0",
        "permissions": ["ai:ops:read"],
        "display_name": "AI 运行观测",
        "category": "系统观测",
        "summary": "查看最近的 AI 运行日志、状态和运行路径。",
        "details": "适合技术调试或复盘失败请求，普通用户通常不需要频繁使用。",
        "example_args": {},
        "result_preview_hint": "返回运行日志、状态统计和路径摘要。",
        "ui_order": 440,
    },
    "get_profile_memory": {
        "skill_id": "ops.profile_memory",
        "version": "1.0.0",
        "permissions": ["user:memory:read"],
        "display_name": "AI 学习画像",
        "category": "系统观测",
        "summary": "读取 AI 长期记忆中的学习画像。",
        "details": "适合查看 AI 当前记住了你的哪些偏好、近期重点词和学习模式。",
        "example_args": {},
        "result_preview_hint": "返回学习画像、偏好模式和近期重点词。",
        "ui_order": 450,
    },
}


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
    keyword = str((args or {}).get("keyword") or args.get("word") or "").strip()

    resolved_word = None
    resolution_message = ""

    if word_id > 0:
        resolved_word = Word.objects.filter(id=word_id).first()
        if resolved_word is None:
            resolution_message = f"word_id={word_id} 不存在，已自动回退到可用词条。"

    if resolved_word is None and keyword:
        resolved_word = (
            Word.objects.filter(word__iexact=keyword).first()
            or Word.objects.filter(word__icontains=keyword).order_by("id").first()
        )
        if resolved_word is not None and not resolution_message:
            resolution_message = f"已根据关键词“{keyword}”匹配词条。"

    if resolved_word is None:
        current_plan = get_manageable_plan(user)
        if current_plan and getattr(current_plan, "book_id", None):
            resolved_word = Word.objects.filter(book_id=current_plan.book_id).order_by("order_in_book", "id").first()
            if resolved_word is not None and not resolution_message:
                resolution_message = "已回退到当前计划词书中的可用词条。"

    if resolved_word is None:
        resolved_word = Word.objects.order_by("id").first()
        if resolved_word is not None and not resolution_message:
            resolution_message = "已回退到词库中的可用词条。"

    if resolved_word is None:
        raise ValueError("word not found")

    result = get_word_detail(user, resolved_word.id)
    if resolution_message:
        result["_mcp_resolution"] = {
            "requested_word_id": word_id or None,
            "requested_keyword": keyword or "",
            "resolved_word_id": resolved_word.id,
            "message": resolution_message,
        }
    return result


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
        retrieval_mode=str(args.get("retrieval_mode") or "hybrid"),
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
    from ..graphs.plan_replanner import build_fast_plan_replan_detail

    return build_fast_plan_replan_detail(user, min(max(int(args.get("trend_days") or 7), 3), 14))


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
        {
            "type": "object",
            "properties": {
                "word_id": {"type": "integer"},
                "keyword": {"type": "string"},
            },
        },
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
        "AI 重规划今日学习计划。",
        {"type": "object", "properties": {"trend_days": {"type": "integer"}}},
    ),
    MCPToolDef("get_ai_quality", "读取 AI 质量摘要。", {"type": "object", "properties": {}}),
    MCPToolDef("get_ai_observability", "读取 AI 运行日志、缓存和限流摘要。", {"type": "object", "properties": {}}),
    MCPToolDef("get_profile_memory", "读取 AI 长期记忆中的学习画像。", {"type": "object", "properties": {}}),
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
        "AI 学习画像",
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
    MCPPromptDef("plan_replanner", "AI 重规划今日学习计划的提示模板。", [{"name": "trend_days", "required": False}]),
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
        {
            "name": item.name,
            "description": item.description,
            "input_schema": item.input_schema,
            "skill_id": (TOOL_UI_META.get(item.name) or {}).get("skill_id") or item.name,
            "version": (TOOL_UI_META.get(item.name) or {}).get("version") or "1.0.0",
            "display_name": (TOOL_UI_META.get(item.name) or {}).get("display_name") or item.description,
            "category": (TOOL_UI_META.get(item.name) or {}).get("category") or "系统观测",
            "summary": (TOOL_UI_META.get(item.name) or {}).get("summary") or item.description,
            "details": (TOOL_UI_META.get(item.name) or {}).get("details") or item.description,
            "example_args": (TOOL_UI_META.get(item.name) or {}).get("example_args") or {},
            "result_preview_hint": (TOOL_UI_META.get(item.name) or {}).get("result_preview_hint") or "",
            "ui_order": int((TOOL_UI_META.get(item.name) or {}).get("ui_order") or 999),
            "permissions": (TOOL_UI_META.get(item.name) or {}).get("permissions") or [],
            "agent_enabled": bool((TOOL_AGENT_META.get(item.name) or {}).get("agent_enabled", False)),
            "safe_for_agent": bool((TOOL_AGENT_META.get(item.name) or {}).get("safe_for_agent", False)),
            "mutation": bool((TOOL_AGENT_META.get(item.name) or {}).get("mutation", False)),
            "requires_approval": bool((TOOL_AGENT_META.get(item.name) or {}).get("requires_approval", False)),
            "tool_timeout_ms": int((TOOL_AGENT_META.get(item.name) or {}).get("tool_timeout_ms") or 15000),
        }
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
    result = executor(user, args or {})
    feature_type = TOOL_FEATURE_TYPE_MAP.get(tool_name, "")
    if feature_type and isinstance(result, dict):
        attach_feature_evidence(feature_type, result)
        normalize_feature_contract(feature_type, result)
    return result


def get_tool_agent_meta(tool_name: str) -> Dict[str, Any]:
    return dict(TOOL_AGENT_META.get(tool_name) or {})


def execute_agent_safe_tool(
    user,
    tool_name: str,
    args: Dict[str, Any] | None = None,
    *,
    feature_type: str = "",
    allowed_tools: List[str] | None = None,
    run=None,
    step=None,
) -> Dict[str, Any]:
    args = args or {}
    meta = get_tool_agent_meta(tool_name)
    if not meta:
        raise ValueError(f"unsupported mcp tool: {tool_name}")
    if allowed_tools is not None and tool_name not in allowed_tools:
        raise ValueError(f"tool not allowed for feature: {tool_name}")
    if not meta.get("agent_enabled") or not meta.get("safe_for_agent"):
        raise ValueError(f"tool not safe for agent: {tool_name}")
    if meta.get("mutation") and meta.get("requires_approval") and maybe_require_approval("settings_update"):
        if not run:
            raise ValueError(f"tool requires approval: {tool_name}")
        approval = (
            run.approvals.filter(action_type=f"mcp_tool:{tool_name}")
            .order_by("-id")
            .first()
        )
        if approval and approval.status == "approved":
            approval = None
        elif approval and approval.status == "rejected":
            raise ValueError(f"tool approval rejected: {tool_name}")
        elif approval and approval.status == "pending":
            return {
                "tool_name": tool_name,
                "status": "pending_approval",
                "approval": {
                    "approval_key": approval.approval_key,
                    "status": approval.status,
                    "title": approval.title,
                },
                "summary": "该工具涉及写操作，已转为待审批。",
            }
        if approval is None:
            approval = create_approval(
                run,
                feature_type=feature_type or tool_name,
                action_type=f"mcp_tool:{tool_name}",
                request_payload={"tool_name": tool_name, "args": args},
                step=step,
                title=f"MCP 工具待确认：{tool_name}",
            )
        return {
            "tool_name": tool_name,
            "status": "pending_approval",
            "approval": {
                "approval_key": approval.approval_key,
                "status": approval.status,
                "title": approval.title,
            },
            "summary": "该工具涉及写操作，已转为待审批。",
        }
    started = monotonic()
    result = execute_tool(user, tool_name, args)
    if isinstance(result, dict):
        result.setdefault("agent_safe", {})
        result["agent_safe"].update(
            {
                "tool_name": tool_name,
                "latency_ms": int((monotonic() - started) * 1000),
                "allowed_by_whitelist": True,
                "mutation": bool(meta.get("mutation")),
                "requires_approval": bool(meta.get("requires_approval")),
            }
        )
    return result


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
