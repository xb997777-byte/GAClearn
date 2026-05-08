from django.db import transaction
from django.utils import timezone

from apps.books.models import Word
from apps.learn.adaptive import annotate_new_word_candidates, build_adaptive_profile
from apps.plans.services import get_current_plan, get_or_create_today_task
from apps.users.services import ensure_user_setting

from .models import Favorite, LearningRecord, WordProgress
from .srs import apply_srs_schedule, infer_quality


def _get_or_create_progress(user, word):
    progress, _ = WordProgress.objects.get_or_create(
        user=user,
        word=word,
        defaults={"book": word.book},
    )
    return progress


def serialize_progress(progress):
    if not progress:
        return {
            "mastery_level": 0,
            "is_favorite": False,
            "is_mastered": False,
            "wrong_count": 0,
            "review_due_at": None,
            "ease_factor": 2.3,
            "interval_days": 0,
            "correct_streak": 0,
            "last_score": 0,
        }
    return {
        "mastery_level": progress.mastery_level,
        "is_favorite": progress.is_favorite,
        "is_mastered": progress.is_mastered,
        "wrong_count": progress.wrong_count,
        "review_due_at": progress.review_due_at,
        "ease_factor": progress.ease_factor,
        "interval_days": progress.interval_days,
        "correct_streak": progress.correct_streak,
        "last_score": progress.last_score,
    }


def _build_pronunciation_payload(word):
    return {
        "audio_url": word.audio_url,
        "tts_text": word.word,
        "example_tts_text": word.example_sentence,
        "language": "en_US",
    }


def serialize_word(word, progress=None, adaptive_reason="", adaptive_tags=None):
    return {
        "id": word.id,
        "book_id": word.book_id,
        "word": word.word,
        "phonetic": word.phonetic,
        "part_of_speech": word.part_of_speech,
        "meaning_cn": word.meaning_cn,
        "example_sentence": word.example_sentence,
        "example_translation": word.example_translation,
        "audio_url": word.audio_url,
        "difficulty": word.difficulty,
        "synonyms": word.synonyms,
        "pronunciation": _build_pronunciation_payload(word),
        "examples": [
            {
                "id": item.id,
                "example_sentence": item.example_sentence,
                "example_translation": item.example_translation,
            }
            for item in word.examples.all()
        ],
        "progress": serialize_progress(progress),
        "adaptive_reason": adaptive_reason,
        "adaptive_tags": adaptive_tags or [],
    }


def _resolve_today_target(user, plan, requested_limit=None):
    requested_limit = max(int(requested_limit or 0), 0)
    if requested_limit > 0:
        return min(requested_limit, 200), None

    task_new_word_target = None
    if plan:
        task = get_or_create_today_task(user, plan)
        task_new_word_target = max(int(task.new_word_target or 0), 0)
        if task_new_word_target > 0:
            return min(task_new_word_target, 200), task

    plan_daily_target = max(int(getattr(plan, "daily_target", 0) or 0), 0)
    if plan_daily_target > 0:
        return min(plan_daily_target, 200), None

    user_setting = ensure_user_setting(user)
    setting_daily_target = max(int(getattr(user_setting, "daily_target", 0) or 0), 0)
    if setting_daily_target > 0:
        return min(setting_daily_target, 200), None

    return 20, None


def get_today_words(user, limit=0):
    plan = get_current_plan(user)
    if not plan:
        return {
            "list": [],
            "adaptive": None,
            "target_count": 0,
            "plan_daily_target": 0,
            "task_new_word_target": 0,
        }

    adaptive_profile = build_adaptive_profile(user, plan)
    target_count, task = _resolve_today_target(user, plan, limit)
    learned_ids = WordProgress.objects.filter(user=user, book=plan.book, learn_count__gt=0).values_list("word_id", flat=True)
    candidates = list(
        Word.objects.filter(book=plan.book)
        .exclude(id__in=learned_ids)
        .prefetch_related("examples")
        .order_by("order_in_book", "id")[: max(target_count * 5, 60)]
    )
    ranked_candidates = annotate_new_word_candidates(candidates, adaptive_profile)[:target_count]

    return {
        "list": [
            serialize_word(
                item["word"],
                adaptive_reason=item["reason"],
                adaptive_tags=item["reasons"],
            )
            for item in ranked_candidates
        ],
        "adaptive": adaptive_profile,
        "target_count": target_count,
        "plan_daily_target": int(getattr(plan, "daily_target", 0) or 0),
        "task_new_word_target": int((task.new_word_target if task else 0) or 0),
    }


def get_word_detail(user, word_id):
    word = Word.objects.select_related("book").prefetch_related("examples").get(id=word_id)
    progress = WordProgress.objects.filter(user=user, word=word).first()
    return serialize_word(word, progress)


def _should_count_as_correct(action_type, result):
    return action_type in {"known", "mastered"} or result == "correct"


def _should_count_as_wrong(action_type, result):
    return action_type == "unknown" or result == "wrong"


def _should_update_schedule(action_type, result):
    return action_type in {"known", "unknown", "mastered"} or result in {"correct", "wrong"}


def _apply_progress(progress, source, action_type, result, occurred_at, extra_payload=None):
    extra_payload = extra_payload or {}
    if source == "learn":
        progress.last_learned_at = occurred_at
        if action_type in {"view", "known", "unknown", "mastered"}:
            progress.learn_count += 1
    elif source == "review":
        progress.review_count += 1
        progress.last_reviewed_at = occurred_at
    elif source == "test":
        progress.last_tested_at = occurred_at

    is_correct = _should_count_as_correct(action_type, result)
    is_wrong = _should_count_as_wrong(action_type, result)

    if is_correct:
        progress.correct_count += 1
        progress.mastery_level = min(progress.mastery_level + 1, 5)
    if is_wrong:
        progress.wrong_count += 1
        progress.mastery_level = max(progress.mastery_level - 1, 0)
    if action_type == "mastered":
        progress.is_mastered = True
        progress.mastery_level = 5

    if _should_update_schedule(action_type, result):
        similarity_score = float((extra_payload or {}).get("score", 0) or 0)
        quality = infer_quality(action_type, is_correct, similarity_score)
        apply_srs_schedule(progress, is_correct, quality, occurred_at)

    progress.save()
    return progress


def _update_plan_progress(user, plan, source, action_type):
    if not plan:
        return
    plan.finished_word_count = WordProgress.objects.filter(user=user, book=plan.book, learn_count__gt=0).count()
    plan.save(update_fields=["finished_word_count", "updated_at"])
    task = get_or_create_today_task(user, plan)
    if source == "learn" and action_type in {"known", "unknown", "mastered"}:
        task.learned_count = min(task.learned_count + 1, task.new_word_target)
    elif source == "review":
        task.reviewed_count = min(task.reviewed_count + 1, task.review_word_target)
    elif source == "test":
        task.test_count += 1
    task.save()


@transaction.atomic
def create_record(user, validated_data):
    word = Word.objects.select_related("book").get(id=validated_data["word_id"])
    plan = get_current_plan(user)
    occurred_at = validated_data.get("occurred_at") or timezone.now()
    extra_payload = validated_data.get("extra_payload", {})
    progress = _get_or_create_progress(user, word)
    record = LearningRecord.objects.create(
        user=user,
        word=word,
        plan=plan,
        source=validated_data["source"],
        action_type=validated_data["action_type"],
        result=validated_data.get("result", ""),
        duration=validated_data.get("duration", 0),
        extra_payload=extra_payload,
        occurred_at=occurred_at,
    )
    progress = _apply_progress(
        progress,
        validated_data["source"],
        validated_data["action_type"],
        validated_data.get("result", ""),
        occurred_at,
        extra_payload,
    )

    if validated_data["action_type"] == "favorite":
        Favorite.objects.get_or_create(user=user, word=word)
        progress.is_favorite = True
        progress.save(update_fields=["is_favorite", "updated_at"])

    _update_plan_progress(user, plan, validated_data["source"], validated_data["action_type"])
    return {"record_id": record.id, "progress": serialize_progress(progress)}


def create_record_batch(user, records):
    return [create_record(user, item) for item in records]


def list_favorites(user):
    favorites = Favorite.objects.filter(user=user).select_related("word", "word__book").order_by("-id")
    result = []
    for favorite in favorites:
        progress = WordProgress.objects.filter(user=user, word=favorite.word).first()
        result.append({"id": favorite.id, "note": favorite.note, "word": serialize_word(favorite.word, progress)})
    return result


def add_favorite(user, word_id, note=""):
    word = Word.objects.select_related("book").get(id=word_id)
    favorite, _ = Favorite.objects.get_or_create(user=user, word=word, defaults={"note": note})
    progress = _get_or_create_progress(user, word)
    progress.is_favorite = True
    progress.save(update_fields=["is_favorite", "updated_at"])
    return {"favorite_id": favorite.id, "word_id": word_id}


def delete_favorite(user, word_id):
    Favorite.objects.filter(user=user, word_id=word_id).delete()
    progress = WordProgress.objects.filter(user=user, word_id=word_id).first()
    if progress:
        progress.is_favorite = False
        progress.save(update_fields=["is_favorite", "updated_at"])
