from collections import Counter
from typing import Dict, List

from apps.learn.adaptive import build_adaptive_profile
from apps.learn.models import WordProgress
from apps.plans.services import build_today_task_payload, get_current_plan
from apps.review.models import WrongWord
from apps.stats.services import build_overview, build_trend


def _serialize_wrong_word(item, reason: str) -> Dict:
    return {
        "word": item.word.word,
        "meaning_cn": item.word.meaning_cn,
        "wrong_count": item.wrong_count,
        "reason": reason,
    }


def _build_priority_wrong_words(user, limit=5) -> List[Dict]:
    queryset = (
        WrongWord.objects.filter(user=user, is_active=True)
        .select_related("word")
        .order_by("-wrong_count", "-last_wrong_at", "-id")[:limit]
    )
    result = []
    for item in queryset:
        reason = "重复出错次数较多，建议优先回收。"
        if (item.word.part_of_speech or "").strip():
            reason = f"{item.word.part_of_speech} 词类近期容易混淆，建议优先再过一遍。"
        result.append(_serialize_wrong_word(item, reason))
    return result


def _build_due_review_words(user, limit=5) -> List[Dict]:
    queryset = (
        WordProgress.objects.filter(user=user, review_due_at__isnull=False)
        .select_related("word")
        .order_by("review_due_at", "-wrong_count", "id")[:limit]
    )
    return [
        {
            "word": item.word.word,
            "meaning_cn": item.word.meaning_cn,
            "mastery_level": item.mastery_level,
            "wrong_count": item.wrong_count,
        }
        for item in queryset
    ]


def _build_wrong_patterns(user, limit=3) -> List[str]:
    counter = Counter()
    queryset = (
        WrongWord.objects.filter(user=user, is_active=True)
        .select_related("word")
        .order_by("-wrong_count", "-last_wrong_at")[:30]
    )
    for item in queryset:
        part_of_speech = (item.word.part_of_speech or "").strip()
        if part_of_speech:
            counter[part_of_speech] += max(item.wrong_count, 1)

    patterns = []
    for pos, count in counter.most_common(limit):
        patterns.append(f"{pos} 词最近更容易出错，当前累计风险值 {count}。")
    return patterns


def build_study_coach_bundle(user, trend_days=7) -> Dict:
    current_plan = get_current_plan(user)
    today_payload = build_today_task_payload(user)
    adaptive = today_payload.get("adaptive") or build_adaptive_profile(user, current_plan)
    overview = build_overview(user)
    trend = build_trend(user, min(max(int(trend_days or 7), 3), 14))

    return {
        "today_task": today_payload,
        "overview": overview,
        "adaptive": adaptive,
        "trend": trend,
        "priority_wrong_words": _build_priority_wrong_words(user, limit=5),
        "due_review_words": _build_due_review_words(user, limit=5),
        "wrong_patterns": _build_wrong_patterns(user, limit=3),
    }


def build_wrong_words_review_bundle(user, limit=12) -> Dict:
    limit = min(max(int(limit or 12), 3), 24)
    wrong_words = list(
        WrongWord.objects.filter(user=user, is_active=True)
        .select_related("word")
        .order_by("-wrong_count", "-last_wrong_at", "-id")[:limit]
    )
    counter = Counter()
    for item in wrong_words:
        part_of_speech = (item.word.part_of_speech or "").strip()
        if part_of_speech:
            counter[part_of_speech] += max(item.wrong_count, 1)

    return {
        "total_wrong_words": WrongWord.objects.filter(user=user, is_active=True).count(),
        "priority_words": [
            _serialize_wrong_word(
                item,
                "重复出错次数较多，建议先做意义辨析和例句回忆。"
                if item.wrong_count >= 2
                else "虽然次数不多，但仍处于活跃错词状态。",
            )
            for item in wrong_words[:5]
        ],
        "wrong_patterns": [
            {"label": pos, "weight": weight}
            for pos, weight in counter.most_common(4)
        ],
        "adaptive_snapshot": build_study_coach_bundle(user, trend_days=7).get("adaptive", {}),
    }
