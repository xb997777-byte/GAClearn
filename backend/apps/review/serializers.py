from rest_framework import serializers


class ReviewAnswerSerializer(serializers.Serializer):
    word_id = serializers.IntegerField()
    user_answer = serializers.CharField(required=False, allow_blank=True, default="")
    question_type = serializers.CharField(required=False, allow_blank=True, default="meaning_to_word")


class ReviewSubmitSerializer(serializers.Serializer):
    session_id = serializers.IntegerField()
    answers = ReviewAnswerSerializer(many=True)
