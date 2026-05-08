from django.db import models

from common.core.models import TimeStampedModel


class CheckinRecord(TimeStampedModel):
    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="checkins")
    checkin_date = models.DateField(verbose_name="打卡日期")
    finished_new_count = models.PositiveIntegerField(default=0, verbose_name="完成新词数")
    finished_review_count = models.PositiveIntegerField(default=0, verbose_name="完成复习数")
    total_minutes = models.PositiveIntegerField(default=0, verbose_name="学习分钟数")
    status = models.CharField(max_length=16, default="success", verbose_name="状态")

    class Meta:
        db_table = "checkin_records"
        ordering = ["-checkin_date", "-id"]
        unique_together = ("user", "checkin_date")
        verbose_name = "打卡记录"
        verbose_name_plural = verbose_name


class StudyDailyStat(TimeStampedModel):
    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="daily_stats")
    stat_date = models.DateField(verbose_name="统计日期")
    learned_count = models.PositiveIntegerField(default=0, verbose_name="学习数量")
    review_count = models.PositiveIntegerField(default=0, verbose_name="复习数量")
    test_count = models.PositiveIntegerField(default=0, verbose_name="测试数量")
    correct_count = models.PositiveIntegerField(default=0, verbose_name="正确数量")
    total_minutes = models.PositiveIntegerField(default=0, verbose_name="学习分钟数")

    class Meta:
        db_table = "study_daily_stats"
        ordering = ["-stat_date", "-id"]
        unique_together = ("user", "stat_date")
        verbose_name = "学习日统计"
        verbose_name_plural = verbose_name

# Create your models here.
