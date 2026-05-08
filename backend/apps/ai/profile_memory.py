from collections import Counter

from apps.review.models import WrongWord
from apps.stats.services import build_overview
from apps.users.services import ensure_user_setting

from .models import AIConversation, AIRequestLog, AIUserFeedback, AIUserProfileMemory
from .tools.study_tools import build_study_coach_bundle


def _build_profile_summary(bundle, setting, feedback_counter):
    overview = bundle.get("overview") or {}
    adaptive = bundle.get("adaptive") or {}
    weak_points = adaptive.get("weak_points") or []
    weak_text = "、".join(item.get("label", "") for item in weak_points[:3] if item.get("label")) or "暂无明显弱点"
    return (
        f"累计学习 {overview.get('learned_word_count', 0)} 个词，"
        f"当前连续学习 {overview.get('streak_days', 0)} 天，"
        f"推荐模式为 {adaptive.get('mode_label', 'balanced')}，"
        f"主要薄弱点为 {weak_text}，"
        f"当前 CEFR={setting.cefr_level or 'unknown'}，"
        f"最近 AI 反馈 helpful={feedback_counter.get('helpful', 0)}。"
    )


def _build_preferred_modes(bundle, logs):
    adaptive = bundle.get("adaptive") or {}
    feature_counter = Counter(logs.values_list("feature_type", flat=True))
    modes = [adaptive.get("mode")] if adaptive.get("mode") else []
    for feature_type, count in feature_counter.most_common(3):
        if count <= 0:
            continue
        modes.append(feature_type)
    return [item for item in dict.fromkeys(modes) if item]


def _build_recent_focus_words(bundle):
    words = []
    for item in (bundle.get("priority_wrong_words") or [])[:4]:
        if item.get("word"):
            words.append(item["word"])
    for item in (bundle.get("due_review_words") or [])[:4]:
        if item.get("word"):
            words.append(item["word"])
    return list(dict.fromkeys(words))[:6]


def build_profile_payload(user):
    bundle = build_study_coach_bundle(user, trend_days=7)
    setting = ensure_user_setting(user)
    feedback_counter = Counter(AIUserFeedback.objects.filter(user=user).values_list("rating", flat=True))
    recent_logs = AIRequestLog.objects.filter(user=user).order_by("-id")[:30]
    recent_conversations = AIConversation.objects.filter(user=user).order_by("-id")[:10]
    weak_points = (bundle.get("adaptive") or {}).get("weak_points") or []
    preferred_modes = _build_preferred_modes(bundle, recent_logs)
    focus_words = _build_recent_focus_words(bundle)
    overview = build_overview(user)

    return {
        "profile_summary": _build_profile_summary(bundle, setting, feedback_counter),
        "weak_points": weak_points,
        "preferred_modes": preferred_modes,
        "recent_focus_words": focus_words,
        "profile_payload": {
            "overview": overview,
            "adaptive": bundle.get("adaptive") or {},
            "wrong_patterns": bundle.get("wrong_patterns") or [],
            "active_wrong_word_count": WrongWord.objects.filter(user=user, is_active=True).count(),
            "recent_conversation_topics": [item.title for item in recent_conversations if item.title][:5],
            "recent_feature_usage": dict(Counter(recent_logs.values_list("feature_type", flat=True))),
            "setting": {
                "daily_target": setting.daily_target,
                "speech_speed": float(setting.speech_speed),
                "cefr_level": setting.cefr_level,
                "review_enabled": setting.review_enabled,
            },
            "feedback_summary": dict(feedback_counter),
        },
        "memory_version": "memory_v1",
    }


def refresh_profile_memory(user, source="manual"):
    payload = build_profile_payload(user)
    memory, _ = AIUserProfileMemory.objects.update_or_create(
        user=user,
        defaults={
            **payload,
            "updated_from": source or "manual",
        },
    )
    return memory


def serialize_profile_memory(memory):
    return {
        "id": memory.id,
        "profile_summary": memory.profile_summary,
        "weak_points": memory.weak_points,
        "preferred_modes": memory.preferred_modes,
        "recent_focus_words": memory.recent_focus_words,
        "profile_payload": memory.profile_payload,
        "memory_version": memory.memory_version,
        "updated_from": memory.updated_from,
        "updated_at": memory.updated_at,
    }


def get_or_refresh_profile_memory(user, source="auto"):
    memory = AIUserProfileMemory.objects.filter(user=user).first()
    if memory:
        return memory
    return refresh_profile_memory(user, source=source)
