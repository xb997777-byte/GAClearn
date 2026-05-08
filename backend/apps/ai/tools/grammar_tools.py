from collections import defaultdict

from apps.grammar.models import GrammarLearningRecord


def build_grammar_user_profile(user):
    records = list(
        GrammarLearningRecord.objects.filter(user=user)
        .select_related("point")
        .order_by("-occurred_at", "-id")[:80]
    )

    practice_total = 0
    practice_correct = 0
    weak_point_counter = defaultdict(int)
    recent_actions = []
    studied_sentences = set()
    mastered_sentences = set()

    for record in records:
        studied_sentences.add(record.sentence_id)
        if record.mastery_level >= 4:
            mastered_sentences.add(record.sentence_id)
        if record.action_type == "practice":
            practice_total += 1
            if record.result == "correct":
                practice_correct += 1
            else:
                weak_point_counter[record.point.title] += 2
        if record.action_type == "unclear":
            weak_point_counter[record.point.title] += 3
        if len(recent_actions) < 6:
            recent_actions.append(
                {
                    "point_title": record.point.title,
                    "action_type": record.action_type,
                    "result": record.result,
                }
            )

    weak_points = [
        {"title": title, "weight": weight}
        for title, weight in sorted(weak_point_counter.items(), key=lambda item: (-item[1], item[0]))[:3]
    ]
    accuracy = round((practice_correct / practice_total) * 100, 2) if practice_total else None

    return {
        "studied_sentence_count": len(studied_sentences),
        "mastered_sentence_count": len(mastered_sentences),
        "practice_total": practice_total,
        "practice_correct": practice_correct,
        "recent_accuracy_percent": int(round(accuracy)) if accuracy is not None else None,
        "weak_points": weak_points,
        "recent_actions": recent_actions,
    }

