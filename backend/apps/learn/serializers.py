from rest_framework import serializers


class LearningRecordSerializer(serializers.Serializer):
    word_id = serializers.IntegerField()
    source = serializers.ChoiceField(choices=["learn", "review", "test"], default="learn")
    action_type = serializers.ChoiceField(
        choices=["view", "known", "unknown", "mastered", "favorite"],
        default="view",
    )
    result = serializers.CharField(required=False, allow_blank=True, default="")
    duration = serializers.IntegerField(required=False, min_value=0, default=0)
    extra_payload = serializers.JSONField(required=False, default=dict)
    occurred_at = serializers.DateTimeField(required=False)


class LearningRecordBatchSerializer(serializers.Serializer):
    records = LearningRecordSerializer(many=True)


class FavoriteSerializer(serializers.Serializer):
    word_id = serializers.IntegerField()
    note = serializers.CharField(required=False, allow_blank=True, default="")
