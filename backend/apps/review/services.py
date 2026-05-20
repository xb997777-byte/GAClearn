import random
import re

from django.utils import timezone

from apps.books.models import Word
from apps.learn.adaptive import annotate_review_progresses, build_adaptive_profile
from apps.learn.models import WordProgress
from apps.learn.srs import (
    apply_srs_schedule,
    infer_quality,
    is_text_answer_correct,
    normalize_answer_text,
    text_similarity_score,
)
from apps.plans.services import get_current_plan, get_or_create_today_task

from .models import ReviewRecord, ReviewSession, WrongWord


WORD_BOUNDARY_TEMPLATE = r"\b{}\b"
QUESTION_TYPE_LABELS = {
    "meaning_to_word": "释义选词",
    "word_to_meaning": "单词选释义",
    "example_to_word": "例句选词",
    "spelling": "拼写填空",
    "listening_to_word": "听音辨词",
}


def _pick_distractors(word, count=3):
    used_ids = {word.id}
    distractors = []
    candidate_groups = [
        Word.objects.filter(
            book=word.book,
            part_of_speech=word.part_of_speech,
            meaning_cn__isnull=False,
        ).exclude(id=word.id).exclude(meaning_cn=""),
        Word.objects.filter(
            book=word.book,
            meaning_cn__isnull=False,
        ).exclude(id=word.id).exclude(meaning_cn=""),
        Word.objects.filter(
            meaning_cn__isnull=False,
        ).exclude(id=word.id).exclude(meaning_cn=""),
    ]
    for queryset in candidate_groups:
        candidates = list(queryset.order_by("id"))
        random.shuffle(candidates)
        for item in candidates:
            if item.id in used_ids:
                continue
            distractors.append(item)
            used_ids.add(item.id)
            if len(distractors) >= count:
                return distractors
    return distractors


def _build_word_options(word):
    values = [item.word for item in _pick_distractors(word, count=3) if str(item.word or "").strip()] + [word.word]
    values = list(dict.fromkeys(values))
    random.shuffle(values)
    return [{"key": chr(65 + idx), "value": value} for idx, value in enumerate(values[:4])]


def _build_meaning_options(word):
    values = [
        str(item.meaning_cn or "").strip()
        for item in _pick_distractors(word, count=3)
        if str(item.meaning_cn or "").strip()
    ] + [str(word.meaning_cn or "").strip()]
    values = [item for item in values if item]
    values = list(dict.fromkeys(values))
    random.shuffle(values)
    return [{"key": chr(65 + idx), "value": value} for idx, value in enumerate(values[:4])]


def _mask_word(sentence, word_text):
    pattern = re.compile(WORD_BOUNDARY_TEMPLATE.format(re.escape(word_text)), re.IGNORECASE)
    masked, count = pattern.subn("____", sentence or "", count=1)
    return masked if count else sentence


def _attach_word_speech(payload, word):
    payload.update(
        {
            "speech_text": word.word,
            "speech_lang": "en-US",
        }
    )
    return payload


def _build_review_question(progress, adaptive_reason=""):
    word = progress.word
    question_types = ["meaning_to_word", "word_to_meaning", "listening_to_word"]
    if word.example_sentence:
        question_types.append("example_to_word")
    if progress.mastery_level >= 2:
        question_types.append("spelling")

    question_type = question_types[(progress.review_count + progress.mastery_level) % len(question_types)]
    if question_type == "word_to_meaning":
        return _attach_word_speech({
            "word_id": word.id,
            "question_type": question_type,
            "answer_mode": "choice",
            "stem": word.word,
            "helper_text": word.part_of_speech or "",
            "reference_text": "",
            "reference_translation": "",
            "options": _build_meaning_options(word),
            "adaptive_reason": adaptive_reason,
        }, word)
    if question_type == "example_to_word":
        return {
            "word_id": word.id,
            "question_type": question_type,
            "answer_mode": "choice",
            "stem": _mask_word(word.example_sentence, word.word),
            "helper_text": word.example_translation or word.meaning_cn,
            "reference_text": word.word,
            "reference_translation": "",
            "options": _build_word_options(word),
            "adaptive_reason": adaptive_reason,
        }
    if question_type == "spelling":
        return {
            "word_id": word.id,
            "question_type": question_type,
            "answer_mode": "input",
            "stem": word.meaning_cn,
            "helper_text": "请根据中文义项拼写对应单词。",
            "reference_text": "",
            "reference_translation": "",
            "options": [],
            "adaptive_reason": adaptive_reason,
        }
    if question_type == "listening_to_word":
        return _attach_word_speech({
            "word_id": word.id,
            "question_type": question_type,
            "answer_mode": "choice",
            "stem": "听发音，选择你听到的单词",
            "helper_text": "可在学习设置里调整全局语速后重复播放。",
            "reference_text": "",
            "reference_translation": "",
            "options": _build_word_options(word),
            "adaptive_reason": adaptive_reason,
        }, word)
    return {
        "word_id": word.id,
        "question_type": question_type,
        "answer_mode": "choice",
        "stem": word.meaning_cn,
        "helper_text": word.part_of_speech or "",
        "reference_text": "",
        "reference_translation": "",
        "options": _build_word_options(word),
        "adaptive_reason": adaptive_reason,
    }


def _expected_answer(word, question_type):
    if question_type == "word_to_meaning":
        return word.meaning_cn
    return word.word


def _evaluate_answer(word, question_type, user_answer):
    expected_answer = _expected_answer(word, question_type)
    user_answer = (user_answer or "").strip()
    if question_type == "spelling":
        similarity = text_similarity_score(expected_answer, user_answer)
        is_correct = is_text_answer_correct(expected_answer, user_answer)
    elif question_type == "word_to_meaning":
        similarity = text_similarity_score(expected_answer, user_answer)
        is_correct = normalize_answer_text(expected_answer) == normalize_answer_text(user_answer)
    else:
        similarity = text_similarity_score(expected_answer, user_answer)
        is_correct = normalize_answer_text(expected_answer) == normalize_answer_text(user_answer)
    quality = infer_quality(question_type, is_correct, similarity)
    return expected_answer, is_correct, similarity, quality


def _lookup_selected_word_text(user_answer):
    selected = (user_answer or "").strip()
    if not selected:
        return ""
    word = Word.objects.filter(word__iexact=selected).first()
    if not word:
        return ""
    return f"{word.word} 的常见意思是“{word.meaning_cn}”。"


def _normalize_review_answer_payload(answer):
    normalized = dict(answer or {})
    if not normalized.get("user_answer") and normalized.get("result"):
        normalized["user_answer"] = normalized.get("result", "")
    return normalized


def _validate_review_answer_payload(answer, question_hint):
    expected_question_type = str((question_hint or {}).get("question_type") or "").strip()
    question_type = str((answer or {}).get("question_type") or "").strip()
    if not question_type:
        raise ValueError("question_type required")
    if expected_question_type and question_type != expected_question_type:
        raise ValueError("question_type mismatch")

    answer_mode = str((question_hint or {}).get("answer_mode") or "").strip()
    user_answer = str((answer or {}).get("user_answer") or "").strip()
    option_values = {
        str(item.get("value") or "").strip()
        for item in (question_hint or {}).get("options", [])
        if str(item.get("value") or "").strip()
    }
    if answer_mode == "choice":
        if not user_answer:
            raise ValueError("choice answer required")
        if option_values and user_answer not in option_values:
            raise ValueError("choice answer not in options")
    elif answer_mode == "input" and not user_answer:
        raise ValueError("input answer required")


def _build_answer_feedback(word, question_type, user_answer, expected_answer, is_correct, similarity, quality):
    label = QUESTION_TYPE_LABELS.get(question_type, "复习题")
    score_percent = int(round(float(similarity or 0) * 100))
    feedback = {
        "source": "rule",
        "label": label,
        "similarity": score_percent,
        "quality": quality,
        "word": word.word,
        "meaning_cn": word.meaning_cn,
        "part_of_speech": word.part_of_speech or "",
        "example_sentence": word.example_sentence or "",
        "example_translation": word.example_translation or "",
        "speech_text": word.example_sentence or word.word,
        "speech_lang": "en-US",
        "usage_tip": "",
    }

    if is_correct:
        feedback.update({
            "source": "rule",
            "status": "correct",
            "title": "答对了，继续巩固这组记忆",
            "explanation": f"这题考的是“{word.word}”和“{expected_answer}”之间的对应关系，你已经匹配正确。",
            "recovery_tip": f"再把它放回例句里读一遍：{word.example_sentence or word.word}",
            "usage_tip": "现在把正确释义、词性和例句一起过一遍，能把这次正确记忆压得更稳。",
        })
        return feedback

    if question_type == "spelling":
        explanation = f"正确拼写是“{expected_answer}”，你的答案是“{user_answer or '未填写'}”，文本相似度约 {score_percent}%。"
        recovery_tip = "先按音节或字母块拆开记，再默写一遍，避免只记住中文释义。"
        usage_tip = "拼写题更适合把单词、词性和例句连着读，再自己默写一次。"
    elif question_type == "word_to_meaning":
        explanation = f"“{word.word}”在当前词书里主要对应“{expected_answer}”，你的选择还没有命中核心中文义项。"
        recovery_tip = f"把词性一起记：{word.part_of_speech or '词性待补充'} + {word.meaning_cn}。"
        usage_tip = "先把核心中文义项记准，再回到例句里确认这个词在真实语境中的意思。"
    elif question_type == "meaning_to_word":
        selected_note = _lookup_selected_word_text(user_answer)
        explanation = f"题目给出的中文义项对应“{expected_answer}”，你选择的是“{user_answer or '未选择'}”。"
        if selected_note:
            explanation = f"{explanation}{selected_note}"
        recovery_tip = "先从中文义项反推出英文，再回到例句确认语境，减少相近词混淆。"
        usage_tip = "易混词题先区分中文义项，再看例句里这个词真正放在什么场景。"
    elif question_type == "example_to_word":
        explanation = f"例句空格里需要的是“{expected_answer}”。它在这句话里承担当前词义“{word.meaning_cn}”。"
        recovery_tip = "读例句时先抓空格前后的搭配，再判断最自然的单词。"
        usage_tip = "例句题要重点看搭配和语境，顺手把整句朗读一遍会更容易记住。"
    elif question_type == "listening_to_word":
        explanation = f"这段发音对应“{expected_answer}”，你选择的是“{user_answer or '未选择'}”。"
        recovery_tip = "听音辨词时先抓重音和开头音，再和词形配对；必要时去学习设置里调慢全局语速。"
        usage_tip = "听力题答完后再对照例句朗读一次，可以把音、形、义重新绑定起来。"
    else:
        explanation = f"正确答案是“{expected_answer}”，你的答案是“{user_answer or '未填写'}”。"
        recovery_tip = "先记核心对应关系，再用例句做一次确认。"
        usage_tip = "先看清核心释义，再把它放回例句语境里确认。"

    feedback.update({
        "status": "wrong",
        "title": "这题答错了，先看错因再进入下一题",
        "explanation": explanation,
        "recovery_tip": recovery_tip,
        "usage_tip": usage_tip,
    })
    return feedback


def _serialize_wrong_word(item):
    return {
        "id": item.id,
        "word_id": item.word_id,
        "word": item.word.word,
        "meaning_cn": item.word.meaning_cn,
        "wrong_count": item.wrong_count,
        "source": item.source,
        "last_wrong_at": item.last_wrong_at,
    }


def generate_review_tasks(user, limit=10):
    limit = max(int(limit or 10), 1)
    plan = get_current_plan(user)
    adaptive_profile = build_adaptive_profile(user, plan)
    candidate_limit = max(limit * 4, 24)

    queryset = (
        WordProgress.objects.select_related("word", "book")
        .filter(user=user, review_due_at__isnull=False, review_due_at__lte=timezone.now())
        .order_by("review_due_at", "id")
    )
    progresses = list(queryset[:candidate_limit])
    if not progresses:
        progresses = list(
            WordProgress.objects.select_related("word", "book")
            .filter(user=user, learn_count__gt=0)
            .order_by("-updated_at")[:candidate_limit]
        )

    if not progresses:
        return {"session_id": None, "list": [], "adaptive": adaptive_profile}

    ranked_progresses = annotate_review_progresses(progresses, adaptive_profile)[:limit]
    question_list = [
        _build_review_question(
            item["progress"],
            adaptive_reason=item["reason"],
        )
        for item in ranked_progresses
    ]
    session = ReviewSession.objects.create(
        user=user,
        plan=plan,
        session_type="daily",
        total_count=len(ranked_progresses),
        started_at=timezone.now(),
        extra_payload={"questions": question_list},
    )
    return {
        "session_id": session.id,
        "list": question_list,
        "adaptive": adaptive_profile,
    }


def submit_review(user, session_id, answers):
    session = ReviewSession.objects.get(id=session_id, user=user)
    correct_count = 0
    submitted_results = []
    now = timezone.now()
    question_lookup = {
        int(item.get("word_id")): item
        for item in (session.extra_payload or {}).get("questions", [])
        if item.get("word_id") is not None
    }

    for answer in answers:
        normalized_answer = _normalize_review_answer_payload(answer)
        if not normalized_answer.get("word_id"):
            raise ValueError("word_id required")
        word = Word.objects.select_related("book").get(id=normalized_answer["word_id"])
        question_hint = question_lookup.get(word.id, {})
        if not question_hint:
            raise ValueError("question not found in session")
        _validate_review_answer_payload(normalized_answer, question_hint)
        question_type = normalized_answer.get("question_type", "")
        user_answer = normalized_answer.get("user_answer", "")
        expected_answer, is_correct, similarity, quality = _evaluate_answer(word, question_type, user_answer)
        answer_feedback = _build_answer_feedback(
            word,
            question_type,
            user_answer,
            expected_answer,
            is_correct,
            similarity,
            quality,
        )

        record = ReviewRecord.objects.create(
            session=session,
            user=user,
            word=word,
            question_type=question_type,
            user_answer=user_answer,
            correct_answer=expected_answer,
            is_correct=is_correct,
            answer_feedback=answer_feedback,
            reviewed_at=now,
        )
        submitted_results.append(
            {
                "record_id": record.id,
                "word_id": record.word_id,
                "word": word.word,
                "question_type": record.question_type,
                "user_answer": record.user_answer,
                "correct_answer": record.correct_answer,
                "is_correct": record.is_correct,
                "answer_feedback": record.answer_feedback,
            }
        )

        progress, _ = WordProgress.objects.get_or_create(user=user, word=word, defaults={"book": word.book})
        progress.review_count += 1
        progress.last_reviewed_at = now
        if is_correct:
            correct_count += 1
            progress.correct_count += 1
            progress.mastery_level = min(progress.mastery_level + 1, 5)
            wrong_word = WrongWord.objects.filter(user=user, word=word, is_active=True).first()
            if wrong_word and progress.mastery_level >= 3:
                wrong_word.is_active = False
                wrong_word.save(update_fields=["is_active", "updated_at"])
        else:
            progress.wrong_count += 1
            progress.mastery_level = max(progress.mastery_level - 1, 0)
            wrong_word, created = WrongWord.objects.get_or_create(
                user=user,
                word=word,
                defaults={
                    "wrong_count": 1,
                    "source": "review",
                    "last_wrong_at": now,
                    "is_active": True,
                },
            )
            if not created:
                wrong_word.wrong_count += 1
                wrong_word.last_wrong_at = now
                wrong_word.is_active = True
                wrong_word.save()

        apply_srs_schedule(progress, is_correct, quality, now)
        progress.save()

    session.finished_count += len(answers)
    session.correct_count += correct_count
    if session.finished_count >= session.total_count:
        session.status = "completed"
        session.completed_at = now
    session.save()

    plan = get_current_plan(user)
    if plan:
        task = get_or_create_today_task(user, plan)
        task.reviewed_count = min(task.reviewed_count + len(answers), task.review_word_target)
        task.save()

    accuracy = round((session.correct_count / session.finished_count) * 100, 2) if session.finished_count else 0
    return {
        "session_id": session.id,
        "finished_count": session.finished_count,
        "correct_count": session.correct_count,
        "accuracy": accuracy,
        "status": session.status,
        "answers": submitted_results,
    }


def get_review_result(user, session_id):
    session = ReviewSession.objects.get(id=session_id, user=user)
    records = session.records.select_related("word").order_by("id")
    accuracy = round((session.correct_count / session.finished_count) * 100, 2) if session.finished_count else 0
    return {
        "session_id": session.id,
        "total_count": session.total_count,
        "finished_count": session.finished_count,
        "correct_count": session.correct_count,
        "accuracy": accuracy,
        "status": session.status,
        "records": [
            {
                "word": item.word.word,
                "question_type": item.question_type,
                "user_answer": item.user_answer,
                "correct_answer": item.correct_answer,
                "is_correct": item.is_correct,
                "answer_feedback": item.answer_feedback,
            }
            for item in records
        ],
    }


def list_wrong_words(user):
    queryset = WrongWord.objects.filter(user=user, is_active=True).select_related("word").order_by("-last_wrong_at")
    return [_serialize_wrong_word(item) for item in queryset]


def remove_wrong_word(user, word_id):
    WrongWord.objects.filter(user=user, word_id=word_id).update(is_active=False)
