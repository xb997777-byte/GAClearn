from django.contrib import admin

from django.utils import timezone

from .models import LoginToken, UserFeedback, UserSetting, WxUser


@admin.register(WxUser)
class WxUserAdmin(admin.ModelAdmin):
    list_display = ("id", "nickname", "openid", "status", "last_login_at", "created_at")
    search_fields = ("nickname", "openid", "unionid")
    list_filter = ("status",)


@admin.register(UserSetting)
class UserSettingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "daily_target",
        "reminder_time",
        "auto_play_audio",
        "speech_speed",
        "review_enabled",
        "theme_id",
        "personalized_rag_enabled",
        "personalized_rag_status",
        "personalized_rag_chunk_count",
    )
    search_fields = ("user__nickname", "user__openid")


@admin.register(UserFeedback)
class UserFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "category", "status", "content_preview", "contact", "created_at", "handled_at")
    list_filter = ("category", "status", "created_at")
    search_fields = ("user__nickname", "user__openid", "content", "contact")
    readonly_fields = ("user", "category", "content", "contact", "page", "app_version", "system_info", "created_at", "updated_at")
    actions = ("mark_processing", "mark_resolved", "mark_ignored")

    @admin.display(description="反馈摘要")
    def content_preview(self, obj):
        return obj.content[:40]

    @admin.action(description="标记为处理中")
    def mark_processing(self, request, queryset):
        queryset.update(status="processing")

    @admin.action(description="标记为已处理")
    def mark_resolved(self, request, queryset):
        queryset.update(status="resolved", handled_at=timezone.now(), handled_by=request.user)

    @admin.action(description="标记为不处理")
    def mark_ignored(self, request, queryset):
        queryset.update(status="ignored", handled_at=timezone.now(), handled_by=request.user)


@admin.register(LoginToken)
class LoginTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "token", "expired_at", "is_active")
    search_fields = ("user__nickname", "token")
    list_filter = ("is_active",)
