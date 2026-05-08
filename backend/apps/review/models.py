from django.db import models

from common.core.models import TimeStampedModel


class ReviewSession(TimeStampedModel):
    STATUS_CHOICES = (
        ("pending", "进行中"),
        ("completed", "已完成"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="review_sessions")
    plan = models.ForeignKey("plans.UserPlan", null=True, blank=True, on_delete=models.SET_NULL, related_name="review_sessions")
    session_type = models.CharField(max_length=32, default="daily", verbose_name="会话类型")
    total_count = models.PositiveIntegerField(default=0, verbose_name="总题数")
    finished_count = models.PositiveIntegerField(default=0, verbose_name="完成题数")
    correct_count = models.PositiveIntegerField(default=0, verbose_name="答对题数")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", verbose_name="状态")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")

    class Meta:
        db_table = "review_sessions"
        ordering = ["-id"]
        verbose_name = "复习会话"
        verbose_name_plural = verbose_name


class ReviewRecord(TimeStampedModel):
    session = models.ForeignKey("review.ReviewSession", on_delete=models.CASCADE, related_name="records")
    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="review_records")
    word = models.ForeignKey("books.Word", on_delete=models.CASCADE, related_name="review_records")
    question_type = models.CharField(max_length=32, default="meaning_to_word", verbose_name="题型")
    user_answer = models.CharField(max_length=255, blank=True, default="", verbose_name="用户答案")
    correct_answer = models.CharField(max_length=255, blank=True, default="", verbose_name="正确答案")
    is_correct = models.BooleanField(default=False, verbose_name="是否正确")
    answer_feedback = models.JSONField(default=dict, blank=True, verbose_name="答题反馈")
    reviewed_at = models.DateTimeField(verbose_name="复习时间")

    class Meta:
        db_table = "review_records"
        ordering = ["-reviewed_at", "-id"]
        verbose_name = "复习记录"
        verbose_name_plural = verbose_name


class WrongWord(TimeStampedModel):
    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="wrong_words")
    word = models.ForeignKey("books.Word", on_delete=models.CASCADE, related_name="wrong_word_users")
    wrong_count = models.PositiveIntegerField(default=1, verbose_name="错误次数")
    source = models.CharField(max_length=16, default="review", verbose_name="来源")
    last_wrong_at = models.DateTimeField(verbose_name="最近错误时间")
    is_active = models.BooleanField(default=True, verbose_name="是否仍在错词本")

    class Meta:
        db_table = "wrong_words"
        ordering = ["-last_wrong_at", "-id"]
        unique_together = ("user", "word")
        verbose_name = "错词本"
        verbose_name_plural = verbose_name

# Create your models here.
