from django.db import models
from django.utils import timezone

from common.core.models import TimeStampedModel


class GrammarPoint(TimeStampedModel):
    code = models.CharField(max_length=64, unique=True, verbose_name="编码")
    title = models.CharField(max_length=128, verbose_name="语法点名称")
    category = models.CharField(max_length=64, blank=True, default="", verbose_name="分类")
    difficulty = models.PositiveSmallIntegerField(default=1, verbose_name="难度")
    description = models.TextField(blank=True, default="", verbose_name="说明")
    learning_tip = models.TextField(blank=True, default="", verbose_name="学习提示")
    practice_prompt = models.TextField(blank=True, default="", verbose_name="默认练习题干")
    practice_options = models.JSONField(default=list, blank=True, verbose_name="默认练习选项")
    practice_answer = models.CharField(max_length=255, blank=True, default="", verbose_name="默认练习答案")
    practice_explanation = models.TextField(blank=True, default="", verbose_name="默认练习解析")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")
    status = models.CharField(max_length=16, default="active", verbose_name="状态")

    class Meta:
        db_table = "grammar_points"
        ordering = ["sort_order", "id"]
        verbose_name = "语法点"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title


class GrammarSentence(TimeStampedModel):
    point = models.ForeignKey("grammar.GrammarPoint", on_delete=models.CASCADE, related_name="sentences")
    sentence = models.CharField(max_length=512, verbose_name="英文句子")
    translation_cn = models.TextField(verbose_name="中文翻译")
    summary = models.CharField(max_length=255, blank=True, default="", verbose_name="核心说明")
    analysis = models.TextField(blank=True, default="", verbose_name="句子解析")
    main_structure = models.CharField(max_length=255, blank=True, default="", verbose_name="主干结构")
    difficulty = models.PositiveSmallIntegerField(default=1, verbose_name="难度")
    scene_tag = models.CharField(max_length=64, blank=True, default="", verbose_name="场景标签")
    grammar_tags = models.JSONField(default=list, blank=True, verbose_name="语法标签")
    chunk_breakdown = models.JSONField(default=list, blank=True, verbose_name="分块拆解")
    audio_url = models.URLField(blank=True, default="", verbose_name="音频地址")
    is_long_sentence = models.BooleanField(default=False, verbose_name="是否长难句")
    practice_type = models.CharField(max_length=32, default="choice", verbose_name="练习类型")
    practice_prompt = models.TextField(blank=True, default="", verbose_name="练习题干")
    practice_options = models.JSONField(default=list, blank=True, verbose_name="练习选项")
    practice_answer = models.CharField(max_length=255, blank=True, default="", verbose_name="练习答案")
    practice_explanation = models.TextField(blank=True, default="", verbose_name="练习解析")
    order_in_point = models.PositiveIntegerField(default=0, verbose_name="语法点内排序")
    status = models.CharField(max_length=16, default="active", verbose_name="状态")

    class Meta:
        db_table = "grammar_sentences"
        ordering = ["point_id", "order_in_point", "id"]
        verbose_name = "语法句子"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.sentence


class GrammarAnnotation(TimeStampedModel):
    sentence = models.ForeignKey("grammar.GrammarSentence", on_delete=models.CASCADE, related_name="annotations")
    text_span = models.CharField(max_length=255, verbose_name="标注文本")
    start_index = models.PositiveIntegerField(verbose_name="起始位置")
    end_index = models.PositiveIntegerField(verbose_name="结束位置")
    role_type = models.CharField(max_length=32, verbose_name="语法角色")
    explanation = models.TextField(blank=True, default="", verbose_name="解释")
    grammar_label = models.CharField(max_length=128, blank=True, default="", verbose_name="标签")
    color_token = models.CharField(max_length=32, blank=True, default="", verbose_name="颜色标识")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="父级标注",
    )
    is_core = models.BooleanField(default=False, verbose_name="是否核心成分")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="排序")

    class Meta:
        db_table = "grammar_annotations"
        ordering = ["sort_order", "start_index", "id"]
        verbose_name = "句子标注"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.sentence_id}: {self.text_span}"


class GrammarLearningRecord(TimeStampedModel):
    ACTION_CHOICES = (
        ("view", "查看"),
        ("understood", "已理解"),
        ("unclear", "未理解"),
        ("practice", "完成练习"),
        ("bookmark", "收藏"),
    )

    RESULT_CHOICES = (
        ("", "无"),
        ("correct", "正确"),
        ("wrong", "错误"),
        ("neutral", "中性"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="grammar_learning_records")
    sentence = models.ForeignKey("grammar.GrammarSentence", on_delete=models.CASCADE, related_name="learning_records")
    point = models.ForeignKey("grammar.GrammarPoint", on_delete=models.CASCADE, related_name="learning_records")
    action_type = models.CharField(max_length=16, choices=ACTION_CHOICES, default="view", verbose_name="动作类型")
    practice_type = models.CharField(max_length=32, blank=True, default="", verbose_name="练习类型")
    result = models.CharField(max_length=16, choices=RESULT_CHOICES, blank=True, default="", verbose_name="结果")
    duration = models.PositiveIntegerField(default=0, verbose_name="耗时秒数")
    mastery_level = models.PositiveSmallIntegerField(default=0, verbose_name="掌握度")
    extra_payload = models.JSONField(default=dict, blank=True, verbose_name="扩展数据")
    occurred_at = models.DateTimeField(default=timezone.now, verbose_name="发生时间")

    class Meta:
        db_table = "grammar_learning_records"
        ordering = ["-occurred_at", "-id"]
        verbose_name = "语法学习记录"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user_id}-{self.sentence_id}-{self.action_type}"

