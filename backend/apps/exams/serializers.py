from rest_framework import serializers


class TestGenerateSerializer(serializers.Serializer):
    question_count = serializers.IntegerField(min_value=1, max_value=100, default=10)
    book_id = serializers.IntegerField(required=False)


class PlacementGenerateSerializer(serializers.Serializer):
    question_count = serializers.IntegerField(min_value=6, max_value=60, default=18)


class TestAnswerSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option = serializers.CharField(max_length=1, required=False, allow_blank=True, default="")
    submitted_text = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    answer = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")


class TestSubmitSerializer(serializers.Serializer):
    test_id = serializers.IntegerField()
    answers = TestAnswerSerializer(many=True)
