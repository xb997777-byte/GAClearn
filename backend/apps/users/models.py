import datetime

from django.db import models
from django.utils import timezone

from common.core.models import TimeStampedModel
from common.utils.tokens import generate_token


class WxUser(TimeStampedModel):
    openid = models.CharField(max_length=64, unique=True, verbose_name="OpenID")
    unionid = models.CharField(max_length=64, blank=True, default="", verbose_name="UnionID")
    nickname = models.CharField(max_length=64, blank=True, default="", verbose_name="昵称")
    avatar_url = models.URLField(blank=True, default="", verbose_name="头像")
    gender = models.CharField(max_length=16, blank=True, default="", verbose_name="性别")
    status = models.CharField(max_length=16, default="active", verbose_name="状态")
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name="最近登录时间")

    class Meta:
        db_table = "users"
        ordering = ["-id"]
        verbose_name = "小程序用户"
        verbose_name_plural = verbose_name

    @property
    def is_authenticated(self):
        return True

    def __str__(self):
        return self.nickname or self.openid


class UserSetting(TimeStampedModel):
    PERSONALIZED_RAG_STATUS_CHOICES = (
        ("idle", "未创建"),
        ("building", "构建中"),
        ("ready", "可用"),
        ("failed", "失败"),
    )

    user = models.OneToOneField("users.WxUser", on_delete=models.CASCADE, related_name="settings")
    daily_target = models.PositiveIntegerField(default=20, verbose_name="每日目标")
    reminder_time = models.TimeField(default=datetime.time(20, 30), verbose_name="提醒时间")
    auto_play_audio = models.BooleanField(default=True, verbose_name="自动播放发音")
    speech_speed = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, verbose_name="发音语速")
    review_enabled = models.BooleanField(default=True, verbose_name="启用复习")
    theme_id = models.CharField(max_length=32, default="busuu_ocean", verbose_name="主题")
    custom_theme = models.JSONField(default=dict, blank=True, verbose_name="自定义主题")
    cefr_level = models.CharField(max_length=16, blank=True, default="", verbose_name="CEFR等级")
    placement_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="分级测试得分")
    placement_completed_at = models.DateTimeField(null=True, blank=True, verbose_name="分级测试完成时间")
    reminder_subscription_status = models.CharField(max_length=16, default="unknown", verbose_name="提醒订阅状态")
    reminder_template_ids = models.JSONField(default=list, blank=True, verbose_name="提醒模板ID")
    last_reminder_sent_at = models.DateTimeField(null=True, blank=True, verbose_name="上次提醒发送时间")
    personalized_rag_enabled = models.BooleanField(default=False, verbose_name="启用个性化RAG")
    personalized_rag_status = models.CharField(
        max_length=16,
        choices=PERSONALIZED_RAG_STATUS_CHOICES,
        default="idle",
        verbose_name="个性化RAG状态",
    )
    personalized_rag_chunk_count = models.PositiveIntegerField(default=0, verbose_name="个性化RAG知识块数")
    personalized_rag_updated_at = models.DateTimeField(null=True, blank=True, verbose_name="个性化RAG更新时间")
    personalized_rag_last_error = models.TextField(blank=True, default="", verbose_name="个性化RAG最近错误")

    class Meta:
        db_table = "user_settings"
        verbose_name = "用户设置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user} 的学习设置"


class UserFeedback(TimeStampedModel):
    CATEGORY_CHOICES = (
        ("experience", "使用体验"),
        ("bug", "问题反馈"),
        ("content", "内容纠错"),
        ("ai", "AI 功能"),
        ("other", "其他"),
    )
    STATUS_CHOICES = (
        ("pending", "待处理"),
        ("processing", "处理中"),
        ("resolved", "已处理"),
        ("ignored", "不处理"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="feedback_items")
    category = models.CharField(max_length=32, choices=CATEGORY_CHOICES, default="experience", verbose_name="反馈类型")
    content = models.TextField(verbose_name="反馈内容")
    contact = models.CharField(max_length=128, blank=True, default="", verbose_name="联系方式")
    page = models.CharField(max_length=128, blank=True, default="", verbose_name="来源页面")
    app_version = models.CharField(max_length=64, blank=True, default="", verbose_name="小程序版本")
    system_info = models.JSONField(default=dict, blank=True, verbose_name="设备信息")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", verbose_name="处理状态")
    admin_note = models.TextField(blank=True, default="", verbose_name="管理员备注")
    handled_at = models.DateTimeField(null=True, blank=True, verbose_name="处理时间")
    handled_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="handled_user_feedbacks",
        verbose_name="处理人",
    )

    class Meta:
        db_table = "user_feedback"
        ordering = ["-id"]
        verbose_name = "意见反馈"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user} - {self.get_category_display()} - {self.status}"


class LoginToken(TimeStampedModel):
    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="tokens")
    token = models.CharField(max_length=128, unique=True, verbose_name="令牌")
    expired_at = models.DateTimeField(verbose_name="过期时间")
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name="最后使用时间")
    is_active = models.BooleanField(default=True, verbose_name="是否有效")

    class Meta:
        db_table = "login_tokens"
        ordering = ["-id"]
        verbose_name = "登录令牌"
        verbose_name_plural = verbose_name

    @property
    def is_expired(self):
        return self.expired_at <= timezone.now() or not self.is_active

    def touch(self):
        self.last_used_at = timezone.now()
        self.save(update_fields=["last_used_at", "updated_at"])

    @classmethod
    def issue_for_user(cls, user, days=30):
        cls.objects.filter(user=user, is_active=True).update(is_active=False)
        return cls.objects.create(
            user=user,
            token=generate_token(),
            expired_at=timezone.now() + datetime.timedelta(days=days),
        )

    def __str__(self):
        return f"{self.user} - {self.token[:8]}"
