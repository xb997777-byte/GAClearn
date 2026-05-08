import datetime
import math
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.books.models import Book
from apps.learn.adaptive import build_adaptive_profile
from apps.learn.models import WordProgress
from apps.review.models import WrongWord
from apps.users.services import ensure_user_setting

from .models import DailyTask, PlanRevision, UserPlan


def serialize_plan(plan):
    if plan is None:
        return None
    estimated_days = math.ceil((plan.book.word_count or 0) / max(plan.daily_target, 1))
    return {
        "id": plan.id,
        "book": {
            "id": plan.book.id,
            "name": plan.book.name,
            "category": plan.book.category,
            "word_count": plan.book.word_count,
        },
        "daily_target": plan.daily_target,
        "start_date": plan.start_date,
        "status": plan.status,
        "finished_word_count": plan.finished_word_count,
        "estimated_days": estimated_days,
    }


def _make_json_safe(value):
    if isinstance(value, dict):
        return {key: _make_json_safe(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_make_json_safe(item) for item in value]
    if isinstance(value, (datetime.date, datetime.datetime, datetime.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return value


def serialize_plan_revision(item):
    return {
        "id": item.id,
        "plan_id": item.plan_id,
        "source": item.source,
        "summary": item.summary,
        "patch_payload": item.patch_payload,
        "before_snapshot": item.before_snapshot,
        "after_snapshot": item.after_snapshot,
        "metadata": item.metadata,
        "rollback_from_id": item.rollback_from_id,
        "created_at": item.created_at,
    }


def serialize_daily_task(task):
    return {
        "id": task.id,
        "task_date": task.task_date,
        "new_word_target": task.new_word_target,
        "review_word_target": task.review_word_target,
        "learned_count": task.learned_count,
        "reviewed_count": task.reviewed_count,
        "test_count": task.test_count,
        "is_started": task.is_started,
        "is_finished": task.is_finished,
    }


def get_current_plan(user):
    return UserPlan.objects.select_related("book").filter(user=user, status="active").order_by("-id").first()


def get_manageable_plan(user):
    active_plan = get_current_plan(user)
    if active_plan:
        return active_plan
    return (
        UserPlan.objects.select_related("book")
        .filter(user=user, status="paused")
        .order_by("-id")
        .first()
    )


def _sync_daily_target_setting(user, daily_target):
    setting = ensure_user_setting(user)
    if setting.daily_target == daily_target:
        return
    setting.daily_target = daily_target
    setting.save(update_fields=["daily_target", "updated_at"])


def _snapshot_plan(plan):
    if not plan:
        return {}
    return _make_json_safe(serialize_plan(plan))


def _build_revision_summary(source, patch_payload):
    daily_target = patch_payload.get("daily_target")
    status = patch_payload.get("status")
    summary_bits = []
    if daily_target not in (None, ""):
        summary_bits.append(f"daily_target={daily_target}")
    if status:
        summary_bits.append(f"status={status}")
    detail = ", ".join(summary_bits) if summary_bits else "no fields"
    return f"{source}: {detail}"


def create_plan_revision(
    *,
    user,
    plan,
    source,
    before_snapshot,
    after_snapshot,
    patch_payload=None,
    summary="",
    metadata=None,
    rollback_from=None,
):
    return PlanRevision.objects.create(
        user=user,
        plan=plan,
        source=source,
        summary=summary or _build_revision_summary(source, patch_payload or {}),
        patch_payload=_make_json_safe(patch_payload or {}),
        before_snapshot=_make_json_safe(before_snapshot or {}),
        after_snapshot=_make_json_safe(after_snapshot or {}),
        metadata=_make_json_safe(metadata or {}),
        rollback_from=rollback_from,
    )


@transaction.atomic
def create_plan(user, book_id, daily_target):
    book = Book.objects.filter(id=book_id, status="active").first()
    if not book:
        raise ValueError("book not found")
    UserPlan.objects.filter(user=user, status="active").update(status="paused")
    plan = UserPlan.objects.create(
        user=user,
        book=book,
        daily_target=daily_target,
        start_date=timezone.localdate(),
        status="active",
    )
    _sync_daily_target_setting(user, daily_target)
    get_or_create_today_task(user, plan)
    create_plan_revision(
        user=user,
        plan=plan,
        source="create",
        before_snapshot={},
        after_snapshot=_snapshot_plan(plan),
        patch_payload={"book_id": book_id, "daily_target": daily_target, "status": "active"},
        summary=f"create: book_id={book_id}, daily_target={daily_target}",
    )
    return plan


def update_current_plan(user, payload, source="manual", summary="", metadata=None, rollback_from=None):
    plan = get_current_plan(user) or get_manageable_plan(user)
    if not plan:
        raise ValueError("plan not found")
    before_snapshot = _snapshot_plan(plan)
    for field in ("daily_target", "status"):
        if field in payload:
            setattr(plan, field, payload[field])
    if payload.get("status") == "active":
        UserPlan.objects.filter(user=user, status="active").exclude(id=plan.id).update(status="paused")
    plan.save()
    if "daily_target" in payload:
        _sync_daily_target_setting(user, plan.daily_target)
    if plan.status == "active":
        get_or_create_today_task(user, plan)
    create_plan_revision(
        user=user,
        plan=plan,
        source=source,
        before_snapshot=before_snapshot,
        after_snapshot=_snapshot_plan(plan),
        patch_payload=payload,
        summary=summary,
        metadata=metadata,
        rollback_from=rollback_from,
    )
    return plan


def switch_book(user, book_id, daily_target=None, keep_progress=False):
    current_plan = get_current_plan(user) or get_manageable_plan(user)
    target = daily_target or (current_plan.daily_target if current_plan else 20)
    new_plan = create_plan(user, book_id, target)
    if keep_progress and current_plan:
        new_plan.finished_word_count = current_plan.finished_word_count
        new_plan.save(update_fields=["finished_word_count", "updated_at"])
    create_plan_revision(
        user=user,
        plan=new_plan,
        source="switch_book",
        before_snapshot={},
        after_snapshot=_snapshot_plan(new_plan),
        patch_payload={"book_id": book_id, "daily_target": target, "keep_progress": keep_progress},
        summary=f"switch_book: book_id={book_id}, daily_target={target}",
        metadata={"previous_plan_id": current_plan.id if current_plan else None},
    )
    return new_plan


def get_or_create_today_task(user, plan):
    adaptive_profile = build_adaptive_profile(user, plan)
    review_target = WordProgress.objects.filter(
        user=user,
        review_due_at__isnull=False,
        review_due_at__lte=timezone.now(),
    ).count()
    task, _ = DailyTask.objects.get_or_create(
        user=user,
        task_date=timezone.localdate(),
        defaults={
            "plan": plan,
            "new_word_target": adaptive_profile["recommended_new_word_target"],
            "review_word_target": max(review_target, adaptive_profile["recommended_review_word_target"]),
        },
    )
    if not task.is_started and not task.is_finished:
        next_new_target = adaptive_profile["recommended_new_word_target"]
        next_review_target = max(review_target, adaptive_profile["recommended_review_word_target"])
        dirty_fields = []
        if task.plan_id != plan.id:
            task.plan = plan
            dirty_fields.append("plan")
        if task.new_word_target != next_new_target:
            task.new_word_target = next_new_target
            dirty_fields.append("new_word_target")
        if task.review_word_target != next_review_target:
            task.review_word_target = next_review_target
            dirty_fields.append("review_word_target")
        if dirty_fields:
            dirty_fields.append("updated_at")
            task.save(update_fields=dirty_fields)
    return task


def build_today_task_payload(user):
    plan = get_current_plan(user)
    if not plan:
        return {
            "plan": None,
            "task": None,
            "summary": {
                "new_words_remaining": 0,
                "review_words_remaining": 0,
                "wrong_words": 0,
            },
            "adaptive": None,
        }
    adaptive_profile = build_adaptive_profile(user, plan)
    task = get_or_create_today_task(user, plan)
    return {
        "plan": serialize_plan(plan),
        "task": serialize_daily_task(task),
        "summary": {
            "new_words_remaining": max(task.new_word_target - task.learned_count, 0),
            "review_words_remaining": max(task.review_word_target - task.reviewed_count, 0),
            "wrong_words": WrongWord.objects.filter(user=user, is_active=True).count(),
        },
        "adaptive": adaptive_profile,
    }


def mark_today_task_started(user):
    plan = get_current_plan(user)
    if not plan:
        raise ValueError("active plan not found")
    task = get_or_create_today_task(user, plan)
    task.is_started = True
    task.save(update_fields=["is_started", "updated_at"])
    return task


def mark_today_task_finished(user):
    plan = get_current_plan(user)
    if not plan:
        raise ValueError("active plan not found")
    task = get_or_create_today_task(user, plan)
    task.is_finished = True
    task.save(update_fields=["is_finished", "updated_at"])
    return task


def list_plan_revisions(user, limit=12):
    queryset = (
        PlanRevision.objects.filter(user=user)
        .select_related("plan", "plan__book")
        .order_by("-id")[: min(max(int(limit or 12), 1), 30)]
    )
    return [serialize_plan_revision(item) for item in queryset]


def apply_ai_plan_patch(user, patch_payload, summary="", metadata=None):
    if not isinstance(patch_payload, dict) or not patch_payload:
        raise ValueError("patch payload is empty")
    allowed_fields = {"daily_target", "status"}
    clean_payload = {key: value for key, value in patch_payload.items() if key in allowed_fields}
    if not clean_payload:
        raise ValueError("patch payload has no supported fields")
    return update_current_plan(
        user,
        clean_payload,
        source="ai_agent",
        summary=summary or "apply ai patch",
        metadata=metadata or {},
    )


@transaction.atomic
def rollback_plan_revision(user, revision_id):
    revision = PlanRevision.objects.select_related("plan").filter(user=user, id=revision_id).first()
    if not revision:
        raise ValueError("revision not found")
    target_snapshot = revision.before_snapshot or {}
    if not target_snapshot:
        raise ValueError("revision has no rollback snapshot")

    patch_payload = {}
    for field in ("daily_target", "status"):
        if field in target_snapshot:
            patch_payload[field] = target_snapshot[field]
    if not patch_payload:
        raise ValueError("rollback fields are empty")

    return update_current_plan(
        user,
        patch_payload,
        source="rollback",
        summary=f"rollback to revision #{revision.id}",
        metadata={"rollback_target_revision_id": revision.id},
        rollback_from=revision,
    )
