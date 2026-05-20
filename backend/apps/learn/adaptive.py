from collections import Counter
from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone

from apps.learn.models import LearningRecord, WordProgress
from apps.review.models import ReviewRecord, WrongWord


DIFFICULTY_LABELS = {
    1: "基础巩固",
    2: "标准推进",
    3: "进阶挑战",
}


MODE_LABELS = {
    "review_priority": "今天先救复习",
    "consolidate": "先稳住正确率",
    "new_word_push": "可以多推进新词",
    "balanced": "维持均衡节奏",
}


def _collect_recent_metrics(user, since_at):
    learn_records = list(
        LearningRecord.objects.filter(user=user, occurred_at__gte=since_at)
        .exclude(action_type="view")
        .order_by("-occurred_at")[:240]
    )
    review_records = list(
        ReviewRecord.objects.filter(user=user, reviewed_at__gte=since_at)
        .order_by("-reviewed_at")[:240]
    )

    learn_total = 0
    learn_correct = 0
    learn_wrong = 0
    recent_new_actions = 0

    for item in learn_records:
        if item.source == "learn" and item.action_type in {"known", "unknown", "mastered"}:
            recent_new_actions += 1

        if item.action_type in {"known", "mastered"} or item.result == "correct":
            learn_total += 1
            learn_correct += 1
        elif item.action_type == "unknown" or item.result == "wrong":
            learn_total += 1
            learn_wrong += 1
    review_total = len(review_records)
    review_correct = sum(1 for item in review_records if item.is_correct)
    review_wrong = max(review_total - review_correct, 0)

    total = learn_total + review_total
    correct = learn_correct + review_correct
    wrong = learn_wrong + review_wrong
    accuracy = round((correct / total) * 100, 2) if total else None

    return {
        "evaluated_total": total,
        "correct_total": correct,
        "wrong_total": wrong,
        "recent_accuracy": accuracy,
        "recent_new_actions": recent_new_actions,
        "learn_records": learn_records,
        "review_records": review_records,
    }


def _build_weak_point_counter(progresses):
    counter = Counter()
    for progress in progresses:
        pos = (progress.word.part_of_speech or "").strip()
        if not pos:
            continue

        risk_weight = 0
        if progress.wrong_count:
            risk_weight += progress.wrong_count * 2
        if progress.mastery_level <= 2:
            risk_weight += 3 - progress.mastery_level
        if progress.last_score and progress.last_score < 70:
            risk_weight += max(1, round((70 - progress.last_score) / 10))

        if risk_weight > 0:
            counter[pos] += risk_weight
    return counter


def _top_weak_points(counter, limit=3):
    result = []
    for pos, weight in counter.most_common(limit):
        result.append(
            {
                "label": pos,
                "weight": round(weight, 2),
                "tip": f"最近 {pos} 相关词更容易出错，建议放慢一点巩固。",
            }
        )
    return result


def _infer_target_difficulty(base_target, due_review_count, avg_mastery, recent_accuracy):
    recent_accuracy = recent_accuracy if recent_accuracy is not None else 78
    avg_mastery = avg_mastery or 0

    if recent_accuracy >= 88 and avg_mastery >= 2.8 and due_review_count <= max(base_target // 3, 4):
        return 3
    if recent_accuracy >= 70 and avg_mastery >= 1.2:
        return 2
    return 1


def _infer_mode(base_target, due_review_count, overdue_review_count, weak_word_count, recent_accuracy):
    recent_accuracy = recent_accuracy if recent_accuracy is not None else 78
    if due_review_count >= max(base_target, 12) or overdue_review_count >= 6:
        return "review_priority"
    if recent_accuracy < 65 or weak_word_count >= max(base_target, 15):
        return "consolidate"
    if recent_accuracy >= 88 and due_review_count <= max(base_target // 3, 4):
        return "new_word_push"
    return "balanced"


def _recommend_targets(base_target, mode, due_review_count, weak_word_count, recent_accuracy):
    recent_accuracy = recent_accuracy if recent_accuracy is not None else 78

    if mode == "review_priority":
        new_target = max(6, round(base_target * 0.55))
        review_target = max(12, min(max(due_review_count, 12), base_target * 2))
    elif mode == "consolidate":
        new_target = max(8, round(base_target * 0.7))
        review_target = max(10, min(max(due_review_count, 10), round(base_target * 1.5)))
    elif mode == "new_word_push":
        new_target = min(base_target + 6, round(base_target * 1.2))
        review_target = max(8, min(max(due_review_count, 8), base_target))
    else:
        new_target = base_target
        review_target = max(10, min(max(due_review_count, 10), round(base_target * 1.25)))

    if recent_accuracy < 55:
        new_target = max(6, min(new_target, round(base_target * 0.6)))
    if weak_word_count >= 20:
        review_target = max(review_target, round(base_target * 1.5))

    return int(new_target), int(review_target)


def _build_focus_tip(mode, due_review_count, overdue_review_count, weak_word_count, recent_accuracy, weak_points):
    if mode == "review_priority":
        return (
            f"今天有 {due_review_count} 个词到了复习时间，其中 {overdue_review_count} 个已经拖后。"
            " 先把高风险复习清掉，再推进新词会更稳。"
        )
    if mode == "consolidate":
        weak_label = weak_points[0]["label"] if weak_points else "薄弱词"
        return (
            f"最近正确率约 {int(recent_accuracy or 0)}%，而且 {weak_word_count} 个词还不稳定。"
            f" 今天更适合优先巩固 {weak_label} 相关内容。"
        )
    if mode == "new_word_push":
        return (
            f"最近正确率约 {int(recent_accuracy or 0)}%，复习压力不高。"
            " 今天可以更积极地推进新词。"
        )
    return "今天适合维持新词与复习并行的节奏，边推进边回收薄弱词。"


def build_adaptive_profile(user, plan=None, recent_days=7):
    now = timezone.now()
    since_at = now - timedelta(days=max(recent_days, 3))
    base_target = max(getattr(plan, "daily_target", 20) or 20, 6)

    recent_metrics = _collect_recent_metrics(user, since_at)

    progress_qs = WordProgress.objects.filter(user=user)
    if plan and getattr(plan, "book_id", None):
        progress_qs = progress_qs.filter(book_id=plan.book_id)
    learned_progress_qs = progress_qs.filter(learn_count__gt=0)

    due_review_count = progress_qs.filter(review_due_at__isnull=False, review_due_at__lte=now).count()
    overdue_review_count = progress_qs.filter(
        review_due_at__isnull=False,
        review_due_at__lte=now - timedelta(hours=24),
    ).count()
    weak_word_qs = WrongWord.objects.filter(user=user, is_active=True)
    if plan and getattr(plan, "book_id", None):
        weak_word_qs = weak_word_qs.filter(word__book_id=plan.book_id)
    weak_word_count = weak_word_qs.count()
    avg_mastery = learned_progress_qs.aggregate(value=Avg("mastery_level")).get("value") or 0

    weak_progresses = list(
        learned_progress_qs.select_related("word")
        .order_by("-wrong_count", "mastery_level", "last_score", "review_due_at")[:80]
    )
    weak_counter = _build_weak_point_counter(weak_progresses)
    weak_points = _top_weak_points(weak_counter)

    target_difficulty = _infer_target_difficulty(
        base_target,
        due_review_count,
        avg_mastery,
        recent_metrics["recent_accuracy"],
    )
    mode = _infer_mode(
        base_target,
        due_review_count,
        overdue_review_count,
        weak_word_count,
        recent_metrics["recent_accuracy"],
    )
    recommended_new_target, recommended_review_target = _recommend_targets(
        base_target,
        mode,
        due_review_count,
        weak_word_count,
        recent_metrics["recent_accuracy"],
    )

    return {
        "strategy_version": "adaptive-v1",
        "mode": mode,
        "mode_label": MODE_LABELS[mode],
        "focus_tip": _build_focus_tip(
            mode,
            due_review_count,
            overdue_review_count,
            weak_word_count,
            recent_metrics["recent_accuracy"],
            weak_points,
        ),
        "recommended_new_word_target": recommended_new_target,
        "recommended_review_word_target": recommended_review_target,
        "base_daily_target": base_target,
        "due_review_count": due_review_count,
        "overdue_review_count": overdue_review_count,
        "weak_word_count": weak_word_count,
        "recent_accuracy": recent_metrics["recent_accuracy"],
        "recent_accuracy_percent": int(round(recent_metrics["recent_accuracy"])) if recent_metrics["recent_accuracy"] is not None else None,
        "recent_new_actions": recent_metrics["recent_new_actions"],
        "target_difficulty": target_difficulty,
        "target_difficulty_label": DIFFICULTY_LABELS[target_difficulty],
        "weak_points": weak_points,
        "weak_point_tokens": [item["label"] for item in weak_points],
    }


def annotate_new_word_candidates(words, adaptive_profile):
    target_difficulty = adaptive_profile["target_difficulty"]
    weak_tokens = set(adaptive_profile.get("weak_point_tokens") or [])
    mode = adaptive_profile["mode"]

    annotated = []
    for word in words:
        difficulty_gap = abs((word.difficulty or 1) - target_difficulty)
        score = max(0, 26 - difficulty_gap * 8)
        reasons = []

        if difficulty_gap == 0:
            score += 16
            reasons.append("更贴合你当前适合推进的难度")
        elif difficulty_gap == 1:
            score += 8
            reasons.append("难度接近你当前的学习节奏")

        pos = (word.part_of_speech or "").strip()
        if pos and pos in weak_tokens:
            score += 12
            reasons.append(f"命中你最近更容易混淆的 {pos} 词类")

        if mode == "review_priority" and (word.difficulty or 1) > target_difficulty:
            score -= 8
        if mode == "new_word_push" and (word.difficulty or 1) == target_difficulty:
            score += 4

        score -= min(word.order_in_book or 0, 3000) / 1000

        if not reasons:
            reasons.append("适合作为今天的平衡推进词")

        annotated.append(
            {
                "word": word,
                "score": round(score, 2),
                "reason": reasons[0],
                "reasons": reasons,
            }
        )

    annotated.sort(key=lambda item: (-item["score"], item["word"].order_in_book, item["word"].id))
    return annotated


def annotate_review_progresses(progresses, adaptive_profile):
    now = timezone.now()
    annotated = []

    for progress in progresses:
        overdue_hours = 0
        if progress.review_due_at:
            overdue_hours = max((now - progress.review_due_at).total_seconds() / 3600, 0)

        due_score = min(overdue_hours, 72) * 1.8
        wrong_score = progress.wrong_count * 11
        mastery_score = max(0, 5 - progress.mastery_level) * 7
        last_score_penalty = max(0, 70 - (progress.last_score or 0)) * 0.35
        streak_penalty = max(0, 2 - progress.correct_streak) * 5
        total_score = due_score + wrong_score + mastery_score + last_score_penalty + streak_penalty

        reason = "优先回收今天到期的复习词"
        if wrong_score >= max(due_score, mastery_score, last_score_penalty, streak_penalty):
            reason = "最近反复出错，建议优先回收"
        elif due_score >= max(wrong_score, mastery_score, last_score_penalty, streak_penalty) and overdue_hours >= 12:
            reason = "已经拖后较久，越早复习越容易捡回来"
        elif mastery_score >= max(due_score, wrong_score, last_score_penalty, streak_penalty):
            reason = "当前掌握度偏低，适合先巩固"
        elif last_score_penalty > 0:
            reason = "上一次得分偏低，建议尽快再练一次"

        annotated.append(
            {
                "progress": progress,
                "score": round(total_score, 2),
                "reason": reason,
            }
        )

    annotated.sort(
        key=lambda item: (
            -item["score"],
            item["progress"].review_due_at or now,
            item["progress"].id,
        )
    )
    return annotated
