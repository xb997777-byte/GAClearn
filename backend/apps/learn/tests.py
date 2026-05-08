from django.test import TestCase
from django.utils import timezone

from apps.books.models import Book, Word
from apps.learn.services import get_today_words
from apps.plans.models import DailyTask, UserPlan
from apps.users.models import UserSetting, WxUser


class LearnServiceTests(TestCase):
    def setUp(self):
        self.user = WxUser.objects.create(openid="learn-test-user", nickname="Learn Test")
        self.today = timezone.localdate()
        self.book = Book.objects.create(
            name="测试词书",
            category="cet4",
            level="basic",
            word_count=3,
        )
        for index in range(1, 4):
            Word.objects.create(
                book=self.book,
                word=f"word-{index}",
                meaning_cn=f"词义{index}",
                order_in_book=index,
            )

    def test_get_today_words_creates_today_task_from_plan_target(self):
        UserSetting.objects.create(user=self.user, daily_target=30)
        UserPlan.objects.create(
            user=self.user,
            book=self.book,
            daily_target=20,
            start_date=self.today,
            status="active",
        )

        payload = get_today_words(self.user)

        self.assertEqual(payload["target_count"], 20)
        self.assertEqual(payload["plan_daily_target"], 20)
        self.assertEqual(payload["task_new_word_target"], 20)

    def test_get_today_words_uses_existing_unstarted_task_target(self):
        UserSetting.objects.create(user=self.user, daily_target=30)
        plan = UserPlan.objects.create(
            user=self.user,
            book=self.book,
            daily_target=20,
            start_date=self.today,
            status="active",
        )
        DailyTask.objects.create(
            user=self.user,
            plan=plan,
            task_date=self.today,
            new_word_target=10,
            review_word_target=5,
            is_started=False,
            is_finished=False,
        )

        payload = get_today_words(self.user)

        self.assertEqual(payload["target_count"], 10)
        self.assertEqual(payload["task_new_word_target"], 10)

    def test_get_today_words_clamps_requested_limit(self):
        UserSetting.objects.create(user=self.user, daily_target=20)
        UserPlan.objects.create(
            user=self.user,
            book=self.book,
            daily_target=20,
            start_date=self.today,
            status="active",
        )

        payload = get_today_words(self.user, limit=9999)

        self.assertEqual(payload["target_count"], 200)
