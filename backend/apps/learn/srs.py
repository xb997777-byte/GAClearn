import re
from datetime import timedelta

from django.utils import timezone


SPACE_PATTERN = re.compile(r"\s+")
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")


def normalize_answer_text(value):
    text = (value or "").strip().lower()
    text = SPACE_PATTERN.sub(" ", text)
    return text


def normalize_compact_text(value):
    return NON_ALNUM_PATTERN.sub("", normalize_answer_text(value))


def levenshtein_distance(left, right):
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous_row = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current_row = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            insert_cost = current_row[right_index - 1] + 1
            delete_cost = previous_row[right_index] + 1
            replace_cost = previous_row[right_index - 1] + (0 if left_char == right_char else 1)
            current_row.append(min(insert_cost, delete_cost, replace_cost))
        previous_row = current_row
    return previous_row[-1]


def text_similarity_score(expected, actual):
    normalized_expected = normalize_compact_text(expected)
    normalized_actual = normalize_compact_text(actual)
    if not normalized_expected and not normalized_actual:
        return 100.0
    if not normalized_expected or not normalized_actual:
        return 0.0

    distance = levenshtein_distance(normalized_expected, normalized_actual)
    longest = max(len(normalized_expected), len(normalized_actual), 1)
    return round(max(0.0, (1 - distance / longest) * 100), 2)


def is_text_answer_correct(expected, actual, threshold=88):
    return text_similarity_score(expected, actual) >= threshold


def infer_quality(question_type, is_correct, similarity_score=0):
    if not is_correct:
        return 2
    if question_type == "spelling":
        if similarity_score >= 98:
            return 5
        if similarity_score >= 92:
            return 4
        return 3
    return 4


def apply_srs_schedule(progress, is_correct, quality=4, occurred_at=None):
    occurred_at = occurred_at or timezone.now()
    ease_factor = float(progress.ease_factor or 2.3)
    interval_days = int(progress.interval_days or 0)
    correct_streak = int(progress.correct_streak or 0)

    if is_correct:
        correct_streak += 1
        if correct_streak == 1:
            interval_days = 1
        elif correct_streak == 2:
            interval_days = 3
        else:
            interval_days = max(4, round(max(interval_days, 3) * ease_factor))
        delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
        ease_factor = round(max(1.3, ease_factor + delta), 2)
    else:
        correct_streak = 0
        interval_days = 1
        ease_factor = round(max(1.3, ease_factor - 0.2), 2)

    progress.ease_factor = ease_factor
    progress.interval_days = interval_days
    progress.correct_streak = correct_streak
    progress.last_score = max(min(int(quality), 5), 0)
    progress.review_due_at = occurred_at + timedelta(days=interval_days)
    return progress
