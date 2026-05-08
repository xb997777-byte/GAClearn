const aiApi = require('../../services/modules/ai');
const plansApi = require('../../services/modules/plans');
const store = require('../../store/app-store');
const { withThemePage } = require('../../utils/theme-manager');

function clipText(text, maxLength) {
  if (typeof text !== 'string') {
    return text || '';
  }
  if (!maxLength || text.length <= maxLength) {
    return text;
  }
  return `${text.slice(0, maxLength - 3)}...`;
}

function toPrettyJson(value) {
  try {
    return JSON.stringify(value || {}, null, 2);
  } catch (error) {
    return '{}';
  }
}

function summarizeObject(source, maxKeys) {
  if (!source || typeof source !== 'object' || Array.isArray(source)) {
    return source || null;
  }
  const summary = {};
  Object.keys(source).slice(0, maxKeys || 5).forEach((key) => {
    const value = source[key];
    if (typeof value === 'string') {
      summary[key] = clipText(value, 60);
      return;
    }
    if (Array.isArray(value)) {
      summary[key] = value.slice(0, 3);
      return;
    }
    if (value && typeof value === 'object') {
      summary[key] = '[object]';
      return;
    }
    summary[key] = value;
  });
  return summary;
}

function trimList(list, limit, mapper) {
  if (!Array.isArray(list) || !list.length) {
    return [];
  }
  return list.slice(0, limit).map((item, index) => mapper(item || {}, index));
}

function flattenFieldErrors(fieldErrors) {
  if (!fieldErrors || typeof fieldErrors !== 'object') {
    return '';
  }
  return Object.keys(fieldErrors).map((key) => {
    const value = fieldErrors[key];
    if (Array.isArray(value)) {
      return `${key}: ${value.join('；')}`;
    }
    if (value && typeof value === 'object') {
      return `${key}: ${toPrettyJson(value)}`;
    }
    return `${key}: ${value}`;
  }).join('\n');
}

function buildErrorPanel(error, fallbackTitle, requestPayload) {
  const message = (error && error.message) || fallbackTitle || '请求失败';
  return {
    title: fallbackTitle || '请求失败',
    message,
    code: (error && error.code) || '',
    requestText: toPrettyJson(requestPayload || {}),
    fieldErrorsText: flattenFieldErrors(error && error.fieldErrors),
    responseText: toPrettyJson((error && (error.response || error.data)) || {})
  };
}

function translateStatus(status) {
  const mapping = {
    success: '成功',
    succeeded: '成功',
    ok: '成功',
    completed: '已完成',
    running: '运行中',
    pending: '待处理',
    queued: '排队中',
    failed: '失败',
    failure: '失败',
    error: '失败'
  };
  return mapping[status] || status || '';
}

function normalizeHandoffs(list) {
  return trimList(list, 6, (item) => ({
    from: clipText(item.from || '', 24),
    to: clipText(item.to || '', 24),
    reason: clipText(item.reason || '', 140)
  }));
}

function normalizeRoles(list) {
  return trimList(list, 6, (item) => ({
    name: clipText(item.name || '', 24),
    title: clipText(item.title || '', 32),
    responsibility: clipText(item.responsibility || '', 120),
    output: clipText(item.output || '', 120)
  }));
}

function normalizeTrace(list) {
  return trimList(list, 10, (item) => ({
    phase: clipText(item.phase || '', 24),
    name: clipText(item.name || '', 32),
    detail: clipText(item.detail || '', 120),
    status: translateStatus(item.status || ''),
    latency_ms: Number(item.latency_ms || 0),
    meta: summarizeObject(item.meta, 5),
    line: buildTraceLine(item)
  }));
}

function buildTraceLine(item) {
  if (!item) {
    return '';
  }
  const prefix = item.phase ? `[${item.phase}] ` : '';
  const latency = item.latency_ms ? ` · ${item.latency_ms}ms` : '';
  return `${prefix}${item.name || ''}${latency}${item.detail ? ` · ${item.detail}` : ''}`;
}

function normalizeEvidence(evidence) {
  if (!evidence) {
    return null;
  }

  const workflow = evidence.workflow || null;

  return {
    summary: clipText(evidence.summary || '', 180),
    workflow: workflow ? {
      label: workflow.label || '',
      steps: trimList(workflow.steps, 5, (item) => ({
        name: clipText(item.name || '', 32),
        detail: clipText(item.detail || '', 96)
      }))
    } : null,
    tools_used: trimList(evidence.tools_used, 4, (item) => ({
      name: clipText(item.name || '', 32),
      detail: clipText(item.detail || '', 96),
      args: summarizeObject(item.args, 5)
    })),
    trace_timeline: trimList(evidence.trace_timeline, 6, (item) => ({
      step: clipText(item.step || '', 36),
      phase: clipText(item.phase || '', 20),
      detail: clipText(item.detail || '', 96),
      status: translateStatus(item.status || ''),
      tool_name: clipText(item.tool_name || '', 28),
      meta: summarizeObject(item.meta, 5)
    })),
    retrieval_hits: trimList(evidence.retrieval_hits, 5, (item) => ({
      title: clipText(item.title || '', 40),
      source_type: clipText(item.source_type || '', 24),
      reason: clipText(item.reason || '', 88),
      preview: clipText(item.preview || '', 100),
      score: item.score
    })),
    observability: evidence.observability || null
  };
}

function normalizePlanReplanResult(data) {
  const source = data || {};
  const newPlan = source.new_plan || {};
  const studyOrder = Array.isArray(newPlan.study_order) ? newPlan.study_order : [];
  const timeBlocks = Array.isArray(newPlan.time_blocks) ? newPlan.time_blocks : [];
  const focusWords = Array.isArray(newPlan.focus_words) ? newPlan.focus_words.filter(Boolean) : [];
  const decision = source.decision || {};
  const selectedTools = Array.isArray((source.multi_agent || {}).selected_tools)
    ? (source.multi_agent || {}).selected_tools
    : [];
  return {
    headline: source.headline || '',
    summary: source.summary || '',
    new_plan: newPlan,
    plan_patch: source.plan_patch || {},
    decision,
    planCardTitle: newPlan.focus_mode_label || source.headline || 'AI 今日学习计划',
    planCardSummary: source.summary || '已根据当前计划、复习压力、错词和学习趋势生成新的今日安排。',
    planFocusWords: focusWords,
    planStudyOrder: studyOrder,
    planTimeBlocks: timeBlocks,
    decisionReasons: Array.isArray(decision.reasons) ? decision.reasons : [],
    decisionRisks: Array.isArray(decision.risks) ? decision.risks : [],
    expectedBenefit: decision.expected_benefit || '',
    multi_agent: {
      roles: normalizeRoles((source.multi_agent || {}).roles),
      handoffs: normalizeHandoffs((source.multi_agent || {}).handoffs),
      selected_tools: selectedTools,
      selected_tools_text: selectedTools.join(' · ')
    },
    langchain_trace: normalizeTrace(source.langchain_trace),
    feature_runtime: source.feature_runtime || {},
    runtime_stack: source.runtime_stack || {},
    evidence: normalizeEvidence(source.evidence),
    ai_observability: source.ai_observability || null
  };
}

function normalizeRetrievalOrchestratorResult(data) {
  const source = data || {};
  const queryAnalysis = source.query_analysis || {};
  const keywords = Array.isArray(queryAnalysis.keywords) ? queryAnalysis.keywords : [];
  const selection = source.selection || {};
  const comparison = selection.comparison || {};
  const selectedPathReason = Array.isArray((source.multi_agent || {}).selected_path_reason)
    ? (source.multi_agent || {}).selected_path_reason
    : [];
  return {
    headline: source.headline || '',
    summary: source.summary || '',
    query_analysis: {
      ...queryAnalysis,
      keywords,
      keywords_text: keywords.join('，')
    },
    selection: {
      ...selection,
      comparison
    },
    final_answer: source.final_answer || {},
    tool_trace: Array.isArray(source.tool_trace) ? source.tool_trace : [],
    multi_agent: {
      roles: normalizeRoles((source.multi_agent || {}).roles),
      handoffs: normalizeHandoffs((source.multi_agent || {}).handoffs),
      selected_path_reason: selectedPathReason
    },
    langchain_trace: normalizeTrace(source.langchain_trace),
    feature_runtime: source.feature_runtime || {},
    runtime_stack: source.runtime_stack || {},
    agent_flow: source.agent_flow || {},
    evidence: normalizeEvidence(source.evidence),
    structuredSummary: (((source.knowledge || {}).structured_rag || {}).answer || {}).summary || '',
    hybridSummary: (((source.knowledge || {}).hybrid_rag || {}).answer || {}).summary || '',
    hybridDocs: normalizeVectorDocuments((((source.knowledge || {}).hybrid_rag || {}).documents || []))
  };
}

function normalizeLightFeatureResult(data) {
  const source = data || {};
  const result = source.result || {};
  const tutor = source.tutor || null;
  const coach = source.coach || null;
  const review = source.review || null;
  const answer = source.answer || null;
  const answerSummary = typeof answer === 'string'
    ? answer
    : ((answer && answer.summary) || '');
  const groundedPoints = Array.isArray(answer && answer.grounded_points) ? answer.grounded_points : [];
  const conversation = source.conversation || null;
  const assistantMessage = source.assistant_message || null;
  const featureRuntime = source.feature_runtime || {};
  const aiStrategy = source.ai_strategy || {};
  const linkedWords = Array.isArray(result.linked_words) ? result.linked_words : [];
  const linkedGrammarPoints = Array.isArray(result.linked_grammar_points) ? result.linked_grammar_points : [];
  const contextSources = Array.isArray(source.context_sources) ? source.context_sources : [];
  return {
    headline: source.headline || '',
    summary: source.summary || '',
    feature_runtime: featureRuntime,
    runtime_stack: source.runtime_stack || {},
    context_sources: contextSources,
    context_sources_text: contextSources.map((item) => item.label || item.key || '').filter(Boolean).join(' · '),
    langchain_trace: normalizeTrace(source.langchain_trace),
    evidence: normalizeEvidence(source.evidence),
    ai_observability: source.ai_observability || null,
    ai_strategy: aiStrategy,
    result,
    tutor,
    coach,
    review,
    retrieval: source.retrieval || {},
    conversation,
    assistant_message: assistantMessage,
    answer,
    answer_summary: answerSummary,
    grounded_points: groundedPoints,
    linked_words: linkedWords,
    linked_words_text: linkedWords.map((item) => item.word || '').filter(Boolean).join(' · '),
    linked_grammar_points: linkedGrammarPoints,
    linked_grammar_points_text: linkedGrammarPoints.map((item) => item.title || '').filter(Boolean).join(' · '),
    runtime_badges: [
      featureRuntime.path || '',
      featureRuntime.orchestrator || '',
      aiStrategy.model_name || ''
    ].filter(Boolean)
  };
}

function normalizeEvaluationRun(data) {
  const source = data || {};
  const caseInfo = source.case || null;
  const featureRuntime = source.feature_runtime || {};
  const tags = Array.isArray(featureRuntime.tags) ? featureRuntime.tags : [];
  return {
    id: source.id,
    case_name: source.case_name || '',
    case_type: source.case_type || '',
    feature_type: source.feature_type || '',
    status: translateStatus(source.status || ''),
    score: Number(source.score || 0),
    failure_reason: source.failure_reason || '',
    prompt_version: source.prompt_version || '',
    model_name: source.model_name || '',
    created_at: source.created_at || '',
    feature_runtime: featureRuntime,
    runtime_stack: source.runtime_stack || {},
    request_payload: source.request_payload || {},
    result_payload: source.result_payload || {},
    trace_payload: source.trace_payload || {},
    runtime_snapshot: source.runtime_snapshot || {},
    trace_steps: Number(source.trace_steps || 0),
    case: caseInfo,
    replay_payload: source.replay_payload || {},
    requestPayloadText: toPrettyJson(source.request_payload || {}),
    resultPayloadText: toPrettyJson(source.result_payload || {}),
    tracePayloadText: toPrettyJson(source.trace_payload || {}),
    runtimeSnapshotText: toPrettyJson(source.runtime_snapshot || {}),
    traceSummaryText: `${source.feature_type || source.case_type || 'ai'} · ${tags.join(' / ') || featureRuntime.path || 'direct'}`,
    runtimeTagText: tags.join(' / ')
  };
}

function normalizeConversationList(list) {
  return (Array.isArray(list) ? list : []).map((item) => ({
    id: item.id,
    title: item.title || `会话 ${item.id}`,
    feature_type: item.feature_type || '',
    updated_at: item.updated_at || '',
    created_at: item.created_at || '',
    tagText: `${getConversationFeatureLabel(item.feature_type || 'rag')} · ${item.updated_at || item.created_at || ''}`
  }));
}

function getConversationFeatureLabel(featureType) {
  const mapping = {
    rag: 'RAG 问答',
    grammar: '语法',
    writing: '写作',
    translation: '翻译'
  };
  return mapping[featureType] || featureType || 'AI';
}

function normalizeConversationDetail(data) {
  const source = data || {};
  return {
    id: source.id || 0,
    feature_type: source.feature_type || '',
    title: source.title || '',
    context: source.context || {},
    status: source.status || '',
    updated_at: source.updated_at || '',
    created_at: source.created_at || '',
    messages: (Array.isArray(source.messages) ? source.messages : []).map((item) => ({
      id: item.id,
      role: item.role || '',
      content: item.content || '',
      payload: item.payload || {},
      prompt_version: item.prompt_version || '',
      model_name: item.model_name || '',
      latency_ms: Number(item.latency_ms || 0),
      created_at: item.created_at || '',
      metaText: [item.prompt_version || '', item.model_name || '', item.latency_ms ? `${item.latency_ms}ms` : '']
        .filter(Boolean)
        .join(' · ')
    })),
    message_count: Array.isArray(source.messages) ? source.messages.length : 0,
    feature_label: getConversationFeatureLabel(source.feature_type)
  };
}

function normalizeMcpDemoResult(data) {
  const source = data || {};
  const result = source.result || {};
  const previewSummary = result.summary
    || result.profile_summary
    || result.description
    || result.headline
    || (Array.isArray(result.list) ? `返回 ${result.list.length} 条记录` : '');
  const previewHeadline = result.headline
    || result.name
    || result.title
    || source.tool_name
    || '';
  return {
    tool_name: source.tool_name || '',
    result: {
      headline: previewHeadline,
      summary: previewSummary,
      langchain_trace: normalizeTrace(result.langchain_trace),
      runtime_stack: result.runtime_stack || {},
      evidence: normalizeEvidence(result.evidence),
      ai_observability: result.ai_observability || null
    }
  };
}

function normalizeMcpResourceResult(data) {
  const source = data || {};
  const payload = source.data || {};
  return {
    uri: source.uri || '',
    template: source.template || '',
    name: source.name || '',
    description: source.description || '',
    resource_type: payload.resource_type || '',
    item: payload.item || {}
  };
}

function normalizeObservability(data) {
  const source = data || {};
  return {
    window: source.window || {},
    totals: source.totals || {},
    status_summary: source.status_summary || {},
    prompt_versions: Array.isArray(source.prompt_versions) ? source.prompt_versions : [],
    model_summary: Array.isArray(source.model_summary) ? source.model_summary : [],
    feature_summary: Array.isArray(source.feature_summary) ? source.feature_summary : [],
    runtime_path_summary: (Array.isArray(source.runtime_path_summary) ? source.runtime_path_summary : []).map((item) => ({
      path: item.path || '',
      total: Number(item.total || 0)
    })),
    recent_logs: (Array.isArray(source.recent_logs) ? source.recent_logs : []).map((item) => ({
      ...item,
      status_text: translateStatus(item.status || '')
    }))
  };
}

function normalizeMcpManifest(data) {
  const source = data || {};
  return {
    ...source,
    transport_modes: Array.isArray(source.transport_modes) ? source.transport_modes : [],
    transport_modes_text: (Array.isArray(source.transport_modes) ? source.transport_modes : []).join(' / '),
    tools: Array.isArray(source.tools) ? source.tools : [],
    resources: Array.isArray(source.resources) ? source.resources : [],
    prompts: Array.isArray(source.prompts) ? source.prompts : []
  };
}

function buildDefaultValueBySchema(schema) {
  const source = schema || {};
  if (source.default !== undefined) {
    return source.default;
  }
  if (Array.isArray(source.enum) && source.enum.length) {
    return source.enum[0];
  }
  if (source.type === 'integer' || source.type === 'number') {
    return 1;
  }
  if (source.type === 'boolean') {
    return false;
  }
  if (source.type === 'array') {
    return [];
  }
  if (source.type === 'object') {
    return {};
  }
  return '';
}

function buildToolArgsFromSchema(schema, toolName) {
  const inputSchema = schema || {};
  const properties = inputSchema.properties || {};
  const args = {};
  Object.keys(properties).forEach((key) => {
    args[key] = buildDefaultValueBySchema(properties[key]);
  });
  if (toolName === 'plan_replanner' && args.trend_days === undefined) {
    args.trend_days = 7;
  }
  if (toolName === 'rag_search') {
    if (!args.query) {
      args.query = 'important 和 significant 的区别是什么？';
    }
    if (args.limit === undefined) {
      args.limit = 5;
    }
  }
  if (toolName === 'vector_rag_search') {
    if (!args.query) {
      args.query = 'important 的近义表达和例句';
    }
    if (args.limit === undefined) {
      args.limit = 6;
    }
    if (!args.retrieval_mode) {
      args.retrieval_mode = 'auto';
    }
  }
  if (toolName === 'get_profile_memory') {
    return {};
  }
  return args;
}

function buildMcpToolState(manifest, selectedToolName) {
  const tools = (manifest && Array.isArray(manifest.tools)) ? manifest.tools : [];
  const fallbackToolName = selectedToolName || (tools[0] && tools[0].name) || 'get_profile_memory';
  const selectedTool = tools.find((item) => item.name === fallbackToolName) || tools[0] || null;
  const nextToolName = (selectedTool && selectedTool.name) || fallbackToolName;
  const schema = (selectedTool && selectedTool.input_schema) || {};
  const properties = schema.properties || {};
  const requiredFields = Array.isArray(schema.required) ? schema.required : [];
  const schemaFields = Object.keys(properties).map((key) => ({
    name: key,
    type: properties[key].type || 'string',
    required: requiredFields.indexOf(key) > -1
  }));
  return {
    selectedTool,
    selectedToolName: nextToolName,
    selectedArgs: buildToolArgsFromSchema(selectedTool && selectedTool.input_schema, nextToolName),
    schemaHint: schemaFields.length
      ? `参数 ${schemaFields.map((item) => `${item.name}(${item.type}${item.required ? '，必填' : ''})`).join('、')}`
      : '当前工具无必填参数',
    schemaFields,
    options: tools.map((item) => ({
      name: item.name,
      description: item.description || '',
      className: item.name === nextToolName ? 'ai-choice active' : 'ai-choice'
    }))
  };
}

function buildMcpToolOptions(manifest) {
  const tools = (manifest && Array.isArray(manifest.tools)) ? manifest.tools : [];
  return tools.map((item) => ({
    name: item.name,
    description: item.description || '',
    className: item.name === 'get_profile_memory' ? 'ai-choice active' : 'ai-choice'
  }));
}

function buildMcpResourceExamples(manifest) {
  const resources = (manifest && Array.isArray(manifest.resources)) ? manifest.resources : [];
  return resources
    .map((item) => ({
      uri: item.example_uri || item.uri || '',
      label: item.name || item.uri || '',
      description: item.description || '',
      className: (item.example_uri || item.uri || '') === 'ai://profile-memory/self' ? 'ai-choice active' : 'ai-choice'
    }))
    .filter((item) => !!item.uri);
}

function normalizeQuality(data) {
  const source = data || {};
  return {
    message_count: Number(source.message_count || 0),
    week_request_count: Number(source.week_request_count || 0),
    cache_hit_count: Number(source.cache_hit_count || 0),
    active_cache_items: Number(source.active_cache_items || 0),
    feedback_summary: source.feedback_summary || {},
    status_summary: source.status_summary || {},
    quality_notes: Array.isArray(source.quality_notes) ? source.quality_notes : [],
    ai_strategy: source.ai_strategy || {}
  };
}

function normalizeAgentsBrief(data) {
  const source = data || {};
  const demos = Array.isArray(source.demos) ? source.demos : [];
  return {
    headline: source.headline || '多 Agent 协作架构说明',
    agents: Array.isArray(source.agents) ? source.agents : [],
    recommended_flow: Array.isArray(source.recommended_flow) ? source.recommended_flow : [],
    demos,
    demos_text: demos.map((item) => `${item.name || ''} · ${item.entry || ''}`).join('\n'),
    ai_strategy: source.ai_strategy || {}
  };
}

function normalizeScenarioTemplates(list) {
  return (Array.isArray(list) ? list : []).map((item) => ({
    scenario: item.scenario || '',
    label: item.label || item.scenario || '',
    mission: item.mission || '',
    coach_focus: item.coach_focus || ''
  }));
}

function normalizeRagResult(data) {
  const source = data || {};
  const answer = source.answer || {};
  return {
    ...source,
    answer,
    answer_points: Array.isArray(answer.grounded_points) ? answer.grounded_points : []
  };
}

function normalizeVectorRagResult(data) {
  const source = data || {};
  const answer = source.answer || {};
  const retrievalStrategy = source.retrieval_strategy || {};
  const retrievalExplain = source.retrieval_explain || {};
  return {
    ...source,
    answer,
    retrieval_strategy: {
      ...retrievalStrategy,
      external_vector_db: !!retrievalStrategy.external_vector_db
    },
    retrieval_explain: {
      ...retrievalExplain,
      why_this_result: Array.isArray(retrievalExplain.why_this_result) ? retrievalExplain.why_this_result : []
    }
  };
}

function normalizeRagRecallResult(data) {
  const source = data || {};
  return {
    ...source,
    structured_recall: source.structured_recall || {},
    vector_recall: source.vector_recall || {}
  };
}

function normalizeRagRuntime(runtime) {
  const source = runtime || {};
  const catalog = Array.isArray(source.knowledge_source_catalog) ? source.knowledge_source_catalog : [];
  return {
    type: source.type || '',
    version: source.version || '',
    backend: source.backend || '',
    embedding_model: source.embedding_model || '',
    embedding_backend: source.embedding_backend || '',
    embedding_provider: source.embedding_provider || '',
    collection_name: source.collection_name || '',
    storage_path: source.storage_path || '',
    available: !!source.available,
    indexed: !!source.indexed,
    chunk_count: Number(source.chunk_count || 0),
    chunk_version: source.chunk_version || '',
    retrieval_mode: source.retrieval_mode || '',
    fallback_runtime: source.fallback_runtime || '',
    rebuild_command: source.rebuild_command || '',
    notes: Array.isArray(source.notes) ? source.notes : [],
    knowledge_sources: Array.isArray(source.knowledge_sources) ? source.knowledge_sources : [],
    knowledge_source_catalog: catalog.map((item) => ({
      key: item.key || '',
      label: item.label || item.key || '',
      table: item.table || '',
      description: item.description || '',
      record_count: Number(item.record_count || 0)
    }))
  };
}

function normalizeRagIndexStatus(status) {
  const source = status || {};
  const totalCount = Number(source.total_count || 0);
  const insertedCount = Number(source.inserted_count || 0);
  const progressPercent = Number(source.progress_percent || 0);
  const running = !!source.running;
  const state = source.state || 'idle';
  return {
    state,
    stateLabel: getRagStateLabel(state),
    running,
    pid_list: Array.isArray(source.pid_list) ? source.pid_list : [],
    pid_text: (Array.isArray(source.pid_list) ? source.pid_list : []).join(', '),
    inserted_count: insertedCount,
    total_count: totalCount,
    expected_chunk_count: Number(source.expected_chunk_count || 0),
    runtime_chunk_count: Number(source.runtime_chunk_count || 0),
    progress_percent: progressPercent,
    progressWidth: `width:${Math.max(4, Math.min(100, progressPercent || 0))}%;`,
    last_progress_line: source.last_progress_line || '',
    latest_line: source.latest_line || '',
    last_error_line: source.last_error_line || '',
    log_tail: Array.isArray(source.log_tail) ? source.log_tail : [],
    error_log_tail: Array.isArray(source.error_log_tail) ? source.error_log_tail : [],
    embedding_backend: source.embedding_backend || '',
    embedding_provider: source.embedding_provider || '',
    embedding_model: source.embedding_model || '',
    status_updated_at: source.status_updated_at || '',
    status_started_at: source.status_started_at || '',
    actionHint: running
      ? '索引正在后台持续写入，页面会自动轮询更新。'
      : state === 'completed'
        ? '索引已经完成，除非你新增了词库/语法数据，否则不需要重复全量构建。'
        : '当前还没有检测到正在运行的构建任务。先启动重建命令后，这里的进度才会持续变化。',
    refreshHint: '刷新索引状态：重新读取后台构建进度、日志和当前已写入数量。',
    syncHint: '增量同步索引：把新增或修改过的知识块补写进 Chroma，不会做整库重建。',
    hasProgress: totalCount > 0,
    progressText: totalCount
      ? `${insertedCount} / ${totalCount}`
      : (source.latest_line || '暂无构建进度')
  };
}

function getRagStateLabel(state) {
  const mapping = {
    idle: '未开始',
    running: '构建中',
    completed: '已完成',
    failed: '失败'
  };
  return mapping[state] || '未知';
}

function normalizeVectorDocuments(list) {
  return (Array.isArray(list) ? list : []).slice(0, 6).map((item) => ({
    title: item.title || '',
    source_type: item.source_type || '',
    score: item.score,
    rerank_score: item.rerank_score,
    source_scope: ((item.metadata || {}).source_scope) || '',
    match_reason: item.match_reason || '',
    highlights: Array.isArray(item.highlights) ? item.highlights : [],
    highlights_text: (Array.isArray(item.highlights) ? item.highlights : []).join('\n'),
    matched_keywords: Array.isArray(item.matched_keywords) ? item.matched_keywords : [],
    matched_keywords_text: (Array.isArray(item.matched_keywords) ? item.matched_keywords : []).join(', '),
    retrieval_sources: Array.isArray(item.retrieval_sources) ? item.retrieval_sources : [],
    retrieval_sources_text: (Array.isArray(item.retrieval_sources) ? item.retrieval_sources : []).join(' + '),
    rank_debug: item.rank_debug || {}
  }));
}

function buildRagModeCards(mode) {
  if (mode === 'tech') {
    return [
      {
        title: '结构化检索实现',
        detail: '先抽取关键词，再从词条、语法点和例句表里做数据库检索，适合稳定查词义和规则。'
      },
      {
        title: '向量检索实现',
        detail: '标准模式下会先把项目教学数据切成知识块，做 embedding 后写入 Chroma，再按相似度召回；语义模型不可用时会临时降级。'
      },
      {
        title: '当前是否有外部向量库',
        detail: '现在已经预留并接入 Chroma 标准 RAG；如果依赖没装好或索引没建好，才会回退到项目内本地轻量实现。'
      },
      {
        title: '后续升级方向',
        detail: '下一步可以继续补 rerank、hybrid search、多路召回和用户弱项知识入库。'
      }
    ];
  }

  return [
    {
      title: '结构化 RAG',
      detail: '更像按词典目录直查，适合查词义区别、例句和对应语法点。'
    },
    {
      title: '向量 RAG',
      detail: '更像按相近意思找资料，就算你的提问说法不完全一样，也会尽量找接近内容。'
    },
    {
      title: '这块真正做的事',
      detail: '先查你项目自己的词库、语法库和例句库，必要时走 Chroma 召回，再根据命中的资料给出解释。'
    },
    {
      title: '你现在项目里的状态',
      detail: '现在主路径已经是标准 RAG 方案；如果依赖没安装或索引没重建，会自动退回到本地轻量检索。'
    }
  ];
}

function buildModuleMaturityPanels(capabilities, ragRuntime, mcpManifest) {
  const runtime = ragRuntime || {};
  const manifest = mcpManifest || {};
  const toolsCount = (manifest.tools || []).length;
  const ragAvailable = !!runtime.available;
  const ragIndexed = !!runtime.indexed;
  const ragBackend = runtime.backend || '本地回退链路';

  return [
    {
      key: 'agent',
      title: 'Agent',
      status: '可用',
      tone: 'ready',
      detail: '学习计划重规划和检索编排都已升级为真实多 Agent 协作流。',
      note: '适合作为项目里的主 AI 亮点。'
    },
    {
      key: 'rag',
      title: 'RAG',
      status: ragAvailable ? '可用' : '演示版',
      tone: ragAvailable ? 'ready' : 'demo',
      detail: ragAvailable
        ? `结构化 RAG + ${ragBackend} 向量检索已接通${ragIndexed ? '，索引链路可用。' : '，但还需要重建索引。'}`
        : 'RAG 页面和召回解释已做完，当前环境会优先回退到本地轻量检索。',
      note: ragIndexed ? '支持索引状态、增量同步和个性化 RAG。' : '适合先演示原理，再补全索引构建。'
    },
    {
      key: 'mcp',
      title: 'MCP',
      status: capabilities && capabilities.mcp_stdio_available ? 'STDIO 可用' : 'HTTP 可用',
      tone: 'ready',
      detail: capabilities && capabilities.mcp_stdio_available
        ? `已抽象 ${toolsCount} 个工具，并同时支持小程序 HTTP 调用与独立 STDIO Server。`
        : `已抽象 ${toolsCount} 个工具，HTTP 接口可直接给小程序使用。`,
      note: capabilities && capabilities.mcp_stdio_available ? '现在可以作为独立 MCP Server 演示。' : '当前以 HTTP 为主，STDIO 视环境可用。'
    },
    {
      key: 'apps',
      title: '应用',
      status: '可用',
      tone: 'ready',
      detail: '讲词、学习教练、语法导学、错词复盘、报告等场景已经接进产品页面。',
      note: '用户能直接感知这部分 AI 能力。'
    },
    {
      key: 'ops',
      title: '观测',
      status: '可用',
      tone: 'ready',
      detail: '已能看 evidence、日志、LangChain trace 和失败信息。',
      note: '更偏工程展示能力，但现在已经能明显看出链路。'
    }
  ];
}

Page(withThemePage({
  data: {
    activeTab: 'apps',
    capabilityIntroCollapsed: true,
    moduleMaturityCollapsed: true,
    appsLoading: false,
    opsLoading: false,
    agentLoading: false,
    profileRefreshing: false,
    mcpLoading: false,
    capabilities: null,
    ragRuntime: null,
    mcpManifest: null,
    stackShowcase: [],
    moduleMaturityPanels: [],
    observability: null,
    quality: null,
    ragIndexStatus: null,
    ragIndexLoading: false,
    ragSyncLoading: false,
    reportHistory: [],
    report: null,
    planReplanResult: null,
    currentPlan: null,
    planApplying: false,
    retrievalOrchestratorLoading: false,
    retrievalOrchestratorQuery: 'important 和 significant 的区别，应该怎么学？',
    retrievalOrchestratorResult: null,
    retrievalOrchestratorError: null,
    mcpDemoTool: 'get_profile_memory',
    mcpDemoToolOptions: [],
    mcpDemoToolSchema: null,
    mcpDemoToolSchemaHint: '',
    mcpDemoToolSchemaFields: [],
    mcpDemoToolArgs: {},
    mcpDemoToolArgsText: '{}',
    mcpDemoResult: null,
    mcpDemoError: null,
    mcpResourceUri: 'ai://profile-memory/self',
    mcpResourceExamples: [],
    mcpResourceLoading: false,
    mcpResourceResult: null,
    mcpResourceError: null,
    ragViewMode: 'learning',
    ragModeCards: buildRagModeCards('learning'),
    ragQuery: 'important 和 significant 怎么区分？',
    ragResult: null,
    ragSearchLoading: false,
    vectorRagQuery: 'important 的近义表达和例句',
    vectorRagResult: null,
    vectorRagLoading: false,
    ragRecallKeywords: 'important, significant, example',
    ragRecallPreferredSourceType: 'word',
    ragRecallResult: null,
    ragRecallLoading: false,
    vectorRagMode: 'auto',
    vectorDocPreview: [],
    grammarGuide: null,
    agentsBrief: null,
    profileMemory: null,
    evaluationCases: [],
    evaluationRuns: [],
    evaluationSummary: null,
    evaluationRunning: false,
    evaluationRunDetailLoading: false,
    evaluationReplayLoading: false,
    selectedEvaluationRun: null,
    appWorkspaceTab: 'grammar',
    appQueryLoading: false,
    appConversationLoading: false,
    appConversationFollowupLoading: false,
    appGrammarSentence: 'The teacher who checks our essays every week offers clear advice before class.',
    appGrammarQuestion: '',
    appGrammarResult: null,
    appWritingTopic: 'How to build a steady English learning routine',
    appWritingLevel: 'cet4',
    appWritingGenre: 'essay',
    appWritingPromptResult: null,
    appWritingText: 'I think learning English every day is helpful because it can make me keep progress.',
    appWritingCorrectResult: null,
    appTranslationSource: '坚持每天复习旧单词，会让你更容易真正记住它们。',
    appTranslationUserAnswer: '',
    appTranslationResult: null,
    appScenario: 'daily',
    appScenarioMessage: 'Hi, I want to practice speaking English with you.',
    appScenarioResult: null,
    appScenarioTemplates: [],
    appConversationFeatureType: 'rag',
    appConversationQuestion: 'How should I learn the difference between important and significant?',
    appConversationFollowup: '',
    appConversationList: [],
    appConversationId: 0,
    appConversationDetail: null,
    appConversationAnswer: null,
    evaluationRunDetail: null
  },

  onLoad(options = {}) {
    this.agentRequesting = false;
    this.profileMemoryRefreshing = false;
    this.mcpToolRunning = false;
    this.ragIndexPollingTimer = null;
    this.applicationsLoaded = false;
    this.observabilityLoaded = false;
    this.pendingOptions = options || {};
    this.applyAiCenterIntent(options || {}, { silent: true });
    this.loadOverview();
  },

  onShow() {
    getApp().setTabBarSelected(3);
    const pendingIntent = store.consumeAiCenterIntent();
    if (pendingIntent) {
      this.applyAiCenterIntent(pendingIntent);
    }
    if (this.data.activeTab === 'rag') {
      this.startRagIndexPolling();
    }
  },

  onHide() {
    this.stopRagIndexPolling();
  },

  onUnload() {
    this.stopRagIndexPolling();
  },

  async loadOverview() {
    try {
      const [capabilities, mcpManifest, reports, profileMemory, evaluationData, currentPlan, ragIndexStatus] = await Promise.all([
        aiApi.getCapabilities(),
        aiApi.getMcpManifest(),
        aiApi.listReports({ limit: 5, include_compare: true }),
        aiApi.getProfileMemory(),
        aiApi.getEvaluations({ limit: 6 }),
        plansApi.getCurrentPlan().catch(() => null),
        aiApi.getRagIndexStatus().catch(() => null)
      ]);
      const normalizedRagRuntime = normalizeRagRuntime(capabilities && capabilities.rag_runtime);
      const mcpToolState = buildMcpToolState(mcpManifest, this.data.mcpDemoTool);
      this.setData({
        capabilities,
        ragRuntime: normalizedRagRuntime,
        ragIndexStatus: normalizeRagIndexStatus(ragIndexStatus),
        mcpManifest: normalizeMcpManifest(mcpManifest),
        mcpDemoTool: mcpToolState.selectedToolName,
        mcpDemoToolOptions: mcpToolState.options,
        mcpDemoToolSchema: mcpToolState.selectedTool ? (mcpToolState.selectedTool.input_schema || null) : null,
        mcpDemoToolSchemaHint: mcpToolState.schemaHint,
        mcpDemoToolSchemaFields: mcpToolState.schemaFields,
        mcpDemoToolArgs: mcpToolState.selectedArgs,
        mcpDemoToolArgsText: toPrettyJson(mcpToolState.selectedArgs),
        mcpResourceExamples: buildMcpResourceExamples(mcpManifest),
        stackShowcase: this.buildStackShowcase(capabilities, mcpManifest),
        moduleMaturityPanels: buildModuleMaturityPanels(capabilities, normalizedRagRuntime, mcpManifest),
        reportHistory: reports.list || [],
        report: reports.list && reports.list.length ? reports.list[0] : null,
        profileMemory,
        currentPlan: currentPlan || null,
        evaluationCases: evaluationData.cases || [],
        evaluationRuns: (evaluationData.runs || []).map(normalizeEvaluationRun),
        evaluationSummary: evaluationData.summary || null
      });
      if (this.data.activeTab === 'apps' && !this.applicationsLoaded) {
        this.loadApplications();
      }
      if (this.data.activeTab === 'ops' && !this.observabilityLoaded) {
        this.loadObservability();
      }
      this.syncRagIndexPolling();
    } catch (error) {
      wx.showToast({ title: 'AI 中心加载失败', icon: 'none' });
    }
  },

  switchTab(event) {
    const { tab } = event.currentTarget.dataset;
    if (!tab) {
      return;
    }
    this.setData({ activeTab: tab });
    if (tab === 'rag') {
      this.refreshRagIndexStatus({ silent: true });
      this.startRagIndexPolling();
    } else {
      this.stopRagIndexPolling();
    }
    if (tab === 'apps' && !this.applicationsLoaded) {
      this.loadApplications();
    }
    if (tab === 'ops' && !this.observabilityLoaded) {
      this.loadObservability();
    }
  },

  applyAiCenterIntent(intent = {}, options = {}) {
    const nextState = {};
    if (intent.tab) {
      nextState.activeTab = intent.tab;
    }
    if (intent.workspace) {
      nextState.appWorkspaceTab = intent.workspace;
      if (!intent.tab) {
        nextState.activeTab = 'apps';
      }
    }
    if (intent.sentence) {
      nextState.appGrammarSentence = intent.sentence;
    }
    if (intent.question) {
      nextState.appGrammarQuestion = intent.question;
    }
    if (intent.query) {
      nextState.appConversationQuestion = intent.query;
      nextState.ragQuery = intent.query;
      nextState.retrievalOrchestratorQuery = intent.query;
    }
    if (!Object.keys(nextState).length) {
      return;
    }
    this.setData(nextState);
    if (!options.silent) {
      if (nextState.activeTab === 'apps' && !this.applicationsLoaded) {
        this.loadApplications();
      }
      if (nextState.activeTab === 'ops' && !this.observabilityLoaded) {
        this.loadObservability();
      }
      if (nextState.activeTab === 'rag') {
        this.refreshRagIndexStatus({ silent: true });
        this.startRagIndexPolling();
      }
    }
  },

  toggleCapabilityIntro() {
    this.setData({
      capabilityIntroCollapsed: !this.data.capabilityIntroCollapsed
    });
  },

  toggleModuleMaturity() {
    this.setData({
      moduleMaturityCollapsed: !this.data.moduleMaturityCollapsed
    });
  },

  syncRagIndexPolling() {
    const status = this.data.ragIndexStatus;
    if (this.data.activeTab === 'rag' && status && status.running) {
      this.startRagIndexPolling();
      return;
    }
    if (this.data.activeTab !== 'rag') {
      this.stopRagIndexPolling();
    }
  },

  startRagIndexPolling() {
    if (this.ragIndexPollingTimer) {
      return;
    }
    this.ragIndexPollingTimer = setInterval(() => {
      this.refreshRagIndexStatus({ silent: true });
    }, 5000);
  },

  stopRagIndexPolling() {
    if (this.ragIndexPollingTimer) {
      clearInterval(this.ragIndexPollingTimer);
      this.ragIndexPollingTimer = null;
    }
  },

  async refreshRagIndexStatus(options = {}) {
    const silent = !!options.silent;
    if (!silent) {
      this.setData({ ragIndexLoading: true });
    }
    try {
      const ragIndexStatus = await aiApi.getRagIndexStatus();
      this.setData({
        ragIndexStatus: normalizeRagIndexStatus(ragIndexStatus)
      });
      this.syncRagIndexPolling();
    } catch (error) {
      if (!silent) {
        wx.showToast({ title: (error.message || '刷新状态失败').slice(0, 20), icon: 'none' });
      }
    } finally {
      if (!silent) {
        this.setData({ ragIndexLoading: false });
      }
    }
  },

  async runWithLoading(flagName, task, failText) {
    this.setData({ [flagName]: true });
    try {
      await task();
    } catch (error) {
      wx.showToast({ title: (error.message || failText).slice(0, 20), icon: 'none' });
      throw error;
    } finally {
      this.setData({ [flagName]: false });
    }
  },

  buildStackShowcase(capabilities, mcpManifest) {
    const manifest = mcpManifest || {};
    const toolsCount = (manifest.tools || []).length;
    const promptsCount = (manifest.prompts || []).length;
    const resourcesCount = (manifest.resources || []).length;
    return [
      {
        title: 'Agent 编排',
        badge: capabilities && capabilities.langgraph_available ? 'LangGraph' : '本地编排',
        detail: capabilities && capabilities.langgraph_available
          ? '当前 Agent 工作流已使用 LangGraph StateGraph 兼容编排。'
          : '当前环境未启用 LangGraph 时，会自动回落到本地 pipeline。'
      },
      {
        title: '模型接入',
        badge: capabilities && capabilities.langchain_explicit_available ? 'LangChain LCEL' : '直连',
        detail: capabilities && capabilities.langchain_explicit_available
          ? '计划重排与检索编排已接入显式 LCEL、Output Parser 和本地 Trace。'
          : '当前页面保留模型能力入口，依赖不可用时会回退到 direct/pipeline。'
      },
      {
        title: '知识增强',
        badge: 'RAG',
        detail: capabilities && capabilities.rag_runtime && capabilities.rag_runtime.available
          ? '已接入结构化 RAG + Chroma 标准向量 RAG，并保留本地轻量回退链路。'
          : '当前仍可展示结构化 RAG 与本地轻量向量 RAG；安装 Chroma 依赖后可升级为标准向量检索。'
      },
      {
        title: '工具协议',
        badge: capabilities && capabilities.mcp_stdio_available ? 'MCP STDIO' : 'MCP 蓝图',
        detail: capabilities && capabilities.mcp_stdio_available
          ? `已抽象 ${toolsCount} 个工具、${resourcesCount} 个资源、${promptsCount} 个提示词，并支持独立 STDIO 服务。`
          : `已抽象 ${toolsCount} 个工具、${resourcesCount} 个资源、${promptsCount} 个提示词，HTTP 端可直接给小程序用。`
      },
      {
        title: '结果可解释',
        badge: '证据链',
        detail: 'AI 输出统一附带工作流、工具调用、检索命中、耗时、缓存等证据。'
      },
      {
        title: '长期记忆',
        badge: '记忆',
        detail: '学习教练和 Agent 会读取 AI 用户画像，结合薄弱点、偏好模式和近期重点词做个性化建议。'
      },
      {
        title: '评测回放',
        badge: '评测',
        detail: '内置 AI 评测用例、失败样本回放和运行记录，方便展示 tracing、质量回归与失败分析。'
      }
    ];
  },

  formatTraceLine(item) {
    return buildTraceLine(item);
  },

  handleRagQuery(event) {
    this.setData({ ragQuery: event.detail.value || '' });
  },

  handleVectorRagQuery(event) {
    this.setData({ vectorRagQuery: event.detail.value || '' });
  },

  handleVectorRagMode(event) {
    const mode = event.currentTarget.dataset.mode;
    if (!mode || mode === this.data.vectorRagMode) {
      return;
    }
    this.setData({ vectorRagMode: mode });
  },

  handleRagRecallKeywords(event) {
    this.setData({ ragRecallKeywords: event.detail.value || '' });
  },

  handleRagRecallSourceType(event) {
    this.setData({ ragRecallPreferredSourceType: event.currentTarget.dataset.sourceType || '' });
  },

  switchRagViewMode(event) {
    const mode = event.currentTarget.dataset.mode;
    if (!mode || mode === this.data.ragViewMode) {
      return;
    }
    this.setData({
      ragViewMode: mode,
      ragModeCards: buildRagModeCards(mode)
    });
  },

  loadPlanReplanner() {
    if (this.agentRequesting || this.data.agentLoading) {
      return;
    }
    this.agentRequesting = true;
    this.setData({ agentLoading: true });
    aiApi.replanStudyPlan({ trend_days: 7 })
      .then((data) => {
        this.setData({
          planReplanResult: normalizePlanReplanResult(data)
        });
      })
      .catch((error) => {
        wx.showToast({ title: ((error && error.message) || 'Agent 请求失败').slice(0, 20), icon: 'none' });
      })
      .finally(() => {
        this.agentRequesting = false;
        this.setData({ agentLoading: false });
      });
  },

  handleRetrievalOrchestratorQuery(event) {
    this.setData({ retrievalOrchestratorQuery: event.detail.value || '' });
  },

  runRetrievalOrchestrator() {
    if (this.data.retrievalOrchestratorLoading) {
      return;
    }
    const query = (this.data.retrievalOrchestratorQuery || '').trim();
    if (!query) {
      wx.showToast({ title: '请输入演示问题', icon: 'none' });
      return;
    }
    const requestPayload = { query, limit: 6 };
    this.setData({
      retrievalOrchestratorLoading: true,
      retrievalOrchestratorError: null
    });
    aiApi.runRetrievalOrchestrator(requestPayload)
      .then((data) => {
        this.setData({
          retrievalOrchestratorResult: normalizeRetrievalOrchestratorResult(data),
          retrievalOrchestratorError: null
        });
      })
      .catch((error) => {
        this.setData({
          retrievalOrchestratorError: buildErrorPanel(error, '检索编排执行失败', requestPayload)
        });
        wx.showToast({ title: ((error && error.message) || '编排执行失败').slice(0, 20), icon: 'none' });
      })
      .finally(() => {
        this.setData({ retrievalOrchestratorLoading: false });
      });
  },

  runMcpDemoTool() {
    if (this.mcpToolRunning || this.data.mcpLoading) {
      return;
    }
    this.mcpToolRunning = true;
    const toolName = this.data.mcpDemoTool;
    let args = {};
    try {
      args = this.data.mcpDemoToolArgsText ? JSON.parse(this.data.mcpDemoToolArgsText) : {};
    } catch (error) {
      this.mcpToolRunning = false;
      this.setData({
        mcpLoading: false,
        mcpDemoError: buildErrorPanel(
          { message: 'MCP 工具参数不是合法 JSON，请先修正后再运行。' },
          'MCP 工具调用失败',
          { tool_name: toolName, args: this.data.mcpDemoToolArgsText }
        )
      });
      wx.showToast({ title: '参数 JSON 无效', icon: 'none' });
      return;
    }
    const requestPayload = {
      tool_name: toolName,
      args
    };
    this.setData({
      mcpLoading: true,
      mcpDemoError: null,
      mcpDemoToolArgs: args
    });
    aiApi.callMcpTool(requestPayload)
      .then((mcpDemoResult) => {
        this.setData({
          mcpDemoResult: normalizeMcpDemoResult(mcpDemoResult),
          mcpDemoError: null
        });
      })
      .catch((error) => {
        this.setData({
          mcpDemoError: buildErrorPanel(error, 'MCP 工具调用失败', requestPayload)
        });
        wx.showToast({ title: ((error && error.message) || 'MCP 调用失败').slice(0, 20), icon: 'none' });
      })
      .finally(() => {
        this.mcpToolRunning = false;
        this.setData({ mcpLoading: false });
      });
  },

  handleMcpResourceUri(event) {
    this.setData({ mcpResourceUri: event.detail.value || '' });
  },

  handleMcpDemoToolSelect(event) {
    const toolName = event.currentTarget.dataset.tool;
    if (!toolName || toolName === this.data.mcpDemoTool) {
      return;
    }
    const mcpToolState = buildMcpToolState(this.data.mcpManifest, toolName);
    this.setData({
      mcpDemoTool: mcpToolState.selectedToolName,
      mcpDemoToolOptions: mcpToolState.options,
      mcpDemoToolSchema: mcpToolState.selectedTool ? (mcpToolState.selectedTool.input_schema || null) : null,
      mcpDemoToolSchemaHint: mcpToolState.schemaHint,
      mcpDemoToolSchemaFields: mcpToolState.schemaFields,
      mcpDemoToolArgs: mcpToolState.selectedArgs,
      mcpDemoToolArgsText: toPrettyJson(mcpToolState.selectedArgs),
      mcpDemoResult: null,
      mcpDemoError: null
    });
  },

  handleMcpResourceExampleSelect(event) {
    const resourceUri = event.currentTarget.dataset.uri;
    if (!resourceUri) {
      return;
    }
    const nextExamples = (this.data.mcpResourceExamples || []).map((item) => ({
      ...item,
      className: item.uri === resourceUri ? 'ai-choice active' : 'ai-choice'
    }));
    this.setData({
      mcpResourceUri: resourceUri,
      mcpResourceExamples: nextExamples,
      mcpResourceResult: null,
      mcpResourceError: null
    });
  },

  runMcpResourceDemo() {
    const resourceUri = (this.data.mcpResourceUri || '').trim();
    if (!resourceUri || this.data.mcpResourceLoading) {
      return;
    }
    const requestPayload = { resource_uri: resourceUri };
    this.setData({
      mcpResourceLoading: true,
      mcpResourceError: null
    });
    aiApi.readMcpResource(requestPayload)
      .then((result) => {
        this.setData({
          mcpResourceResult: normalizeMcpResourceResult(result),
          mcpResourceError: null
        });
      })
      .catch((error) => {
        this.setData({
          mcpResourceError: buildErrorPanel(error, 'MCP 资源读取失败', requestPayload)
        });
        wx.showToast({ title: ((error && error.message) || '资源读取失败').slice(0, 20), icon: 'none' });
      })
      .finally(() => {
        this.setData({ mcpResourceLoading: false });
      });
  },

  async applyReplannedPlan() {
    const patch = this.data.planReplanResult && this.data.planReplanResult.plan_patch;
    if (!patch || !patch.daily_target) {
      wx.showToast({ title: '当前没有可应用修改', icon: 'none' });
      return;
    }
    if (!this.data.currentPlan) {
      wx.showToast({ title: '请先创建学习计划', icon: 'none' });
      return;
    }
    this.setData({ planApplying: true });
    try {
      const updatedPlan = await plansApi.applyAiPlanPatch({
        patch,
        summary: this.data.planReplanResult.headline || 'apply ai patch',
        evidence: this.data.planReplanResult.evidence || {}
      });
      this.setData({
        currentPlan: updatedPlan || this.data.currentPlan
      });
      wx.showToast({ title: '学习计划已更新', icon: 'success' });
    } catch (error) {
      wx.showToast({ title: (error.message || '应用失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ planApplying: false });
    }
  },

  searchRag() {
    if (!this.data.ragQuery.trim()) {
      wx.showToast({ title: '请输入检索问题', icon: 'none' });
      return;
    }
    this.runWithLoading('ragSearchLoading', async () => {
      const ragResult = await aiApi.ragSearch({ query: this.data.ragQuery, limit: 6 });
      this.setData({ ragResult: normalizeRagResult(ragResult) });
    }, '检索失败');
  },

  searchVectorRag() {
    if (!this.data.vectorRagQuery.trim()) {
      wx.showToast({ title: '请输入向量问题', icon: 'none' });
      return;
    }
    this.runWithLoading('vectorRagLoading', async () => {
      const vectorRagResult = await aiApi.vectorRagSearch({
        query: this.data.vectorRagQuery,
        limit: 8,
        retrieval_mode: this.data.vectorRagMode
      });
      const nextRagRuntime = normalizeRagRuntime(
        (this.data.capabilities && this.data.capabilities.rag_runtime) || (vectorRagResult && vectorRagResult.retrieval_strategy)
      );
      this.setData({
        vectorRagResult: normalizeVectorRagResult(vectorRagResult),
        vectorDocPreview: normalizeVectorDocuments(vectorRagResult.documents),
        ragRuntime: nextRagRuntime,
        moduleMaturityPanels: buildModuleMaturityPanels(this.data.capabilities, nextRagRuntime, this.data.mcpManifest)
      });
      this.refreshRagIndexStatus({ silent: true });
    }, '向量检索失败');
  },

  syncRagIndexIncrementally() {
    if (this.data.ragSyncLoading) {
      return;
    }
    this.setData({ ragSyncLoading: true });
    aiApi.syncRagIndex({ batch_size: 64, delete_missing: false })
      .then((result) => {
        wx.showToast({ title: `同步 ${result.upserted_count || 0} 条`, icon: 'success' });
        this.refreshRagIndexStatus({ silent: true });
      })
      .catch((error) => {
        wx.showToast({ title: (error.message || '同步失败').slice(0, 20), icon: 'none' });
      })
      .finally(() => {
        this.setData({ ragSyncLoading: false });
      });
  },

  evaluateRagRecall() {
    const query = this.data.ragQuery.trim() || this.data.vectorRagQuery.trim();
    if (!query) {
      wx.showToast({ title: '请先输入问题', icon: 'none' });
      return;
    }
    const expectedKeywords = (this.data.ragRecallKeywords || '')
      .split(/[,，\s]+/)
      .map((item) => item.trim())
      .filter(Boolean);
    this.runWithLoading('ragRecallLoading', async () => {
      const ragRecallResult = await aiApi.evaluateRagRecall({
        query,
        expected_keywords: expectedKeywords,
        preferred_source_type: this.data.ragRecallPreferredSourceType,
        limit: 6
      });
      this.setData({ ragRecallResult: normalizeRagRecallResult(ragRecallResult) });
    }, '召回评测失败');
  },

  loadApplications() {
    return this.runWithLoading('appsLoading', async () => {
      const [grammarGuide, agentsBrief, quality, observability, scenarioTemplates, conversations] = await Promise.all([
        aiApi.getGrammarGuide(),
        aiApi.getAgentsBrief(),
        aiApi.getQuality(),
        aiApi.getObservability(),
        aiApi.getScenarioTemplates(),
        aiApi.listConversations({ limit: 10 })
      ]);
      this.setData({
        grammarGuide: normalizeLightFeatureResult(grammarGuide),
        agentsBrief: normalizeAgentsBrief(agentsBrief),
        quality: normalizeQuality(quality),
        observability: normalizeObservability(observability),
        appScenarioTemplates: normalizeScenarioTemplates((scenarioTemplates || {}).list),
        appConversationList: normalizeConversationList((conversations || {}).list)
      });
      this.applicationsLoaded = true;
    }, 'AI 应用加载失败');
  },

  loadObservability() {
    return this.runWithLoading('opsLoading', async () => {
      const [quality, observability, evaluationData] = await Promise.all([
        aiApi.getQuality(),
        aiApi.getObservability(),
        aiApi.getEvaluations({ limit: 8 })
      ]);
      this.setData({
        quality: normalizeQuality(quality),
        observability: normalizeObservability(observability),
        evaluationCases: evaluationData.cases || [],
        evaluationRuns: (evaluationData.runs || []).map(normalizeEvaluationRun),
        evaluationSummary: evaluationData.summary || null
      });
      this.observabilityLoaded = true;
    }, '观测加载失败');
  },

  refreshProfileMemory() {
    if (this.profileMemoryRefreshing || this.data.profileRefreshing) {
      return;
    }
    this.profileMemoryRefreshing = true;
    this.setData({ profileRefreshing: true });
    aiApi.refreshProfileMemory({ source: 'ai_center' })
      .then((profileMemory) => {
        this.setData({ profileMemory });
      })
      .catch((error) => {
        wx.showToast({ title: ((error && error.message) || '画像刷新失败').slice(0, 20), icon: 'none' });
      })
      .finally(() => {
        this.profileMemoryRefreshing = false;
        this.setData({ profileRefreshing: false });
      });
  },

  switchAppWorkspace(event) {
    const tab = event.currentTarget.dataset.tab;
    if (!tab || tab === this.data.appWorkspaceTab) {
      return;
    }
    this.setData({ appWorkspaceTab: tab });
  },

  handleMcpToolArgsInput(event) {
    const value = event.detail.value || '';
    let nextArgs = {};
    try {
      nextArgs = value ? JSON.parse(value) : {};
    } catch (error) {
      this.setData({ mcpDemoToolArgsText: value });
      return;
    }
    this.setData({
      mcpDemoToolArgs: nextArgs,
      mcpDemoToolArgsText: toPrettyJson(nextArgs)
    });
  },

  handleAppGrammarSentence(event) {
    this.setData({ appGrammarSentence: event.detail.value || '' });
  },

  handleAppGrammarQuestion(event) {
    this.setData({ appGrammarQuestion: event.detail.value || '' });
  },

  runGrammarTutor() {
    const sentence = (this.data.appGrammarSentence || '').trim();
    if (!sentence) {
      wx.showToast({ title: '请输入语法句子', icon: 'none' });
      return;
    }
    this.runWithLoading('appQueryLoading', async () => {
      const result = await aiApi.grammarTutor({
        sentence,
        question: (this.data.appGrammarQuestion || '').trim()
      });
      this.setData({
        appGrammarResult: normalizeLightFeatureResult(result)
      });
    }, '语法问答失败');
  },

  handleAppWritingTopic(event) {
    this.setData({ appWritingTopic: event.detail.value || '' });
  },

  handleAppWritingLevel(event) {
    this.setData({ appWritingLevel: event.currentTarget.dataset.value || 'cet4' });
  },

  handleAppWritingGenre(event) {
    this.setData({ appWritingGenre: event.currentTarget.dataset.value || 'essay' });
  },

  runWritingPrompt() {
    this.runWithLoading('appQueryLoading', async () => {
      const result = await aiApi.generateWritingPrompt({
        topic: (this.data.appWritingTopic || '').trim(),
        level: this.data.appWritingLevel,
        genre: this.data.appWritingGenre
      });
      this.setData({
        appWritingPromptResult: normalizeLightFeatureResult(result)
      });
    }, '写作题目生成失败');
  },

  handleAppWritingText(event) {
    this.setData({ appWritingText: event.detail.value || '' });
  },

  runWritingCorrect() {
    const text = (this.data.appWritingText || '').trim();
    if (!text) {
      wx.showToast({ title: '请输入待批改内容', icon: 'none' });
      return;
    }
    this.runWithLoading('appQueryLoading', async () => {
      const result = await aiApi.correctWriting({
        text,
        level: this.data.appWritingLevel
      });
      this.setData({
        appWritingCorrectResult: normalizeLightFeatureResult(result)
      });
    }, '写作批改失败');
  },

  handleAppTranslationSource(event) {
    this.setData({ appTranslationSource: event.detail.value || '' });
  },

  handleAppTranslationUserAnswer(event) {
    this.setData({ appTranslationUserAnswer: event.detail.value || '' });
  },

  runTranslationEvaluate() {
    const sourceText = (this.data.appTranslationSource || '').trim();
    if (!sourceText) {
      wx.showToast({ title: '请输入原文', icon: 'none' });
      return;
    }
    this.runWithLoading('appQueryLoading', async () => {
      const result = await aiApi.evaluateTranslation({
        source_text: sourceText,
        user_translation: (this.data.appTranslationUserAnswer || '').trim(),
        direction: 'auto'
      });
      this.setData({
        appTranslationResult: normalizeLightFeatureResult(result)
      });
    }, '翻译训练失败');
  },

  handleAppScenario(event) {
    this.setData({ appScenario: event.currentTarget.dataset.value || 'daily' });
  },

  handleAppScenarioMessage(event) {
    this.setData({ appScenarioMessage: event.detail.value || '' });
  },

  runScenarioDialogue() {
    const userMessage = (this.data.appScenarioMessage || '').trim();
    if (!userMessage) {
      wx.showToast({ title: '请输入对话内容', icon: 'none' });
      return;
    }
    this.runWithLoading('appQueryLoading', async () => {
      const result = await aiApi.scenarioDialogue({
        scenario: this.data.appScenario,
        user_message: userMessage
      });
      this.setData({
        appScenarioResult: normalizeLightFeatureResult(result),
        appConversationAnswer: normalizeLightFeatureResult(result)
      });
    }, '情景对话失败');
  },

  handleConversationFeatureType(event) {
    this.setData({ appConversationFeatureType: event.currentTarget.dataset.value || 'rag' });
  },

  handleConversationQuestion(event) {
    this.setData({ appConversationQuestion: event.detail.value || '' });
  },

  handleConversationFollowup(event) {
    this.setData({ appConversationFollowup: event.detail.value || '' });
  },

  async loadConversationDetailById(conversationId) {
    if (!conversationId) {
      return;
    }
    const detail = await aiApi.getConversationDetail(conversationId);
    this.setData({
      appConversationId: conversationId,
      appConversationDetail: normalizeConversationDetail(detail)
    });
  },

  selectConversation(event) {
    const conversationId = Number(event.currentTarget.dataset.id || 0);
    if (!conversationId) {
      return;
    }
    this.runWithLoading('appConversationLoading', async () => {
      await this.loadConversationDetailById(conversationId);
    }, '会话加载失败');
  },

  askConversation() {
    const question = (this.data.appConversationQuestion || '').trim();
    if (!question) {
      wx.showToast({ title: '请输入问题', icon: 'none' });
      return;
    }
    this.runWithLoading('appConversationLoading', async () => {
      const result = await aiApi.askConversation({
        feature_type: this.data.appConversationFeatureType,
        question
      });
      const answer = normalizeLightFeatureResult(result.answer || {});
      const conversation = result.conversation || {};
      this.setData({
        appConversationAnswer: answer,
        appConversationQuestion: '',
        appConversationId: conversation.id || 0
      });
      const conversations = await aiApi.listConversations({ limit: 10 });
      this.setData({
        appConversationList: normalizeConversationList((conversations || {}).list)
      });
      if (conversation.id) {
        await this.loadConversationDetailById(conversation.id);
      }
    }, '连续会话失败');
  },

  followupConversation() {
    const conversationId = Number(this.data.appConversationId || 0);
    const question = (this.data.appConversationFollowup || '').trim();
    if (!conversationId) {
      wx.showToast({ title: '请先发起一次会话', icon: 'none' });
      return;
    }
    if (!question) {
      wx.showToast({ title: '请输入追问内容', icon: 'none' });
      return;
    }
    this.runWithLoading('appConversationFollowupLoading', async () => {
      const result = await aiApi.askConversation({
        conversation_id: conversationId,
        feature_type: this.data.appConversationFeatureType,
        question
      });
      this.setData({
        appConversationAnswer: normalizeLightFeatureResult(result.answer || {}),
        appConversationFollowup: ''
      });
      await this.loadConversationDetailById(conversationId);
    }, '追问失败');
  },

  loadEvaluationRunDetail(event) {
    const runId = Number(event.currentTarget.dataset.runId || 0);
    if (!runId) {
      return;
    }
    this.runWithLoading('evaluationRunDetailLoading', async () => {
      const result = await aiApi.getEvaluationRunDetail(runId);
      this.setData({
        selectedEvaluationRun: runId,
        evaluationRunDetail: normalizeEvaluationRun(result)
      });
    }, '评测详情加载失败');
  },

  replaySingleEvaluationRun(event) {
    const runId = Number(event.currentTarget.dataset.runId || this.data.selectedEvaluationRun || 0);
    if (!runId) {
      return;
    }
    this.runWithLoading('evaluationReplayLoading', async () => {
      const replayRun = await aiApi.replayEvaluationRun(runId, {});
      const evaluationData = await aiApi.getEvaluations({ limit: 8 });
      this.setData({
        evaluationRuns: (evaluationData.runs || []).map(normalizeEvaluationRun),
        evaluationSummary: evaluationData.summary || null,
        selectedEvaluationRun: replayRun.id,
        evaluationRunDetail: normalizeEvaluationRun(replayRun)
      });
      wx.showToast({ title: '单条回放完成', icon: 'success' });
    }, '单条回放失败');
  },

  runEvaluations() {
    this.setData({ evaluationRunning: true });
    aiApi.runEvaluations({ limit: 3 })
      .then(() => aiApi.getEvaluations({ limit: 8 }))
      .then((evaluationData) => {
        this.setData({
          evaluationCases: evaluationData.cases || [],
          evaluationRuns: (evaluationData.runs || []).map(normalizeEvaluationRun),
          evaluationSummary: evaluationData.summary || null
        });
        wx.showToast({ title: '评测完成', icon: 'success' });
      })
      .catch((error) => {
        wx.showToast({ title: (error.message || '评测失败').slice(0, 20), icon: 'none' });
      })
      .finally(() => {
        this.setData({ evaluationRunning: false });
      });
  },

  replayFailedEvaluations() {
    if (this.data.evaluationRunning) {
      return;
    }
    this.setData({ evaluationRunning: true });
    aiApi.runEvaluations({ replay_failed_only: true, limit: 5 })
      .then(() => aiApi.getEvaluations({ limit: 8 }))
      .then((evaluationData) => {
        this.setData({
          evaluationCases: evaluationData.cases || [],
          evaluationRuns: (evaluationData.runs || []).map(normalizeEvaluationRun),
          evaluationSummary: evaluationData.summary || null
        });
        wx.showToast({ title: '失败样本已重放', icon: 'success' });
      })
      .catch((error) => {
        wx.showToast({ title: (error.message || '重放失败').slice(0, 20), icon: 'none' });
      })
      .finally(() => {
        this.setData({ evaluationRunning: false });
      });
  }
}));
