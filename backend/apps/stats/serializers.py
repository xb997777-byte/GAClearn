from rest_framework import serializers


class TrendQuerySerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=90, default=7)
