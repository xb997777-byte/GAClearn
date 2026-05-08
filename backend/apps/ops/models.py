from django.db import models

from common.core.models import TimeStampedModel


class OperationLog(TimeStampedModel):
    module = models.CharField(max_length=64, verbose_name="模块")
    action = models.CharField(max_length=64, verbose_name="动作")
    operator = models.CharField(max_length=64, blank=True, default="", verbose_name="操作人")
    remark = models.CharField(max_length=255, blank=True, default="", verbose_name="备注")

    class Meta:
        db_table = "operation_logs"
        ordering = ["-id"]
        verbose_name = "操作日志"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.module} - {self.action}"


class DataImportTask(TimeStampedModel):
    task_name = models.CharField(max_length=128, verbose_name="任务名称")
    file_name = models.CharField(max_length=255, blank=True, default="", verbose_name="文件名")
    status = models.CharField(max_length=16, default="pending", verbose_name="状态")
    success_count = models.PositiveIntegerField(default=0, verbose_name="成功数量")
    fail_count = models.PositiveIntegerField(default=0, verbose_name="失败数量")
    executed_at = models.DateTimeField(null=True, blank=True, verbose_name="执行时间")

    class Meta:
        db_table = "data_import_tasks"
        ordering = ["-id"]
        verbose_name = "数据导入任务"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.task_name

# Create your models here.
