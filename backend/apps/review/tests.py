from django.test import TestCase

from apps.books.models import Book, Word
from apps.learn.models import WordProgress
from apps.review.models import ReviewSession
from apps.review.services import _build_answer_feedback, _build_meaning_options, _build_review_question, submit_review
from apps.users.models import WxUser


class ReviewQuestionContractTests(TestCase):
    def setUp(self):
        self.user = WxUser.objects.create(openid="review-contract-user", nickname="Review Contract")
        self.book = Book.objects.create(
            name="测试词书",
            category="cet4",
            level="基础",
            description="",
            word_count=1,
            status="active",
        )
        self.word = Word.objects.create(
            book=self.book,
            word="astronomy",
            part_of_speech="n.",
            meaning_cn="天文学",
            example_sentence="I'm keen on astronomy.",
            example_translation="我热衷于天文学。",
            order_in_book=1,
        )

    def test_word_to_meaning_question_does_not_expose_example_before_answer(self):
        progress = WordProgress.objects.create(
            user=self.user,
            book=self.book,
            word=self.word,
            review_count=1,
            mastery_level=0,
        )

        question = _build_review_question(progress, adaptive_reason="测试")

        self.assertEqual(question["question_type"], "word_to_meaning")
        self.assertEqual(question["stem"], "astronomy")
        self.assertEqual(question["helper_text"], "n.")
        self.assertEqual(question["reference_text"], "")
        self.assertEqual(question["reference_translation"], "")

    def test_answer_feedback_exposes_meaning_example_and_speech_after_submit(self):
        feedback = _build_answer_feedback(
            self.word,
            "word_to_meaning",
            "天文学",
            "天文学",
            True,
            1,
            "good",
        )

        self.assertEqual(feedback["meaning_cn"], "天文学")
        self.assertEqual(feedback["part_of_speech"], "n.")
        self.assertEqual(feedback["example_sentence"], "I'm keen on astronomy.")
        self.assertEqual(feedback["example_translation"], "我热衷于天文学。")
        self.assertEqual(feedback["speech_text"], "I'm keen on astronomy.")

    def test_meaning_options_skip_blank_meanings(self):
        Word.objects.create(
            book=self.book,
            word="blankmeaning",
            part_of_speech="n.",
            meaning_cn="",
            example_sentence="",
            example_translation="",
            order_in_book=2,
        )
        Word.objects.create(
            book=self.book,
            word="planet",
            part_of_speech="n.",
            meaning_cn="行星",
            example_sentence="The planet is bright tonight.",
            example_translation="这颗行星今晚很亮。",
            order_in_book=3,
        )
        Word.objects.create(
            book=self.book,
            word="galaxy",
            part_of_speech="n.",
            meaning_cn="星系",
            example_sentence="We live in the Milky Way galaxy.",
            example_translation="我们生活在银河系。",
            order_in_book=4,
        )
        Word.objects.create(
            book=self.book,
            word="comet",
            part_of_speech="n.",
            meaning_cn="彗星",
            example_sentence="A comet crossed the sky.",
            example_translation="一颗彗星划过天空。",
            order_in_book=5,
        )

        options = _build_meaning_options(self.word)

        self.assertTrue(options)
        self.assertTrue(all((item.get("value") or "").strip() for item in options))

    def test_submit_review_rejects_question_type_mismatch(self):
        session = ReviewSession.objects.create(
            user=self.user,
            total_count=1,
            extra_payload={
                "questions": [
                    {
                        "word_id": self.word.id,
                        "question_type": "word_to_meaning",
                        "answer_mode": "choice",
                        "options": [{"key": "A", "value": "天文学"}],
                    }
                ]
            },
        )

        with self.assertRaisesMessage(ValueError, "question_type mismatch"):
            submit_review(
                self.user,
                session.id,
                [{"word_id": self.word.id, "question_type": "meaning_to_word", "user_answer": "astronomy"}],
            )

    def test_submit_review_requires_question_type(self):
        session = ReviewSession.objects.create(
            user=self.user,
            total_count=1,
            extra_payload={
                "questions": [
                    {
                        "word_id": self.word.id,
                        "question_type": "word_to_meaning",
                        "answer_mode": "choice",
                        "options": [{"key": "A", "value": "天文学"}],
                    }
                ]
            },
        )

        with self.assertRaisesMessage(ValueError, "question_type required"):
            submit_review(
                self.user,
                session.id,
                [{"word_id": self.word.id, "user_answer": "天文学"}],
            )

    def test_submit_review_rejects_choice_answer_not_in_options(self):
        session = ReviewSession.objects.create(
            user=self.user,
            total_count=1,
            extra_payload={
                "questions": [
                    {
                        "word_id": self.word.id,
                        "question_type": "word_to_meaning",
                        "answer_mode": "choice",
                        "options": [{"key": "A", "value": "天文学"}],
                    }
                ]
            },
        )

        with self.assertRaisesMessage(ValueError, "choice answer not in options"):
            submit_review(
                self.user,
                session.id,
                [{"word_id": self.word.id, "question_type": "word_to_meaning", "user_answer": "错误答案"}],
            )

    def test_submit_review_rejects_question_not_found_in_session(self):
        other_word = Word.objects.create(
            book=self.book,
            word="orbit",
            part_of_speech="n.",
            meaning_cn="轨道",
            example_sentence="The satellite remained in orbit.",
            example_translation="卫星保持在轨道上。",
            order_in_book=2,
        )
        session = ReviewSession.objects.create(
            user=self.user,
            total_count=1,
            extra_payload={
                "questions": [
                    {
                        "word_id": self.word.id,
                        "question_type": "word_to_meaning",
                        "answer_mode": "choice",
                        "options": [{"key": "A", "value": "天文学"}],
                    }
                ]
            },
        )

        with self.assertRaisesMessage(ValueError, "question not found in session"):
            submit_review(
                self.user,
                session.id,
                [{"word_id": other_word.id, "question_type": "word_to_meaning", "user_answer": "轨道"}],
            )
