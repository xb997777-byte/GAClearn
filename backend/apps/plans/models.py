from django.db import models

from common.core.models import TimeStampedModel


class UserPlan(TimeStampedModel):
    STATUS_CHOICES = (
        ("active", "进行中"),
        ("paused", "暂停"),
        ("completed", "完成"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="plans")
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, related_name="plans")
    daily_target = models.PositiveIntegerField(default=20, verbose_name="每日目标")
    start_date = models.DateField(verbose_name="开始日期")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active", verbose_name="状态")
    finished_word_count = models.PositiveIntegerField(default=0, verbose_name="已完成单词数")

    class Meta:
        db_table = "user_plans"
        ordering = ["-id"]
        verbose_name = "学习计划"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user} - {self.book}"


class DailyTask(TimeStampedModel):
    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="daily_tasks")
    plan = models.ForeignKey("plans.UserPlan", on_delete=models.CASCADE, related_name="daily_tasks")
    task_date = models.DateField(verbose_name="任务日期")
    new_word_target = models.PositiveIntegerField(default=20, verbose_name="新词目标")
    review_word_target = models.PositiveIntegerField(default=10, verbose_name="复习目标")
    learned_count = models.PositiveIntegerField(default=0, verbose_name="已学数量")
    reviewed_count = models.PositiveIntegerField(default=0, verbose_name="已复习数量")
    test_count = models.PositiveIntegerField(default=0, verbose_name="已测试数量")
    is_started = models.BooleanField(default=False, verbose_name="是否开始")
    is_finished = models.BooleanField(default=False, verbose_name="是否完成")

    class Meta:
        db_table = "daily_tasks"
        ordering = ["-task_date", "-id"]
        unique_together = ("user", "task_date")
        verbose_name = "每日任务"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user} - {self.task_date}"


class PlanRevision(TimeStampedModel):
    SOURCE_CHOICES = (
        ("create", "Create"),
        ("manual", "Manual"),
        ("ai_agent", "AI Agent"),
        ("rollback", "Rollback"),
        ("switch_book", "Switch Book"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="plan_revisions")
    plan = models.ForeignKey("plans.UserPlan", on_delete=models.CASCADE, related_name="revisions")
    source = models.CharField(max_length=24, choices=SOURCE_CHOICES, default="manual", verbose_name="Source")
    summary = models.CharField(max_length=255, blank=True, default="", verbose_name="Summary")
    patch_payload = models.JSONField(default=dict, blank=True, verbose_name="Patch Payload")
    before_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Before Snapshot")
    after_snapshot = models.JSONField(default=dict, blank=True, verbose_name="After Snapshot")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")
    rollback_from = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rollback_children",
        verbose_name="Rollback From",
    )

    class Meta:
        db_table = "plan_revisions"
        ordering = ["-id"]
        verbose_name = "Plan Revision"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user_id}-{self.plan_id}-{self.source}-{self.id}"
