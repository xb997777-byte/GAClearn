from rest_framework import serializers

from .models import DailyTask, UserPlan


class PlanCreateSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()
    daily_target = serializers.IntegerField(min_value=1, max_value=200)


class PlanUpdateSerializer(serializers.Serializer):
    daily_target = serializers.IntegerField(min_value=1, max_value=200, required=False)
    status = serializers.ChoiceField(choices=["active", "paused", "completed"], required=False)


class PlanApplyAIPatchSerializer(serializers.Serializer):
    summary = serializers.CharField(required=False, allow_blank=True, default="", max_length=255)
    patch = serializers.JSONField()
    evidence = serializers.JSONField(required=False, default=dict)


class PlanRollbackSerializer(serializers.Serializer):
    revision_id = serializers.IntegerField(min_value=1)


class SwitchBookSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()
    daily_target = serializers.IntegerField(min_value=1, max_value=200, required=False)
    keep_progress = serializers.BooleanField(required=False, default=False)


class UserPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPlan
        fields = ("id", "user", "book", "daily_target", "start_date", "status", "finished_word_count")


class DailyTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyTask
        fields = (
            "id",
            "task_date",
            "new_word_target",
            "review_word_target",
            "learned_count",
            "reviewed_count",
            "test_count",
            "is_started",
            "is_finished",
        )
