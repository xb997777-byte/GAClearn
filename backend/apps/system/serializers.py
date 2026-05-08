from rest_framework import serializers


class SpeechSynthesizeSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=400, allow_blank=False, trim_whitespace=True)
    lang = serializers.CharField(max_length=32, required=False, allow_blank=True, default="en-US")
    speed = serializers.FloatField(required=False, min_value=0.5, max_value=1.2, default=1.0)
