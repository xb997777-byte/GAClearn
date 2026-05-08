from django.db import models

from common.core.models import TimeStampedModel


class TestSession(TimeStampedModel):
    STATUS_CHOICES = (
        ("draft", "未完成"),
        ("completed", "已完成"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="test_sessions")
    book = models.ForeignKey("books.Book", null=True, blank=True, on_delete=models.SET_NULL, related_name="test_sessions")
    title = models.CharField(max_length=128, default="词汇小测", verbose_name="测试标题")
    session_type = models.CharField(max_length=32, default="practice", verbose_name="测试类型")
    question_count = models.PositiveIntegerField(default=0, verbose_name="题目数")
    correct_count = models.PositiveIntegerField(default=0, verbose_name="答对数")
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="得分")
    cefr_result = models.CharField(max_length=16, blank=True, default="", verbose_name="CEFR结果")
    extra_payload = models.JSONField(default=dict, blank=True, verbose_name="扩展数据")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft", verbose_name="状态")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")

    class Meta:
        db_table = "test_sessions"
        ordering = ["-id"]
        verbose_name = "测试会话"
        verbose_name_plural = verbose_name


class TestQuestion(TimeStampedModel):
    test_session = models.ForeignKey("exams.TestSession", on_delete=models.CASCADE, related_name="questions")
    word = models.ForeignKey("books.Word", on_delete=models.CASCADE, related_name="test_questions")
    question_type = models.CharField(max_length=32, default="word_to_meaning", verbose_name="题型")
    answer_mode = models.CharField(max_length=16, default="choice", verbose_name="作答方式")
    stem = models.CharField(max_length=255, verbose_name="题干")
    option_a = models.CharField(max_length=255, blank=True, default="", verbose_name="选项A")
    option_b = models.CharField(max_length=255, blank=True, default="", verbose_name="选项B")
    option_c = models.CharField(max_length=255, blank=True, default="", verbose_name="选项C")
    option_d = models.CharField(max_length=255, blank=True, default="", verbose_name="选项D")
    correct_option = models.CharField(max_length=1, blank=True, default="", verbose_name="正确选项")
    answer_text = models.CharField(max_length=255, blank=True, default="", verbose_name="文本答案")
    difficulty_level = models.PositiveSmallIntegerField(default=1, verbose_name="难度等级")
    cefr_tag = models.CharField(max_length=16, blank=True, default="", verbose_name="CEFR标签")
    explanation = models.CharField(max_length=255, blank=True, default="", verbose_name="解析")

    class Meta:
        db_table = "test_questions"
        ordering = ["id"]
        verbose_name = "测试题目"
        verbose_name_plural = verbose_name


class TestAnswer(TimeStampedModel):
    test_session = models.ForeignKey("exams.TestSession", on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey("exams.TestQuestion", on_delete=models.CASCADE, related_name="answers")
    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="test_answers")
    selected_option = models.CharField(max_length=1, blank=True, default="", verbose_name="选择项")
    submitted_text = models.CharField(max_length=255, blank=True, default="", verbose_name="文本作答")
    is_correct = models.BooleanField(default=False, verbose_name="是否正确")
    answered_at = models.DateTimeField(verbose_name="答题时间")

    class Meta:
        db_table = "test_answers"
        ordering = ["-answered_at", "-id"]
        unique_together = ("test_session", "question")
        verbose_name = "测试答案"
        verbose_name_plural = verbose_name
