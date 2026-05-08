from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Iterable, List

from django.utils import timezone

from apps.grammar.models import GrammarLearningRecord
from apps.learn.models import LearningRecord, WordProgress
from apps.plans.models import DailyTask, PlanRevision, UserPlan
from apps.review.models import ReviewRecord, WrongWord

from .knowledge_base import CHUNK_VERSION, KnowledgeChunk, _clean_text, _content_hash, _make_chunk_id, _token_summary


PERSONALIZED_CHUNK_VERSION = f"{CHUNK_VERSION}_personalized_v1"


@dataclass
class PersonalizedChunkBundle:
    chunks: List[KnowledgeChunk]
    summary: Dict[str, object]


def _now():
    return timezone.now()


def _safe_days_ago(days: int):
    return _now() - timedelta(days=max(int(days or 0), 0))


def _join_word_lines(progresses: Iterable[WordProgress], limit: int = 8) -> str:
    rows = []
    for item in list(progresses)[:limit]:
        rows.append(
            f"{item.word.word} | 中文: {item.word.meaning_cn} | 错误 {item.wrong_count} 次 | 掌握度 {item.mastery_level}"
        )
    return "\n".join(rows)


def _join_review_lines(records: Iterable[ReviewRecord], limit: int = 8) -> str:
    rows = []
    for item in list(records)[:limit]:
        rows.append(
            f"{item.word.word} | 题型: {item.question_type} | 你的答案: {item.user_answer or '空'} | 正确答案: {item.correct_answer or item.word.word}"
        )
    return "\n".join(rows)


def _build_plan_chunk(user) -> List[KnowledgeChunk]:
    chunks: List[KnowledgeChunk] = []
    plan = UserPlan.objects.select_related("book").filter(user=user, status="active").order_by("-id").first()
    task = DailyTask.objects.filter(user=user).order_by("-task_date", "-id").first()
    latest_revision = PlanRevision.objects.filter(user=user).order_by("-id").first()
    if not plan and not task and not latest_revision:
        return chunks

    content = _clean_text(
        "这是当前用户的学习计划快照。",
        (
            f"当前计划词书: {plan.book.name} | 每日目标: {plan.daily_target} | 已完成单词数: {plan.finished_word_count}"
            if plan
            else ""
        ),
        (
            f"今日任务: 新词目标 {task.new_word_target} | 复习目标 {task.review_word_target} | 已学 {task.learned_count} | 已复习 {task.reviewed_count}"
            if task
            else ""
        ),
        (
            f"最近一次计划调整: {latest_revision.summary or latest_revision.source} | patch: {latest_revision.patch_payload}"
            if latest_revision
            else ""
        ),
    )
    chunks.append(
        KnowledgeChunk(
            chunk_id=_make_chunk_id("personalized_plan", user.id, "active_plan"),
            source_type="personalized_plan",
            source_id=user.id,
            title=f"{user.nickname or user.openid} 的学习计划",
            content=content,
            metadata={
                "scope": "personalized",
                "chunk_kind": "personalized_plan",
                "user_id": user.id,
                "keyword_hints": _token_summary(content),
                "chunk_version": PERSONALIZED_CHUNK_VERSION,
            },
        )
    )
    return chunks


def _build_progress_chunks(user) -> List[KnowledgeChunk]:
    chunks: List[KnowledgeChunk] = []
    weak_progresses = list(
        WordProgress.objects.select_related("word")
        .filter(user=user)
        .order_by("-wrong_count", "mastery_level", "review_due_at", "-id")[:12]
    )
    if weak_progresses:
        content = _clean_text(
            "这是用户当前最需要重点复习的单词画像。",
            "优先关注这些高错词和低掌握度词。",
            _join_word_lines(weak_progresses, limit=10),
        )
        chunks.append(
            KnowledgeChunk(
                chunk_id=_make_chunk_id("personalized_vocab", user.id, "weak_words"),
                source_type="personalized_vocab",
                source_id=user.id,
                title=f"{user.nickname or user.openid} 的高频错词",
                content=content,
                metadata={
                    "scope": "personalized",
                    "chunk_kind": "weak_words",
                    "user_id": user.id,
                    "keyword_hints": _token_summary(content),
                    "chunk_version": PERSONALIZED_CHUNK_VERSION,
                },
            )
        )

    mastered_progresses = list(
        WordProgress.objects.select_related("word")
        .filter(user=user, is_mastered=True)
        .order_by("-last_reviewed_at", "-last_learned_at", "-id")[:10]
    )
    if mastered_progresses:
        content = _clean_text(
            "这是用户已经掌握得比较稳定的一批词。",
            "当 AI 安排训练计划时，可以减少重复讲解，更多做对比和迁移。",
            _join_word_lines(mastered_progresses, limit=8),
        )
        chunks.append(
            KnowledgeChunk(
                chunk_id=_make_chunk_id("personalized_vocab", user.id, "mastered_words"),
                source_type="personalized_vocab",
                source_id=user.id,
                title=f"{user.nickname or user.openid} 的已掌握词汇",
                content=content,
                metadata={
                    "scope": "personalized",
                    "chunk_kind": "mastered_words",
                    "user_id": user.id,
                    "keyword_hints": _token_summary(content),
                    "chunk_version": PERSONALIZED_CHUNK_VERSION,
                },
            )
        )
    return chunks


def _build_recent_behavior_chunk(user) -> List[KnowledgeChunk]:
    chunks: List[KnowledgeChunk] = []
    recent_records = list(
        LearningRecord.objects.select_related("word")
        .filter(user=user, occurred_at__gte=_safe_days_ago(7))
        .order_by("-occurred_at", "-id")[:24]
    )
    if not recent_records:
        return chunks

    action_counter = Counter(item.action_type for item in recent_records if item.action_type)
    focus_words = [item.word.word for item in recent_records if item.word_id][:10]
    content = _clean_text(
        "这是用户最近 7 天的学习行为摘要。",
        f"行为分布: {dict(action_counter)}",
        f"近期高频接触词: {', '.join(list(dict.fromkeys(focus_words))[:10])}",
    )
    chunks.append(
        KnowledgeChunk(
            chunk_id=_make_chunk_id("personalized_behavior", user.id, "recent_behavior"),
            source_type="personalized_behavior",
            source_id=user.id,
            title=f"{user.nickname or user.openid} 的最近学习行为",
            content=content,
            metadata={
                "scope": "personalized",
                "chunk_kind": "recent_behavior",
                "user_id": user.id,
                "keyword_hints": _token_summary(content),
                "chunk_version": PERSONALIZED_CHUNK_VERSION,
            },
        )
    )
    return chunks


def _build_wrong_review_chunks(user) -> List[KnowledgeChunk]:
    chunks: List[KnowledgeChunk] = []
    wrong_words = list(
        WrongWord.objects.select_related("word")
        .filter(user=user, is_active=True)
        .order_by("-wrong_count", "-last_wrong_at", "-id")[:12]
    )
    recent_wrong_records = list(
        ReviewRecord.objects.select_related("word")
        .filter(user=user, is_correct=False)
        .order_by("-reviewed_at", "-id")[:10]
    )

    if wrong_words:
        content = _clean_text(
            "这是用户当前仍然活跃的错词本摘要。",
            "\n".join(
                [
                    f"{item.word.word} | 中文: {item.word.meaning_cn} | 错误次数: {item.wrong_count} | 最近错于: {item.last_wrong_at}"
                    for item in wrong_words[:10]
                ]
            ),
        )
        chunks.append(
            KnowledgeChunk(
                chunk_id=_make_chunk_id("personalized_review", user.id, "wrong_words"),
                source_type="personalized_review",
                source_id=user.id,
                title=f"{user.nickname or user.openid} 的错词本",
                content=content,
                metadata={
                    "scope": "personalized",
                    "chunk_kind": "wrong_words",
                    "user_id": user.id,
                    "keyword_hints": _token_summary(content),
                    "chunk_version": PERSONALIZED_CHUNK_VERSION,
                },
            )
        )

    if recent_wrong_records:
        content = _clean_text(
            "这是用户最近答错的复习记录样本。",
            _join_review_lines(recent_wrong_records, limit=8),
        )
        chunks.append(
            KnowledgeChunk(
                chunk_id=_make_chunk_id("personalized_review", user.id, "recent_wrong_records"),
                source_type="personalized_review",
                source_id=user.id,
                title=f"{user.nickname or user.openid} 的最近错题",
                content=content,
                metadata={
                    "scope": "personalized",
                    "chunk_kind": "recent_wrong_records",
                    "user_id": user.id,
                    "keyword_hints": _token_summary(content),
                    "chunk_version": PERSONALIZED_CHUNK_VERSION,
                },
            )
        )
    return chunks


def _build_grammar_chunks(user) -> List[KnowledgeChunk]:
    chunks: List[KnowledgeChunk] = []
    records = list(
        GrammarLearningRecord.objects.select_related("point", "sentence")
        .filter(user=user, occurred_at__gte=_safe_days_ago(14))
        .order_by("-occurred_at", "-id")[:30]
    )
    if not records:
        return chunks

    weak_points = Counter()
    related_sentences = []
    for item in records:
        if item.result == "wrong" or item.action_type == "unclear":
            weak_points[item.point.title] += 1
            if item.sentence and item.sentence.sentence:
                related_sentences.append(item.sentence.sentence)

    if not weak_points:
        return chunks

    weak_lines = [f"{title} | 近期困难次数: {count}" for title, count in weak_points.most_common(8)]
    content = _clean_text(
        "这是用户最近的语法薄弱点摘要。",
        "\n".join(weak_lines),
        f"相关句子样本: {' | '.join(related_sentences[:4])}",
    )
    chunks.append(
        KnowledgeChunk(
            chunk_id=_make_chunk_id("personalized_grammar", user.id, "weak_grammar"),
            source_type="personalized_grammar",
            source_id=user.id,
            title=f"{user.nickname or user.openid} 的语法薄弱点",
            content=content,
            metadata={
                "scope": "personalized",
                "chunk_kind": "weak_grammar",
                "user_id": user.id,
                "keyword_hints": _token_summary(content),
                "chunk_version": PERSONALIZED_CHUNK_VERSION,
            },
        )
    )
    return chunks


def build_personalized_knowledge_chunks(user) -> PersonalizedChunkBundle:
    if not user or not getattr(user, "id", None):
        raise ValueError("valid user is required")

    chunks: List[KnowledgeChunk] = []
    chunks.extend(_build_plan_chunk(user))
    chunks.extend(_build_progress_chunks(user))
    chunks.extend(_build_recent_behavior_chunk(user))
    chunks.extend(_build_wrong_review_chunks(user))
    chunks.extend(_build_grammar_chunks(user))

    summary = {
        "chunk_count": len(chunks),
        "source_type_breakdown": dict(Counter(item.source_type for item in chunks)),
    }
    return PersonalizedChunkBundle(chunks=chunks, summary=summary)


def split_personalized_payload(chunks: Iterable[KnowledgeChunk]):
    ids: List[str] = []
    documents: List[str] = []
    metadatas: List[Dict[str, object]] = []
    for item in chunks:
        ids.append(item.chunk_id)
        documents.append(item.content)
        payload_metadata = {
            "source_type": item.source_type,
            "source_id": item.source_id,
            "title": item.title,
            **item.metadata,
        }
        payload_metadata["content_hash"] = _content_hash(
            item.source_type,
            item.source_id,
            item.title,
            item.content,
            payload_metadata,
        )
        metadatas.append(payload_metadata)
    return ids, documents, metadatas
