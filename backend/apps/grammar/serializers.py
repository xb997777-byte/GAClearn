from rest_framework import serializers

from .models import GrammarLearningRecord


class GrammarSentenceQuerySerializer(serializers.Serializer):
    point_id = serializers.IntegerField(required=False)
    difficulty = serializers.IntegerField(min_value=1, max_value=3, required=False)
    keyword = serializers.CharField(required=False, allow_blank=True, default="")
    scene_tag = serializers.CharField(required=False, allow_blank=True, default="")
    is_long_sentence = serializers.BooleanField(required=False)
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


class GrammarRecommendQuerySerializer(serializers.Serializer):
    point_id = serializers.IntegerField(required=False)
    current_sentence_id = serializers.IntegerField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=12, default=6)


class GrammarAnalyzeSerializer(serializers.Serializer):
    sentence = serializers.CharField(min_length=2, max_length=512)


class GrammarAskSerializer(serializers.Serializer):
    sentence = serializers.CharField(required=False, allow_blank=True, default="")
    question = serializers.CharField(min_length=2, max_length=512)


class GrammarRecordSerializer(serializers.Serializer):
    sentence_id = serializers.IntegerField()
    action_type = serializers.ChoiceField(choices=[item[0] for item in GrammarLearningRecord.ACTION_CHOICES])
    practice_type = serializers.CharField(required=False, allow_blank=True, default="")
    result = serializers.ChoiceField(
        choices=[item[0] for item in GrammarLearningRecord.RESULT_CHOICES],
        required=False,
        allow_blank=True,
        default="",
    )
    duration = serializers.IntegerField(min_value=0, required=False, default=0)
    mastery_level = serializers.IntegerField(min_value=0, max_value=5, required=False)
    extra_payload = serializers.JSONField(required=False, default=dict)
    occurred_at = serializers.DateTimeField(required=False)
