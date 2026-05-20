from django.db import models

from common.core.models import TimeStampedModel


class AIConversation(TimeStampedModel):
    FEATURE_CHOICES = (
        ("grammar", "语法问答"),
        ("word", "AI讲词"),
        ("study_coach", "学习教练"),
        ("wrong_words", "错词复盘"),
        ("writing", "写作批改"),
        ("translation", "翻译训练"),
        ("report", "学习报告"),
        ("grammar_guide", "语法导学"),
        ("rag", "RAG检索"),
        ("vector_rag", "向量RAG"),
        ("agents", "多Agent简报"),
        ("writing_prompt", "写作题目范文"),
        ("scenario", "情景文本对话"),
        ("observability", "AI观测"),
    )
    STATUS_CHOICES = (
        ("active", "进行中"),
        ("archived", "已归档"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="ai_conversations")
    feature_type = models.CharField(max_length=32, choices=FEATURE_CHOICES, default="study_coach", verbose_name="功能类型")
    title = models.CharField(max_length=128, blank=True, default="", verbose_name="标题")
    context = models.JSONField(default=dict, blank=True, verbose_name="上下文")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active", verbose_name="状态")

    class Meta:
        db_table = "ai_conversations"
        ordering = ["-id"]
        verbose_name = "AI会话"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title or f"{self.user_id}-{self.feature_type}"


class AIMessage(TimeStampedModel):
    ROLE_CHOICES = (
        ("system", "系统"),
        ("user", "用户"),
        ("assistant", "AI"),
    )

    conversation = models.ForeignKey("ai.AIConversation", on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=ROLE_CHOICES, verbose_name="角色")
    content = models.TextField(blank=True, default="", verbose_name="内容")
    payload = models.JSONField(default=dict, blank=True, verbose_name="结构化内容")
    prompt_version = models.CharField(max_length=32, blank=True, default="", verbose_name="提示词版本")
    model_name = models.CharField(max_length=64, blank=True, default="", verbose_name="模型")
    latency_ms = models.PositiveIntegerField(default=0, verbose_name="耗时毫秒")
    runtime_run = models.ForeignKey(
        "ai.AIAsyncRun",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="conversation_messages",
        verbose_name="关联运行",
    )

    class Meta:
        db_table = "ai_messages"
        ordering = ["id"]
        verbose_name = "AI消息"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.conversation_id}-{self.role}"


class AIUserFeedback(TimeStampedModel):
    RATING_CHOICES = (
        ("helpful", "有帮助"),
        ("neutral", "一般"),
        ("unhelpful", "没帮助"),
        ("wrong", "内容有误"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="ai_feedback_items")
    conversation = models.ForeignKey(
        "ai.AIConversation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feedback_items",
    )
    message = models.ForeignKey(
        "ai.AIMessage",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="feedback_items",
    )
    feature_type = models.CharField(max_length=32, blank=True, default="", verbose_name="功能类型")
    rating = models.CharField(max_length=16, choices=RATING_CHOICES, default="helpful", verbose_name="评价")
    content = models.TextField(blank=True, default="", verbose_name="反馈内容")
    payload = models.JSONField(default=dict, blank=True, verbose_name="扩展数据")

    class Meta:
        db_table = "ai_user_feedback"
        ordering = ["-id"]
        verbose_name = "AI反馈"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user_id}-{self.feature_type}-{self.rating}"


class AIStudyReport(TimeStampedModel):
    REPORT_TYPE_CHOICES = (
        ("weekly", "周报"),
        ("monthly", "月报"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="ai_study_reports")
    report_type = models.CharField(max_length=16, choices=REPORT_TYPE_CHOICES, default="weekly", verbose_name="报告类型")
    period_start = models.DateField(verbose_name="开始日期")
    period_end = models.DateField(verbose_name="结束日期")
    title = models.CharField(max_length=128, blank=True, default="", verbose_name="标题")
    summary = models.JSONField(default=dict, blank=True, verbose_name="报告内容")
    source_snapshot = models.JSONField(default=dict, blank=True, verbose_name="数据快照")

    class Meta:
        db_table = "ai_study_reports"
        ordering = ["-period_end", "-id"]
        verbose_name = "AI学习报告"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title or f"{self.user_id}-{self.report_type}-{self.period_end}"


class AIRequestLog(TimeStampedModel):
    STATUS_CHOICES = (
        ("success", "成功"),
        ("failed", "失败"),
        ("rate_limited", "限流"),
    )

    user = models.ForeignKey(
        "users.WxUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_request_logs",
        verbose_name="用户",
    )
    feature_type = models.CharField(max_length=32, db_index=True, verbose_name="功能类型")
    endpoint = models.CharField(max_length=128, blank=True, default="", verbose_name="接口")
    cache_key = models.CharField(max_length=64, blank=True, default="", db_index=True, verbose_name="缓存键")
    cache_hit = models.BooleanField(default=False, verbose_name="是否命中缓存")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="success", db_index=True, verbose_name="状态")
    latency_ms = models.PositiveIntegerField(default=0, verbose_name="耗时毫秒")
    prompt_version = models.CharField(max_length=32, blank=True, default="", verbose_name="提示词版本")
    model_name = models.CharField(max_length=64, blank=True, default="", verbose_name="模型")
    request_payload = models.JSONField(default=dict, blank=True, verbose_name="请求载荷")
    response_payload = models.JSONField(default=dict, blank=True, verbose_name="响应载荷")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")

    class Meta:
        db_table = "ai_run_logs"
        ordering = ["-id"]
        verbose_name = "AI运行日志"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user_id}-{self.feature_type}-{self.status}"


class AIResponseCache(TimeStampedModel):
    feature_type = models.CharField(max_length=32, db_index=True, verbose_name="功能类型")
    cache_key = models.CharField(max_length=64, unique=True, verbose_name="缓存键")
    request_hash = models.CharField(max_length=64, db_index=True, verbose_name="请求哈希")
    response_payload = models.JSONField(default=dict, blank=True, verbose_name="响应载荷")
    expires_at = models.DateTimeField(db_index=True, verbose_name="过期时间")
    hit_count = models.PositiveIntegerField(default=0, verbose_name="命中次数")
    last_hit_at = models.DateTimeField(null=True, blank=True, verbose_name="最近命中时间")

    class Meta:
        db_table = "ai_response_cache"
        ordering = ["-updated_at", "-id"]
        verbose_name = "AI响应缓存"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.feature_type}-{self.cache_key[:12]}"


class AIUserProfileMemory(TimeStampedModel):
    user = models.OneToOneField("users.WxUser", on_delete=models.CASCADE, related_name="ai_profile_memory")
    profile_summary = models.TextField(blank=True, default="", verbose_name="Profile Summary")
    weak_points = models.JSONField(default=list, blank=True, verbose_name="Weak Points")
    preferred_modes = models.JSONField(default=list, blank=True, verbose_name="Preferred Modes")
    recent_focus_words = models.JSONField(default=list, blank=True, verbose_name="Recent Focus Words")
    profile_payload = models.JSONField(default=dict, blank=True, verbose_name="Profile Payload")
    memory_version = models.CharField(max_length=32, blank=True, default="memory_v1", verbose_name="Memory Version")
    updated_from = models.CharField(max_length=32, blank=True, default="", verbose_name="Updated From")

    class Meta:
        db_table = "ai_user_profile_memory"
        verbose_name = "AI User Profile Memory"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user_id}-{self.memory_version}"


class AIEvaluationCase(TimeStampedModel):
    CASE_TYPE_CHOICES = (
        ("rag_recall", "RAG Recall"),
        ("vector_rag", "Vector RAG"),
        ("plan_replan", "Plan Replan"),
        ("retrieval_orchestrator", "Retrieval Orchestrator"),
        ("study_coach", "Study Coach"),
        ("word_tutor", "Word Tutor"),
        ("wrong_words_review", "Wrong Words Review"),
        ("grammar_tutor", "Grammar Tutor"),
        ("conversation", "Conversation"),
    )

    name = models.CharField(max_length=128, verbose_name="Case Name")
    case_type = models.CharField(max_length=32, choices=CASE_TYPE_CHOICES, default="rag_recall", verbose_name="Case Type")
    enabled = models.BooleanField(default=True, verbose_name="Enabled")
    input_payload = models.JSONField(default=dict, blank=True, verbose_name="Input Payload")
    expected_signals = models.JSONField(default=dict, blank=True, verbose_name="Expected Signals")
    description = models.TextField(blank=True, default="", verbose_name="Description")

    class Meta:
        db_table = "ai_evaluation_cases"
        ordering = ["id"]
        verbose_name = "AI Evaluation Case"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class AIEvaluationRun(TimeStampedModel):
    STATUS_CHOICES = (
        ("passed", "Passed"),
        ("failed", "Failed"),
        ("error", "Error"),
    )

    user = models.ForeignKey(
        "users.WxUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_evaluation_runs",
    )
    case = models.ForeignKey("ai.AIEvaluationCase", on_delete=models.CASCADE, related_name="runs")
    feature_type = models.CharField(max_length=32, blank=True, default="", verbose_name="Feature Type")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="passed", verbose_name="Status")
    score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="Score")
    request_payload = models.JSONField(default=dict, blank=True, verbose_name="Request Payload")
    result_payload = models.JSONField(default=dict, blank=True, verbose_name="Result Payload")
    trace_payload = models.JSONField(default=dict, blank=True, verbose_name="Trace Payload")
    failure_reason = models.TextField(blank=True, default="", verbose_name="Failure Reason")
    runtime_snapshot = models.JSONField(default=dict, blank=True, verbose_name="Runtime Snapshot")

    class Meta:
        db_table = "ai_evaluation_runs"
        ordering = ["-id"]
        verbose_name = "AI Evaluation Run"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.case_id}-{self.status}-{self.id}"


class AIAsyncRun(TimeStampedModel):
    STATUS_CHOICES = (
        ("queued", "排队中"),
        ("running", "运行中"),
        ("succeeded", "已完成"),
        ("failed", "失败"),
        ("waiting_approval", "等待审批"),
        ("cancelled", "已取消"),
    )
    RUNTIME_KIND_CHOICES = (
        ("legacy_thread", "旧线程运行时"),
        ("celery", "Celery Worker"),
        ("inline", "同步运行时"),
    )
    APPROVAL_STATE_CHOICES = (
        ("not_required", "无需审批"),
        ("pending", "待审批"),
        ("approved", "已批准"),
        ("rejected", "已拒绝"),
    )

    user = models.ForeignKey("users.WxUser", on_delete=models.CASCADE, related_name="ai_async_runs")
    feature_type = models.CharField(max_length=32, db_index=True, verbose_name="功能类型")
    public_id = models.CharField(max_length=32, unique=True, db_index=True, verbose_name="运行ID")
    runtime_kind = models.CharField(
        max_length=24,
        choices=RUNTIME_KIND_CHOICES,
        default="legacy_thread",
        db_index=True,
        verbose_name="运行时类型",
    )
    queue_name = models.CharField(max_length=32, blank=True, default="", verbose_name="队列名称")
    current_agent = models.CharField(max_length=64, blank=True, default="", verbose_name="当前智能体")
    checkpoint_version = models.CharField(max_length=32, blank=True, default="agent_v1", verbose_name="检查点版本")
    approval_state = models.CharField(
        max_length=24,
        choices=APPROVAL_STATE_CHOICES,
        default="not_required",
        db_index=True,
        verbose_name="审批状态",
    )
    retry_count = models.PositiveIntegerField(default=0, verbose_name="重试次数")
    endpoint = models.CharField(max_length=128, blank=True, default="", verbose_name="接口")
    request_hash = models.CharField(max_length=64, db_index=True, verbose_name="请求哈希")
    request_payload = models.JSONField(default=dict, blank=True, verbose_name="请求载荷")
    result_payload = models.JSONField(default=dict, blank=True, verbose_name="结果载荷")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="queued", db_index=True, verbose_name="状态")
    status_text = models.CharField(max_length=128, blank=True, default="", verbose_name="状态说明")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    latency_ms = models.PositiveIntegerField(default=0, verbose_name="耗时毫秒")
    degraded = models.BooleanField(default=False, verbose_name="是否降级")
    retryable = models.BooleanField(default=True, verbose_name="是否可重试")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    conversation = models.ForeignKey(
        "ai.AIConversation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="agent_runs",
        verbose_name="关联会话",
    )
    parent_run = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_runs",
        verbose_name="父运行",
    )

    class Meta:
        db_table = "ai_async_runs"
        ordering = ["-id"]
        verbose_name = "AI 异步任务"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.feature_type}-{self.public_id}-{self.status}"


class AIAgentStep(TimeStampedModel):
    STEP_KIND_CHOICES = (
        ("agent", "智能体步骤"),
        ("tool", "工具调用"),
        ("critic", "校验步骤"),
        ("system", "系统步骤"),
    )
    STATUS_CHOICES = (
        ("queued", "排队中"),
        ("running", "运行中"),
        ("succeeded", "已完成"),
        ("failed", "失败"),
        ("skipped", "已跳过"),
        ("cancelled", "已取消"),
    )

    run = models.ForeignKey("ai.AIAsyncRun", on_delete=models.CASCADE, related_name="steps", verbose_name="运行")
    parent_step = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_steps",
        verbose_name="父步骤",
    )
    step_index = models.PositiveIntegerField(default=0, db_index=True, verbose_name="步骤序号")
    step_key = models.CharField(max_length=64, blank=True, default="", verbose_name="步骤键")
    step_kind = models.CharField(max_length=16, choices=STEP_KIND_CHOICES, default="agent", verbose_name="步骤类型")
    agent_name = models.CharField(max_length=64, blank=True, default="", verbose_name="智能体名称")
    title = models.CharField(max_length=128, blank=True, default="", verbose_name="标题")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="queued", db_index=True, verbose_name="状态")
    input_payload = models.JSONField(default=dict, blank=True, verbose_name="输入载荷")
    output_payload = models.JSONField(default=dict, blank=True, verbose_name="输出载荷")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="步骤元数据")
    error_message = models.TextField(blank=True, default="", verbose_name="错误信息")
    latency_ms = models.PositiveIntegerField(default=0, verbose_name="耗时毫秒")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="开始时间")
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")

    class Meta:
        db_table = "ai_agent_steps"
        ordering = ["run_id", "step_index", "id"]
        verbose_name = "AI 智能体步骤"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.run_id}-{self.step_index}-{self.agent_name or self.step_key}"


class AIAgentArtifact(TimeStampedModel):
    run = models.ForeignKey("ai.AIAsyncRun", on_delete=models.CASCADE, related_name="artifacts", verbose_name="运行")
    step = models.ForeignKey(
        "ai.AIAgentStep",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="artifacts",
        verbose_name="关联步骤",
    )
    artifact_type = models.CharField(max_length=32, db_index=True, verbose_name="产物类型")
    artifact_key = models.CharField(max_length=64, blank=True, default="", verbose_name="产物键")
    title = models.CharField(max_length=128, blank=True, default="", verbose_name="标题")
    payload = models.JSONField(default=dict, blank=True, verbose_name="产物内容")
    summary = models.TextField(blank=True, default="", verbose_name="摘要")

    class Meta:
        db_table = "ai_agent_artifacts"
        ordering = ["run_id", "id"]
        verbose_name = "AI 智能体产物"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.run_id}-{self.artifact_type}-{self.artifact_key}"


class AIAgentApproval(TimeStampedModel):
    STATUS_CHOICES = (
        ("pending", "待审批"),
        ("approved", "已批准"),
        ("rejected", "已拒绝"),
        ("cancelled", "已取消"),
    )

    run = models.ForeignKey("ai.AIAsyncRun", on_delete=models.CASCADE, related_name="approvals", verbose_name="运行")
    step = models.ForeignKey(
        "ai.AIAgentStep",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approvals",
        verbose_name="关联步骤",
    )
    approval_key = models.CharField(max_length=64, unique=True, db_index=True, verbose_name="审批键")
    feature_type = models.CharField(max_length=32, db_index=True, verbose_name="功能类型")
    action_type = models.CharField(max_length=32, blank=True, default="", verbose_name="动作类型")
    title = models.CharField(max_length=128, blank=True, default="", verbose_name="标题")
    request_payload = models.JSONField(default=dict, blank=True, verbose_name="审批请求")
    decision_payload = models.JSONField(default=dict, blank=True, verbose_name="审批结果")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True, verbose_name="状态")
    decision_note = models.TextField(blank=True, default="", verbose_name="审批备注")
    approved_by = models.ForeignKey(
        "users.WxUser",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_ai_agent_actions",
        verbose_name="审批人",
    )
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="审批时间")

    class Meta:
        db_table = "ai_agent_approvals"
        ordering = ["-id"]
        verbose_name = "AI 智能体审批"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.feature_type}-{self.approval_key}-{self.status}"
