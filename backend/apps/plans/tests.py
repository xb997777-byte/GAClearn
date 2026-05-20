from django.test import TestCase

from apps.books.models import Book
from django.utils import timezone

from apps.plans.models import DailyTask, PlanRevision, UserPlan
from apps.plans.services import create_plan, get_or_create_today_task, switch_book, update_current_plan
from apps.users.models import WxUser


class PlanServiceTests(TestCase):
    def setUp(self):
        self.user = WxUser.objects.create(openid="test-openid", nickname="Tester")
        self.book_a = Book.objects.create(
            name="四级核心词",
            category="CET4",
            level="A2-B1",
            description="测试词书A",
            word_count=1200,
            status="active",
        )
        self.book_b = Book.objects.create(
            name="六级高频词",
            category="CET6",
            level="B1-B2",
            description="测试词书B",
            word_count=1800,
            status="active",
        )

    def test_create_plan_persists_json_safe_revision_snapshot(self):
        plan = create_plan(self.user, self.book_a.id, 20)

        revision = PlanRevision.objects.filter(plan=plan, source="create").order_by("-id").first()

        self.assertIsNotNone(revision)
        self.assertEqual(revision.after_snapshot["book"]["id"], self.book_a.id)
        self.assertIsInstance(revision.after_snapshot["start_date"], str)
        self.assertEqual(plan.status, "active")

    def test_switch_book_keeps_progress_and_creates_switch_revision(self):
        original_plan = create_plan(self.user, self.book_a.id, 20)
        original_plan.finished_word_count = 36
        original_plan.save(update_fields=["finished_word_count", "updated_at"])

        new_plan = switch_book(self.user, self.book_b.id, daily_target=30, keep_progress=True)

        self.assertEqual(new_plan.book_id, self.book_b.id)
        self.assertEqual(new_plan.daily_target, 30)
        self.assertEqual(new_plan.finished_word_count, 36)
        self.assertEqual(UserPlan.objects.filter(user=self.user, status="active").count(), 1)
        self.assertTrue(
            PlanRevision.objects.filter(
                plan=new_plan,
                source="switch_book",
                metadata__previous_plan_id=original_plan.id,
            ).exists()
        )

    def test_update_plan_syncs_today_task_new_word_target(self):
        plan = create_plan(self.user, self.book_a.id, 6)
        task = get_or_create_today_task(self.user, plan)
        self.assertEqual(task.new_word_target, 6)

        update_current_plan(self.user, {"daily_target": 55})

        task.refresh_from_db()
        self.assertEqual(task.new_word_target, 55)

    def test_update_plan_does_not_shrink_below_today_learned_count(self):
        plan = create_plan(self.user, self.book_a.id, 20)
        task = DailyTask.objects.get(user=self.user, task_date=timezone.localdate())
        task.learned_count = 12
        task.new_word_target = 20
        task.save(update_fields=["learned_count", "new_word_target", "updated_at"])

        update_current_plan(self.user, {"daily_target": 6})

        task.refresh_from_db()
        self.assertEqual(task.new_word_target, 12)

    def test_serialize_plan_returns_structured_empty_state_for_none(self):
        from apps.plans.services import serialize_plan

        payload = serialize_plan(None)
        self.assertEqual(payload["status"], "empty")
        self.assertIsNone(payload["book"])
        self.assertEqual(payload["daily_target"], 0)
