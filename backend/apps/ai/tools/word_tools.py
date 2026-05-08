import re
from typing import Dict, List

from django.utils import timezone

from apps.books.models import Word
from apps.learn.models import LearningRecord, WordProgress
from apps.learn.services import get_word_detail
from apps.plans.services import get_current_plan
from apps.review.models import WrongWord


WORD_TOKEN_PATTERN = re.compile(r"[A-Za-z']+")


def _split_synonyms(text: str) -> List[str]:
    if not text:
        return []
    return [item.strip() for item in re.split(r"[;,/，；、]+", text) if item.strip()]


def _serialize_examples(word: Word) -> List[Dict]:
    result = []
    for item in word.examples.all()[:3]:
        result.append(
            {
                "sentence": item.example_sentence,
                "translation": item.example_translation,
            }
        )
    if not result and word.example_sentence:
        result.append(
            {
                "sentence": word.example_sentence,
                "translation": word.example_translation,
            }
        )
    return result


def _extract_example_phrases(word: Word) -> List[str]:
    sentence = (word.example_sentence or "").strip()
    if not sentence:
        return []

    tokens = WORD_TOKEN_PATTERN.findall(sentence)
    if not tokens:
        return []

    lower_word = (word.word or "").lower()
    result = []
    for index, token in enumerate(tokens):
        if token.lower() != lower_word:
            continue
        if index > 0:
            result.append(f"{tokens[index - 1]} {token}")
        if index + 1 < len(tokens):
            result.append(f"{token} {tokens[index + 1]}")
        if index > 0 and index + 1 < len(tokens):
            result.append(f"{tokens[index - 1]} {token} {tokens[index + 1]}")

    deduped = []
    seen = set()
    for item in result:
        normalized = item.lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(item)
    return deduped[:4]


def _serialize_related_word(word: Word, reason: str) -> Dict:
    return {
        "word": word.word,
        "meaning_cn": word.meaning_cn,
        "part_of_speech": word.part_of_speech,
        "difficulty": word.difficulty,
        "reason": reason,
    }


def _build_related_words(word: Word) -> List[Dict]:
    result = []
    seen_ids = {word.id}

    candidate_groups = [
        (
            Word.objects.filter(book=word.book, part_of_speech=word.part_of_speech)
            .exclude(id=word.id)
            .order_by("difficulty", "order_in_book", "id")[:4],
            "同词书、同词性，适合放在一起对比理解",
        ),
        (
            Word.objects.filter(part_of_speech=word.part_of_speech)
            .exclude(id__in=seen_ids)
            .order_by("difficulty", "id")[:4],
            "同词性词汇，适合比较用法差异",
        ),
    ]

    for queryset, reason in candidate_groups:
        for item in queryset:
            if item.id in seen_ids:
                continue
            seen_ids.add(item.id)
            result.append(_serialize_related_word(item, reason))
            if len(result) >= 4:
                return result
    return result


def _build_learning_reason(word_detail: Dict, word: Word, current_plan) -> str:
    progress = word_detail.get("progress") or {}
    wrong_count = int(progress.get("wrong_count") or 0)
    mastery_level = int(progress.get("mastery_level") or 0)
    learn_count = int(progress.get("learn_count") or 0)

    if wrong_count > 0:
        return "你之前在这个词上出现过错误，优先讲清楚更能减少重复出错。"
    if learn_count > 0 and mastery_level < 3:
        return "你已经见过这个词，但掌握度还不稳定，现在补上用法最合适。"
    if current_plan and current_plan.book_id == word.book_id:
        return "它来自你当前正在学习的词书，讲清楚后更方便继续推进今日任务。"
    return "这是你当前查看的词条，先把核心词义和例句理解透会更高效。"


def build_word_tutor_bundle(user, word_id: int) -> Dict:
    try:
        word = Word.objects.select_related("book").prefetch_related("examples").get(id=word_id)
    except Word.DoesNotExist as exc:
        raise ValueError("word not found") from exc

    word_detail = get_word_detail(user, word_id)
    recent_records = list(
        LearningRecord.objects.filter(user=user, word=word)
        .order_by("-occurred_at", "-id")[:8]
    )
    progress = WordProgress.objects.filter(user=user, word=word).first()
    current_plan = get_current_plan(user)
    due_review_count = WordProgress.objects.filter(
        user=user,
        review_due_at__isnull=False,
        review_due_at__lte=timezone.now(),
    ).count()
    same_pos_weak_count = WordProgress.objects.filter(
        user=user,
        word__part_of_speech=word.part_of_speech,
        wrong_count__gt=0,
    ).count()
    in_wrong_book = WrongWord.objects.filter(user=user, word=word, is_active=True).exists()

    recent_actions = [
        {
            "source": item.source,
            "action_type": item.action_type,
            "result": item.result,
        }
        for item in recent_records
    ]

    return {
        "word_detail": {
            **word_detail,
            "book": {
                "id": word.book_id,
                "name": word.book.name,
                "category": word.book.category,
                "level": word.book.level,
            },
            "synonym_list": _split_synonyms(word.synonyms),
            "example_phrases": _extract_example_phrases(word),
            "examples_preview": _serialize_examples(word),
            "related_words": _build_related_words(word),
        },
        "user_profile": {
            "current_plan_book_id": current_plan.book_id if current_plan else None,
            "due_review_count": due_review_count,
            "same_pos_weak_count": same_pos_weak_count,
            "in_wrong_book": in_wrong_book,
            "recent_actions": recent_actions,
            "mastery_level": progress.mastery_level if progress else 0,
            "wrong_count": progress.wrong_count if progress else 0,
            "review_count": progress.review_count if progress else 0,
            "learn_count": progress.learn_count if progress else 0,
            "why_recommended": _build_learning_reason(word_detail, word, current_plan),
        },
    }
