import random
import re

from django.utils import timezone

from apps.books.models import Book, Word
from apps.learn.models import WordProgress
from apps.learn.srs import apply_srs_schedule, infer_quality, is_text_answer_correct, normalize_answer_text, text_similarity_score
from apps.plans.services import get_current_plan, get_or_create_today_task
from apps.review.models import WrongWord
from apps.users.services import ensure_user_setting

from .models import TestAnswer, TestQuestion, TestSession


DIFFICULTY_TO_CEFR = {
    1: "A2",
    2: "B1",
    3: "C1",
}


def _pick_distractors(word, count=3):
    used_ids = {word.id}
    distractors = []
    candidate_groups = [
        Word.objects.filter(book=word.book, part_of_speech=word.part_of_speech).exclude(id=word.id),
        Word.objects.filter(book=word.book).exclude(id=word.id),
        Word.objects.exclude(id=word.id),
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


def _choice_values(word, question_type):
    if question_type == "word_to_meaning":
        values = [item.meaning_cn for item in _pick_distractors(word, count=3)] + [word.meaning_cn]
    else:
        values = [item.word for item in _pick_distractors(word, count=3)] + [word.word]
    values = list(dict.fromkeys(values))
    while len(values) < 4:
        filler = f"选项{len(values) + 1}"
        if filler not in values:
            values.append(filler)
    random.shuffle(values)
    return values[:4]


def _mask_word(sentence, word_text):
    pattern = re.compile(r"\b{}\b".format(re.escape(word_text)), re.IGNORECASE)
    masked, count = pattern.subn("____", sentence or "", count=1)
    return masked if count else sentence


def _select_question_type(word, seed_value):
    available = ["word_to_meaning", "meaning_to_word"]
    if word.example_sentence:
        available.append("example_to_word")
    if word.difficulty >= 2:
        available.append("spelling")
    return available[seed_value % len(available)]


def _question_payload(word, question_type):
    if question_type == "word_to_meaning":
        values = _choice_values(word, question_type)
        correct_option = chr(65 + values.index(word.meaning_cn))
        return {
            "question_type": question_type,
            "answer_mode": "choice",
            "stem": word.word,
            "option_a": values[0],
            "option_b": values[1],
            "option_c": values[2],
            "option_d": values[3],
            "correct_option": correct_option,
            "answer_text": word.meaning_cn,
            "explanation": word.meaning_cn,
        }
    if question_type == "example_to_word":
        values = _choice_values(word, "meaning_to_word")
        correct_option = chr(65 + values.index(word.word))
        return {
            "question_type": question_type,
            "answer_mode": "choice",
            "stem": f"{_mask_word(word.example_sentence, word.word)}\n{word.example_translation or ''}".strip(),
            "option_a": values[0],
            "option_b": values[1],
            "option_c": values[2],
            "option_d": values[3],
            "correct_option": correct_option,
            "answer_text": word.word,
            "explanation": word.meaning_cn,
        }
    if question_type == "spelling":
        return {
            "question_type": question_type,
            "answer_mode": "input",
            "stem": f"根据中文释义写出单词：{word.meaning_cn}\n例句：{word.example_sentence or '无'}",
            "option_a": "",
            "option_b": "",
            "option_c": "",
            "option_d": "",
            "correct_option": "",
            "answer_text": word.word,
            "explanation": word.meaning_cn,
        }
    values = _choice_values(word, "meaning_to_word")
    correct_option = chr(65 + values.index(word.word))
    return {
        "question_type": question_type,
        "answer_mode": "choice",
        "stem": word.meaning_cn,
        "option_a": values[0],
        "option_b": values[1],
        "option_c": values[2],
        "option_d": values[3],
        "correct_option": correct_option,
        "answer_text": word.word,
        "explanation": word.example_sentence or word.meaning_cn,
    }


def _serialize_question(question):
    return {
        "question_id": question.id,
        "stem": question.stem,
        "question_type": question.question_type,
        "answer_mode": question.answer_mode,
        "cefr_tag": question.cefr_tag,
        "options": {
            "A": question.option_a,
            "B": question.option_b,
            "C": question.option_c,
            "D": question.option_d,
        },
    }


def _build_questions(session, words, session_type="practice"):
    questions = []
    for index, word in enumerate(words, start=1):
        question_type = _select_question_type(word, index + word.id)
        payload = _question_payload(word, question_type)
        question = TestQuestion.objects.create(
            test_session=session,
            word=word,
            difficulty_level=word.difficulty,
            cefr_tag=DIFFICULTY_TO_CEFR.get(word.difficulty, "A2"),
            **payload,
        )
        questions.append(question)
    return questions


def _resolve_book_for_test(user, book_id=None):
    if book_id:
        return Book.objects.filter(id=book_id).first()
    current_plan = get_current_plan(user)
    if current_plan:
        return current_plan.book
    return Book.objects.order_by("id").first()


def generate_test(user, question_count, book_id=None):
    book = _resolve_book_for_test(user, book_id)
    if not book:
        raise ValueError("book not found")

    words = list(Word.objects.filter(book=book).order_by("order_in_book", "id"))
    if not words:
        raise ValueError("no words found in selected book")
    if len(words) > question_count:
        words = random.sample(words, question_count)
    else:
        words = words[:question_count]

    session = TestSession.objects.create(
        user=user,
        book=book,
        title=f"{book.name} quick test",
        session_type="practice",
        question_count=len(words),
        started_at=timezone.now(),
    )
    questions = _build_questions(session, words, session_type="practice")
    return {
        "test_id": session.id,
        "session_type": session.session_type,
        "book": {"id": book.id, "name": book.name},
        "questions": [_serialize_question(item) for item in questions],
    }


def _placement_word_pool(question_count):
    difficulty_buckets = {
        1: list(Word.objects.filter(difficulty=1).order_by("id")[:200]),
        2: list(Word.objects.filter(difficulty=2).order_by("id")[:200]),
        3: list(Word.objects.filter(difficulty=3).order_by("id")[:200]),
    }
    targets = {
        1: max(2, round(question_count * 0.4)),
        2: max(2, round(question_count * 0.35)),
        3: max(2, question_count - max(2, round(question_count * 0.4)) - max(2, round(question_count * 0.35))),
    }
    words = []
    for difficulty, count in targets.items():
        bucket = difficulty_buckets[difficulty]
        if not bucket:
            continue
        if len(bucket) > count:
            words.extend(random.sample(bucket, count))
        else:
            words.extend(bucket)
    if len(words) < question_count:
        existing_ids = {item.id for item in words}
        fallback_pool = list(Word.objects.exclude(id__in=existing_ids).order_by("id")[:400])
        random.shuffle(fallback_pool)
        words.extend(fallback_pool[: max(question_count - len(words), 0)])
    if len(words) > question_count:
        words = random.sample(words, question_count)
    return words[:question_count]


def generate_placement_test(user, question_count=18):
    words = _placement_word_pool(question_count)
    if not words:
        raise ValueError("no words available for placement test")
    session = TestSession.objects.create(
        user=user,
        title="English Placement Test",
        session_type="placement",
        question_count=len(words),
        started_at=timezone.now(),
    )
    questions = _build_questions(session, words, session_type="placement")
    return {
        "test_id": session.id,
        "session_type": session.session_type,
        "book": None,
        "questions": [_serialize_question(item) for item in questions],
    }


def _evaluate_question_answer(question, answer):
    normalized_answer = dict(answer or {})
    if not normalized_answer.get("selected_option") and normalized_answer.get("answer"):
        selected_value = str(normalized_answer.get("answer") or "").strip()
        option_map = {
            str(getattr(question, field) or "").strip(): key
            for field, key in (
                ("option_a", "A"),
                ("option_b", "B"),
                ("option_c", "C"),
                ("option_d", "D"),
            )
            if str(getattr(question, field) or "").strip()
        }
        normalized_answer["selected_option"] = option_map.get(selected_value, selected_value[:1].upper())
    selected_option = (normalized_answer.get("selected_option") or "").upper().strip()
    submitted_text = (normalized_answer.get("submitted_text") or "").strip()
    if question.answer_mode == "input":
        if not submitted_text:
            raise ValueError("submitted_text required")
        similarity = text_similarity_score(question.answer_text, submitted_text)
        is_correct = is_text_answer_correct(question.answer_text, submitted_text)
        quality = infer_quality(question.question_type, is_correct, similarity)
        return is_correct, quality, "", submitted_text

    if not selected_option:
        raise ValueError("selected_option required")
    if selected_option not in {"A", "B", "C", "D"}:
        raise ValueError("selected_option invalid")
    is_correct = selected_option == question.correct_option
    quality = infer_quality(question.question_type, is_correct, 100 if is_correct else 0)
    return is_correct, quality, selected_option, submitted_text


def _update_word_progress(user, question, is_correct, quality, now):
    progress, _ = WordProgress.objects.get_or_create(user=user, word=question.word, defaults={"book": question.word.book})
    progress.last_tested_at = now
    if is_correct:
        progress.correct_count += 1
        progress.mastery_level = min(progress.mastery_level + 1, 5)
    else:
        progress.wrong_count += 1
        progress.mastery_level = max(progress.mastery_level - 1, 0)
        wrong_word, created = WrongWord.objects.get_or_create(
            user=user,
            word=question.word,
            defaults={
                "wrong_count": 1,
                "source": "test",
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


def submit_test(user, test_id, answers):
    session = TestSession.objects.get(id=test_id, user=user)
    correct_count = 0
    now = timezone.now()

    for answer in answers:
        question = TestQuestion.objects.select_related("word", "word__book").get(id=answer["question_id"], test_session=session)
        is_correct, quality, selected_option, submitted_text = _evaluate_question_answer(question, answer)
        TestAnswer.objects.update_or_create(
            test_session=session,
            question=question,
            defaults={
                "user": user,
                "selected_option": selected_option,
                "submitted_text": submitted_text,
                "is_correct": is_correct,
                "answered_at": now,
            },
        )
        if is_correct:
            correct_count += 1
        _update_word_progress(user, question, is_correct, quality, now)

    session.correct_count = correct_count
    session.score = round((correct_count / session.question_count) * 100, 2) if session.question_count else 0
    session.status = "completed"
    session.completed_at = now
    session.save()

    plan = get_current_plan(user)
    if plan:
        task = get_or_create_today_task(user, plan)
        task.test_count += 1
        task.save()

    return {
        "test_id": session.id,
        "question_count": session.question_count,
        "correct_count": session.correct_count,
        "score": session.score,
        "status": session.status,
        "session_type": session.session_type,
    }


def _score_to_cefr(score):
    if score < 45:
        return "A1"
    if score < 60:
        return "A2"
    if score < 75:
        return "B1"
    if score < 88:
        return "B2"
    if score < 96:
        return "C1"
    return "C2"


def _recommend_focus(cefr_level):
    mapping = {
        "A1": "先补基础词汇、常用句型和发音模仿。",
        "A2": "继续巩固高频词、基础时态和简单阅读。",
        "B1": "重点提升语法稳定性、场景表达和输入量。",
        "B2": "加强长难句、写作表达和输出准确度。",
        "C1": "进入高阶阅读、学术表达和复杂语义辨析。",
        "C2": "保持高阶输入输出，重点做精细化纠错和表达升级。",
    }
    return mapping.get(cefr_level, "继续保持系统学习。")


def _recommend_daily_target(cefr_level):
    mapping = {
        "A1": 12,
        "A2": 18,
        "B1": 24,
        "B2": 28,
        "C1": 32,
        "C2": 36,
    }
    return mapping.get(cefr_level, 20)


def _recommend_book(cefr_level):
    tokens = [cefr_level.lower(), cefr_level.upper()]
    for token in tokens:
        book = (
            Book.objects.filter(status="active")
            .filter(level__icontains=token)
            .order_by("id")
            .first()
        )
        if book:
            return {"id": book.id, "name": book.name}
    book = Book.objects.filter(status="active").order_by("id").first()
    return {"id": book.id, "name": book.name} if book else None


def submit_placement_test(user, test_id, answers):
    result = submit_test(user, test_id, answers)
    session = TestSession.objects.get(id=test_id, user=user)
    score = float(session.score or 0)
    cefr_level = _score_to_cefr(score)
    recommendation = {
        "cefr_level": cefr_level,
        "daily_target": _recommend_daily_target(cefr_level),
        "focus": _recommend_focus(cefr_level),
        "book": _recommend_book(cefr_level),
    }
    session.cefr_result = cefr_level
    session.extra_payload = recommendation
    session.save(update_fields=["cefr_result", "extra_payload", "updated_at"])

    setting = ensure_user_setting(user)
    setting.cefr_level = cefr_level
    setting.placement_score = session.score
    setting.placement_completed_at = timezone.now()
    setting.save(update_fields=["cefr_level", "placement_score", "placement_completed_at", "updated_at"])

    result.update(
        {
            "cefr_level": cefr_level,
            "recommendation": recommendation,
        }
    )
    return result


def get_test_result(user, test_id):
    session = TestSession.objects.get(id=test_id, user=user)
    answers = session.answers.select_related("question").order_by("id")
    return {
        "test_id": session.id,
        "title": session.title,
        "session_type": session.session_type,
        "question_count": session.question_count,
        "correct_count": session.correct_count,
        "score": session.score,
        "status": session.status,
        "cefr_result": session.cefr_result,
        "recommendation": session.extra_payload or {},
        "answers": [
            {
                "question_id": item.question_id,
                "selected_option": item.selected_option,
                "submitted_text": item.submitted_text,
                "correct_option": item.question.correct_option,
                "answer_text": item.question.answer_text,
                "is_correct": item.is_correct,
            }
            for item in answers
        ],
    }


def list_test_history(user):
    sessions = TestSession.objects.filter(user=user).order_by("-id")
    return [
        {
            "test_id": item.id,
            "title": item.title,
            "session_type": item.session_type,
            "question_count": item.question_count,
            "correct_count": item.correct_count,
            "score": item.score,
            "status": item.status,
            "cefr_result": item.cefr_result,
            "completed_at": item.completed_at,
        }
        for item in sessions
    ]
