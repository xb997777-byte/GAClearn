from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.exams.models import TestSession
from apps.grammar.models import GrammarLearningRecord, GrammarSentence
from apps.learn.models import Favorite, LearningRecord, WordProgress
from apps.review.models import ReviewRecord, WrongWord

from .models import CheckinRecord


def _calculate_streak(user):
    dates = list(CheckinRecord.objects.filter(user=user).values_list("checkin_date", flat=True).order_by("-checkin_date"))
    if not dates:
        return 0
    streak = 0
    current_date = timezone.localdate()
    date_set = set(dates)
    while current_date in date_set:
        streak += 1
        current_date -= timedelta(days=1)
    return streak


def _day_range(local_day):
    tz = timezone.get_current_timezone()
    start_at = timezone.make_aware(datetime.combine(local_day, time.min), tz)
    end_at = start_at + timedelta(days=1)
    return start_at, end_at


def build_overview(user):
    learned_count = WordProgress.objects.filter(user=user, learn_count__gt=0).count()
    review_count = ReviewRecord.objects.filter(user=user).count()
    tests = TestSession.objects.filter(user=user, status="completed")
    average_score = round(sum(float(item.score) for item in tests) / tests.count(), 2) if tests.exists() else 0
    grammar_studied_count = (
        GrammarLearningRecord.objects.filter(user=user).values("sentence_id").distinct().count()
    )
    grammar_total_count = GrammarSentence.objects.filter(status="active", point__status="active").count()
    return {
        "learned_word_count": learned_count,
        "review_count": review_count,
        "test_count": tests.count(),
        "average_test_score": average_score,
        "favorite_count": Favorite.objects.filter(user=user).count(),
        "wrong_word_count": WrongWord.objects.filter(user=user, is_active=True).count(),
        "grammar_sentence_count": grammar_total_count,
        "grammar_studied_count": grammar_studied_count,
        "grammar_learning_percent": round((grammar_studied_count / grammar_total_count) * 100, 2)
        if grammar_total_count
        else 0,
        "streak_days": _calculate_streak(user),
    }


def build_trend(user, days=7):
    today = timezone.localdate()
    result = []
    for offset in range(days - 1, -1, -1):
        current_day = today - timedelta(days=offset)
        start_at, end_at = _day_range(current_day)
        learned = LearningRecord.objects.filter(user=user, occurred_at__gte=start_at, occurred_at__lt=end_at, source="learn").count()
        reviewed = ReviewRecord.objects.filter(user=user, reviewed_at__gte=start_at, reviewed_at__lt=end_at).count()
        grammar_count = GrammarLearningRecord.objects.filter(user=user, occurred_at__gte=start_at, occurred_at__lt=end_at).count()
        test_count = TestSession.objects.filter(
            user=user,
            completed_at__gte=start_at,
            completed_at__lt=end_at,
            status="completed",
        ).count()
        correct_total = ReviewRecord.objects.filter(
            user=user,
            reviewed_at__gte=start_at,
            reviewed_at__lt=end_at,
            is_correct=True,
        ).count()
        review_total = ReviewRecord.objects.filter(
            user=user,
            reviewed_at__gte=start_at,
            reviewed_at__lt=end_at,
        ).count()
        accuracy = round((correct_total / review_total) * 100, 2) if review_total else 0
        result.append(
            {
                "date": current_day,
                "learned_count": learned,
                "review_count": reviewed,
                "grammar_count": grammar_count,
                "test_count": test_count,
                "review_accuracy": accuracy,
            }
        )
    return result


def perform_checkin(user):
    today = timezone.localdate()
    learned_count = LearningRecord.objects.filter(user=user, occurred_at__date=today, source="learn").count()
    reviewed_count = ReviewRecord.objects.filter(user=user, reviewed_at__date=today).count()
    minutes = int(sum(item.duration for item in LearningRecord.objects.filter(user=user, occurred_at__date=today)) / 60)
    record, _ = CheckinRecord.objects.update_or_create(
        user=user,
        checkin_date=today,
        defaults={
            "finished_new_count": learned_count,
            "finished_review_count": reviewed_count,
            "total_minutes": minutes,
            "status": "success" if learned_count or reviewed_count else "pending",
        },
    )
    return {
        "checkin_date": record.checkin_date,
        "finished_new_count": record.finished_new_count,
        "finished_review_count": record.finished_review_count,
        "total_minutes": record.total_minutes,
        "status": record.status,
    }


def list_checkin_history(user):
    queryset = CheckinRecord.objects.filter(user=user).order_by("-checkin_date")
    return [
        {
            "checkin_date": item.checkin_date,
            "finished_new_count": item.finished_new_count,
            "finished_review_count": item.finished_review_count,
            "total_minutes": item.total_minutes,
            "status": item.status,
        }
        for item in queryset
    ]
