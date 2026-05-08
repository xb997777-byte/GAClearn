from django.contrib import admin

from .models import (
    AIConversation,
    AIEvaluationCase,
    AIEvaluationRun,
    AIMessage,
    AIRequestLog,
    AIResponseCache,
    AIStudyReport,
    AIUserFeedback,
    AIUserProfileMemory,
)


class AIMessageInline(admin.TabularInline):
    model = AIMessage
    extra = 0
    fields = ("role", "content", "prompt_version", "model_name", "latency_ms", "created_at")
    readonly_fields = ("created_at",)


@admin.register(AIConversation)
class AIConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "feature_type", "title", "status", "created_at")
    list_filter = ("feature_type", "status", "created_at")
    search_fields = ("user__nickname", "user__openid", "title")
    inlines = (AIMessageInline,)


@admin.register(AIMessage)
class AIMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "content_preview", "prompt_version", "model_name", "created_at")
    list_filter = ("role", "prompt_version", "created_at")
    search_fields = ("content", "conversation__title", "conversation__user__nickname", "conversation__user__openid")

    @admin.display(description="内容摘要")
    def content_preview(self, obj):
        return obj.content[:60]


@admin.register(AIUserFeedback)
class AIUserFeedbackAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "feature_type", "rating", "content_preview", "created_at")
    list_filter = ("feature_type", "rating", "created_at")
    search_fields = ("user__nickname", "user__openid", "content")

    @admin.display(description="反馈摘要")
    def content_preview(self, obj):
        return obj.content[:60]


@admin.register(AIStudyReport)
class AIStudyReportAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "report_type", "period_start", "period_end", "title", "created_at")
    list_filter = ("report_type", "period_end", "created_at")
    search_fields = ("user__nickname", "user__openid", "title")


@admin.register(AIRequestLog)
class AIRequestLogAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "feature_type", "status", "cache_hit", "latency_ms", "endpoint", "created_at")
    list_filter = ("feature_type", "status", "cache_hit", "created_at")
    search_fields = ("user__nickname", "user__openid", "endpoint", "cache_key", "error_message")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AIResponseCache)
class AIResponseCacheAdmin(admin.ModelAdmin):
    list_display = ("id", "feature_type", "cache_key_preview", "hit_count", "expires_at", "updated_at")
    list_filter = ("feature_type", "expires_at", "updated_at")
    search_fields = ("feature_type", "cache_key", "request_hash")
    readonly_fields = ("created_at", "updated_at", "last_hit_at")

    @admin.display(description="缓存键")
    def cache_key_preview(self, obj):
        return obj.cache_key[:24]


@admin.register(AIUserProfileMemory)
class AIUserProfileMemoryAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "memory_version", "updated_from", "updated_at")
    search_fields = ("user__nickname", "user__openid", "profile_summary")
    readonly_fields = ("created_at", "updated_at")


@admin.register(AIEvaluationCase)
class AIEvaluationCaseAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "case_type", "enabled", "created_at")
    list_filter = ("case_type", "enabled", "created_at")
    search_fields = ("name", "description")


@admin.register(AIEvaluationRun)
class AIEvaluationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "case", "feature_type", "status", "score", "created_at")
    list_filter = ("feature_type", "status", "created_at")
    search_fields = ("case__name", "feature_type", "failure_reason")
    readonly_fields = ("created_at", "updated_at")
