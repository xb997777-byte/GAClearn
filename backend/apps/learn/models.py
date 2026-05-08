from django.db import models

from common.core.models import TimeStampedModel


class LearningRecord(TimeStampedModel):
    SOURCE_CHOICES = (
        ("learn", "学习"),
        ("review", "复习"),
        ("test", "测试"),
    )
    ACTION_CHOICES = (
        ("view", "查看"),
        ("known", "认识"),
        ("unknown", "不认识"),
        ("mastered", "已掌握"),
        ("favorite", "收藏"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="learning_records")
    word = models.ForeignKey("books.Word", on_delete=models.CASCADE, related_name="learning_records")
    plan = models.ForeignKey("plans.UserPlan", null=True, blank=True, on_delete=models.SET_NULL, related_name="learning_records")
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default="learn", verbose_name="来源")
    action_type = models.CharField(max_length=16, choices=ACTION_CHOICES, default="view", verbose_name="动作")
    result = models.CharField(max_length=16, blank=True, default="", verbose_name="结果")
    duration = models.PositiveIntegerField(default=0, verbose_name="耗时秒数")
    extra_payload = models.JSONField(default=dict, blank=True, verbose_name="扩展数据")
    occurred_at = models.DateTimeField(verbose_name="发生时间")

    class Meta:
        db_table = "learning_records"
        ordering = ["-occurred_at", "-id"]
        verbose_name = "学习记录"
        verbose_name_plural = verbose_name


class WordProgress(TimeStampedModel):
    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="word_progresses")
    book = models.ForeignKey("books.Book", on_delete=models.CASCADE, related_name="word_progresses")
    word = models.ForeignKey("books.Word", on_delete=models.CASCADE, related_name="progresses")
    mastery_level = models.PositiveSmallIntegerField(default=0, verbose_name="掌握度")
    learn_count = models.PositiveIntegerField(default=0, verbose_name="学习次数")
    review_count = models.PositiveIntegerField(default=0, verbose_name="复习次数")
    correct_count = models.PositiveIntegerField(default=0, verbose_name="答对次数")
    wrong_count = models.PositiveIntegerField(default=0, verbose_name="答错次数")
    last_learned_at = models.DateTimeField(null=True, blank=True, verbose_name="最近学习时间")
    last_reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="最近复习时间")
    last_tested_at = models.DateTimeField(null=True, blank=True, verbose_name="最近测试时间")
    review_due_at = models.DateTimeField(null=True, blank=True, verbose_name="下次复习时间")
    is_favorite = models.BooleanField(default=False, verbose_name="是否收藏")
    is_mastered = models.BooleanField(default=False, verbose_name="是否掌握")
    ease_factor = models.FloatField(default=2.3, verbose_name="记忆容易度")
    interval_days = models.PositiveIntegerField(default=0, verbose_name="当前间隔天数")
    correct_streak = models.PositiveIntegerField(default=0, verbose_name="连续正确次数")
    last_score = models.PositiveSmallIntegerField(default=0, verbose_name="最近一次评分")

    class Meta:
        db_table = "word_progress"
        ordering = ["review_due_at", "-id"]
        unique_together = ("user", "word")
        verbose_name = "单词掌握进度"
        verbose_name_plural = verbose_name


class Favorite(TimeStampedModel):
    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="favorites")
    word = models.ForeignKey("books.Word", on_delete=models.CASCADE, related_name="favorite_users")
    note = models.CharField(max_length=255, blank=True, default="", verbose_name="备注")

    class Meta:
        db_table = "favorites"
        ordering = ["-id"]
        unique_together = ("user", "word")
        verbose_name = "收藏词"
        verbose_name_plural = verbose_name
