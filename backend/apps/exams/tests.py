from django.test import TestCase

from apps.books.models import Book, Word
from apps.exams.services import generate_test, submit_test
from apps.users.models import WxUser


class ExamContractTests(TestCase):
    def setUp(self):
        self.user = WxUser.objects.create(openid="exam-contract-user", nickname="Exam Contract")
        self.book = Book.objects.create(name="测试词书", description="", word_count=1)
        self.word = Word.objects.create(
            book=self.book,
            word="important",
            meaning_cn="重要的",
            part_of_speech="adj.",
            difficulty=1,
            order_in_book=1,
        )

    def test_submit_test_accepts_legacy_answer_value_for_choice_question(self):
        test = generate_test(self.user, question_count=1, book_id=self.book.id)
        question = test["questions"][0]
        selected_value = question["options"]["A"]

        result = submit_test(
            self.user,
            test["test_id"],
            [{"question_id": question["question_id"], "answer": selected_value}],
        )

        self.assertEqual(result["test_id"], test["test_id"])
        self.assertEqual(result["question_count"], 1)

    def test_submit_test_rejects_empty_choice_answer(self):
        test = generate_test(self.user, question_count=1, book_id=self.book.id)
        question = test["questions"][0]

        with self.assertRaisesMessage(ValueError, "selected_option required"):
            submit_test(self.user, test["test_id"], [{"question_id": question["question_id"]}])
