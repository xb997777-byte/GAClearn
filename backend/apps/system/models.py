from django.db import models

from common.core.models import TimeStampedModel


class SystemConfig(TimeStampedModel):
    key = models.CharField(max_length=64, unique=True, verbose_name="配置键")
    name = models.CharField(max_length=64, verbose_name="配置名称")
    value = models.TextField(blank=True, default="", verbose_name="配置值")
    description = models.CharField(max_length=255, blank=True, default="", verbose_name="描述")
    is_public = models.BooleanField(default=False, verbose_name="是否公开")

    class Meta:
        db_table = "system_configs"
        ordering = ["id"]
        verbose_name = "系统配置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class BannerNotice(TimeStampedModel):
    title = models.CharField(max_length=128, verbose_name="标题")
    content = models.TextField(blank=True, default="", verbose_name="内容")
    status = models.CharField(max_length=16, default="active", verbose_name="状态")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "banner_notices"
        ordering = ["sort_order", "-id"]
        verbose_name = "公告横幅"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title

# Create your models here.
