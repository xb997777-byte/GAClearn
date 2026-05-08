from rest_framework import serializers


class AIGrammarTutorSerializer(serializers.Serializer):
    sentence = serializers.CharField(min_length=2, max_length=512)
    question = serializers.CharField(required=False, allow_blank=True, default="", max_length=512)


class AIWordExplainSerializer(serializers.Serializer):
    word_id = serializers.IntegerField(min_value=1)


class AIStudyCoachSerializer(serializers.Serializer):
    trend_days = serializers.IntegerField(required=False, min_value=3, max_value=14, default=7)


class AIPlanReplanSerializer(serializers.Serializer):
    trend_days = serializers.IntegerField(required=False, min_value=3, max_value=14, default=7)


class AIRetrievalOrchestratorSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1, max_length=512)
    limit = serializers.IntegerField(required=False, min_value=3, max_value=8, default=6)


class AIProfileRefreshSerializer(serializers.Serializer):
    source = serializers.CharField(required=False, allow_blank=True, default="manual", max_length=32)


class AIEvaluationRunSerializer(serializers.Serializer):
    case_id = serializers.IntegerField(required=False, min_value=1)
    case_type = serializers.ChoiceField(
        choices=[
            "",
            "rag_recall",
            "vector_rag",
            "plan_replan",
            "retrieval_orchestrator",
            "study_coach",
            "word_tutor",
            "wrong_words_review",
            "grammar_tutor",
            "conversation",
        ],
        required=False,
        default="",
    )
    replay_failed_only = serializers.BooleanField(required=False, default=False)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=20, default=5)


class AIEvaluationReplaySerializer(serializers.Serializer):
    request_payload = serializers.JSONField(required=False, default=dict)


class AIWrongWordsReviewSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=3, max_value=24, default=12)


class AIMCPToolCallSerializer(serializers.Serializer):
    tool_name = serializers.CharField(max_length=64)
    args = serializers.JSONField(required=False, default=dict)


class AIMCPResourceReadSerializer(serializers.Serializer):
    resource_uri = serializers.CharField(max_length=255)


class AIWritingCorrectSerializer(serializers.Serializer):
    text = serializers.CharField(min_length=2, max_length=3000)
    level = serializers.CharField(required=False, allow_blank=True, default="cet4", max_length=32)


class AIWritingPromptSerializer(serializers.Serializer):
    level = serializers.CharField(required=False, allow_blank=True, default="cet4", max_length=32)
    topic = serializers.CharField(required=False, allow_blank=True, default="", max_length=255)
    genre = serializers.CharField(required=False, allow_blank=True, default="essay", max_length=32)


class AITranslationEvaluateSerializer(serializers.Serializer):
    source_text = serializers.CharField(min_length=1, max_length=1200)
    user_translation = serializers.CharField(required=False, allow_blank=True, default="", max_length=1200)
    direction = serializers.ChoiceField(choices=["auto", "zh_to_en", "en_to_zh"], required=False, default="auto")


class AIReportGenerateSerializer(serializers.Serializer):
    report_type = serializers.ChoiceField(choices=["weekly", "monthly"], required=False, default="weekly")


class AIRAGSearchSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1, max_length=512)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=12, default=6)


class AIVectorRAGSearchSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1, max_length=512)
    limit = serializers.IntegerField(required=False, min_value=1, max_value=12, default=8)
    retrieval_mode = serializers.ChoiceField(
        choices=["auto", "vector_only", "structured_only", "hybrid"],
        required=False,
        default="auto",
    )


class AIRAGIndexSyncSerializer(serializers.Serializer):
    limit = serializers.IntegerField(required=False, min_value=1, max_value=5000)
    batch_size = serializers.IntegerField(required=False, min_value=1, max_value=128, default=64)
    delete_missing = serializers.BooleanField(required=False, default=False)


class AIRAGRecallEvaluateSerializer(serializers.Serializer):
    query = serializers.CharField(min_length=1, max_length=512)
    expected_keywords = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        allow_empty=True,
        default=list,
    )
    preferred_source_type = serializers.ChoiceField(
        choices=["", "word", "grammar_point", "grammar_sentence"],
        required=False,
        default="",
    )
    limit = serializers.IntegerField(required=False, min_value=1, max_value=12, default=6)


class AIScenarioDialogueSerializer(serializers.Serializer):
    scenario = serializers.ChoiceField(
        choices=["restaurant", "classroom", "interview", "travel", "shopping", "daily", "hotel", "airport"],
        required=False,
        default="daily",
    )
    user_message = serializers.CharField(min_length=1, max_length=1000)
    conversation_id = serializers.IntegerField(required=False, min_value=1)


class AIConversationCreateSerializer(serializers.Serializer):
    feature_type = serializers.CharField(required=False, allow_blank=True, default="rag", max_length=32)
    title = serializers.CharField(required=False, allow_blank=True, default="", max_length=128)
    context = serializers.JSONField(required=False, default=dict)


class AIConversationAskSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=False, min_value=1)
    feature_type = serializers.CharField(required=False, allow_blank=True, default="rag", max_length=32)
    question = serializers.CharField(min_length=1, max_length=1000)


class AIFeedbackSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=False, min_value=1)
    message_id = serializers.IntegerField(required=False, min_value=1)
    feature_type = serializers.CharField(required=False, allow_blank=True, default="", max_length=32)
    rating = serializers.ChoiceField(choices=["helpful", "neutral", "unhelpful", "wrong"], default="helpful")
    content = serializers.CharField(required=False, allow_blank=True, default="", max_length=1000)
    payload = serializers.JSONField(required=False, default=dict)
