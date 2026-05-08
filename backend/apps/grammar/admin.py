from django.contrib import admin

from .models import GrammarAnnotation, GrammarLearningRecord, GrammarPoint, GrammarSentence


@admin.register(GrammarPoint)
class GrammarPointAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "difficulty", "sort_order", "status")
    list_filter = ("category", "difficulty", "status")
    search_fields = ("title", "code", "description")
    ordering = ("sort_order", "id")


@admin.register(GrammarSentence)
class GrammarSentenceAdmin(admin.ModelAdmin):
    list_display = ("id", "sentence", "point", "difficulty", "scene_tag", "is_long_sentence", "status")
    list_filter = ("point", "difficulty", "scene_tag", "is_long_sentence", "status")
    search_fields = ("sentence", "translation_cn", "summary")
    autocomplete_fields = ("point",)
    ordering = ("point_id", "order_in_point", "id")


@admin.register(GrammarAnnotation)
class GrammarAnnotationAdmin(admin.ModelAdmin):
    list_display = ("id", "sentence", "text_span", "role_type", "grammar_label", "color_token", "is_core")
    list_filter = ("role_type", "color_token", "is_core")
    search_fields = ("text_span", "grammar_label", "explanation")
    autocomplete_fields = ("sentence", "parent")
    ordering = ("sentence_id", "sort_order", "id")


@admin.register(GrammarLearningRecord)
class GrammarLearningRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "point", "sentence", "action_type", "result", "mastery_level", "occurred_at")
    list_filter = ("action_type", "result", "point")
    search_fields = ("user__nickname", "sentence__sentence", "point__title")
    autocomplete_fields = ("user", "point", "sentence")
    ordering = ("-occurred_at", "-id")

