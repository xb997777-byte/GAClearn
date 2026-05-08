from rest_framework import serializers

from .models import UserFeedback, UserSetting, WxUser


class WxLoginSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=128)
    nickname = serializers.CharField(max_length=64, required=False, allow_blank=True)
    avatar_url = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(max_length=16, required=False, allow_blank=True)


class ProfileUpdateSerializer(serializers.Serializer):
    nickname = serializers.CharField(max_length=64, required=False, allow_blank=True)
    avatar_url = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(max_length=16, required=False, allow_blank=True)


class WxUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = WxUser
        fields = ("id", "openid", "unionid", "nickname", "avatar_url", "gender", "status", "last_login_at")


class UserSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSetting
        fields = (
            "daily_target",
            "reminder_time",
            "auto_play_audio",
            "speech_speed",
            "review_enabled",
            "theme_id",
            "custom_theme",
            "cefr_level",
            "placement_score",
            "placement_completed_at",
            "reminder_subscription_status",
            "reminder_template_ids",
            "last_reminder_sent_at",
            "personalized_rag_enabled",
            "personalized_rag_status",
            "personalized_rag_chunk_count",
            "personalized_rag_updated_at",
            "personalized_rag_last_error",
        )
        read_only_fields = (
            "cefr_level",
            "placement_score",
            "placement_completed_at",
            "last_reminder_sent_at",
            "personalized_rag_status",
            "personalized_rag_chunk_count",
            "personalized_rag_updated_at",
            "personalized_rag_last_error",
        )

    def validate_speech_speed(self, value):
        if value < 0.5 or value > 1.2:
            raise serializers.ValidationError("speech_speed must be between 0.5 and 1.2")
        return value


class UserFeedbackSubmitSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=[item[0] for item in UserFeedback.CATEGORY_CHOICES],
        required=False,
        default="experience",
    )
    content = serializers.CharField(max_length=2000, allow_blank=False, trim_whitespace=True)
    contact = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    page = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    app_version = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    system_info = serializers.JSONField(required=False, default=dict)
