<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import AiRuntimePanel from '../components/AiRuntimePanel.vue';
import PageSection from '../components/PageSection.vue';
import {
  askConversation,
  approveAiRun,
  callMcpTool,
  cancelAiRun,
  getAiRun,
  getAiRunArtifacts,
  getAiRunSteps,
  getCapabilities,
  getConversationDetail,
  getConversations,
  getMcpManifest,
  getRagIndexStatus,
  resumeAiRun,
  retryAiRun,
  vectorRagSearch,
} from '../services/ai';

const TOOL_CATEGORY_ORDER = ['学习计划', '词汇/语法', 'RAG 问答', '写作/场景', '系统观测'];

const capabilities = ref(null);
const manifest = ref(null);
const ragIndexStatus = ref(null);

const ragQuery = ref('');
const ragResult = ref(null);
const ragLoading = ref(false);
const ragError = ref('');
const ragChatHistory = ref([]);
const conversationQuestion = ref('');
const conversationFollowup = ref('');
const conversationRoute = ref('rag');
const conversationAnswer = ref(null);
const conversationRuntime = ref(null);
const conversationList = ref([]);
const conversationDetail = ref(null);
const conversationId = ref(0);
const conversationLoading = ref(false);
const conversationFollowupLoading = ref(false);

const selectedTool = ref('');
const toolForm = ref({});
const toolFieldErrors = ref({});
const mcpResult = ref(null);
const mcpError = ref('');
const mcpLoading = ref(false);
const activeRuntime = ref(null);
const activeRuntimeSteps = ref([]);
const activeRuntimeArtifacts = ref([]);
const runtimeLoading = ref(false);
let runtimePollTimer = null;

const tools = computed(() => manifest.value?.tools || []);
const selectedToolMeta = computed(() => tools.value.find((tool) => tool.name === selectedTool.value) || null);
const ragSourcePills = computed(() => ragResult.value?.source_pills || []);
const ragBrief = computed(() => ragResult.value?.answer_brief || ragResult.value?.answer || null);

const capabilityItems = computed(() => {
  const status = ragIndexStatus.value || {};
  const ragRuntime = capabilities.value?.rag_runtime || {};
  const ragBackend = status.active_retrieval_backend || ragRuntime.active_retrieval_backend || ragRuntime.backend || 'unknown';
  return [
    {
      label: 'AI 模型',
      value: capabilities.value?.ai_model_env_ready ? '已就绪' : '未配置',
      description: '网页端直接复用后端当前模型配置。',
    },
    {
      label: 'MCP 技能',
      value: capabilities.value?.mcp_available ? '可直接使用' : '暂不可用',
      description: '常用技能会以中文卡片和表单展示。',
    },
    {
      label: '严格 Runtime',
      value: capabilities.value?.worker_healthy ? '健康' : '不健康',
      description: capabilities.value?.degraded_reason || 'queued feature 需要 Redis + Celery Worker。',
    },
    {
      label: '自动恢复',
      value: capabilities.value?.auto_recover_enabled ? '已开启' : '未开启',
      description: `stale run ${capabilities.value?.stale_run_count || 0} 个，周期 ${capabilities.value?.auto_recover_every_seconds || 0}s`,
    },
    {
      label: 'RAG 索引',
      value: status.collection_health || status.runtime_state || status.state || 'unknown',
      description: status.runtime_degraded_reason
        ? `${status.runtime_degraded_reason} 当前后端：${ragBackend}`
        : (status.chunk_count ? `当前 ${status.chunk_count} 个知识块，后端：${ragBackend}` : '知识库状态加载中'),
    },
    {
      label: '多步编排',
      value: capabilities.value?.langgraph_available ? '已接入' : '未启用',
      description: '复杂链路仍由后端统一编排。',
    },
  ];
});

const ragStatusSummary = computed(() => {
  const status = ragIndexStatus.value || {};
  const runtime = capabilities.value?.rag_runtime || {};
  const backend = status.active_retrieval_backend || runtime.active_retrieval_backend || runtime.backend || 'unknown';
  if (status.runtime_degraded_reason) {
    return `${status.state || 'unknown'} · ${backend} · ${status.runtime_degraded_reason}`;
  }
  if (status.collection_health || status.runtime_state) {
    return `${status.collection_health || 'unknown'} · ${status.runtime_state || status.state || 'unknown'} · ${backend}`;
  }
  return `${backend}`;
});

const groupedTools = computed(() => {
  const groups = [];
  const bucket = new Map();

  TOOL_CATEGORY_ORDER.forEach((title) => {
    bucket.set(title, []);
  });

  tools.value.forEach((tool) => {
    const title = TOOL_CATEGORY_ORDER.includes(tool.category) ? tool.category : '其他技能';
    if (!bucket.has(title)) {
      bucket.set(title, []);
    }
    bucket.get(title).push(tool);
  });

  bucket.forEach((value, key) => {
    if (value.length) {
      groups.push({
        title: key,
        tools: value.sort((a, b) => Number(a.ui_order || 999) - Number(b.ui_order || 999)),
      });
    }
  });

  return groups;
});

const fieldDefinitions = computed(() => {
  const schema = selectedToolMeta.value?.input_schema || {};
  const props = schema.properties || {};
  const required = new Set(schema.required || []);

  return Object.entries(props).map(([name, field]) => ({
    name,
    type: field.type || 'string',
    required: required.has(name),
    enum: Array.isArray(field.enum) ? field.enum : [],
    itemsType: field.items?.type || '',
    title: field.title || prettyFieldLabel(name),
    description: field.description || '',
    exampleValue: selectedToolMeta.value?.example_args?.[name],
    defaultValue: field.default,
  }));
});

const mcpResultView = computed(() => summarizeMcpResult(selectedToolMeta.value, mcpResult.value?.result || mcpResult.value));

async function loadRuntime(runId) {
  if (!runId) {
    activeRuntime.value = null;
    activeRuntimeSteps.value = [];
    activeRuntimeArtifacts.value = [];
    return null;
  }
  runtimeLoading.value = true;
  try {
    const [run, steps, artifacts] = await Promise.all([
      getAiRun(runId),
      getAiRunSteps(runId),
      getAiRunArtifacts(runId),
    ]);
    activeRuntime.value = run;
    activeRuntimeSteps.value = steps?.steps || [];
    activeRuntimeArtifacts.value = artifacts?.artifacts || [];
    return run;
  } finally {
    runtimeLoading.value = false;
  }
}

function stopRuntimePolling() {
  if (runtimePollTimer) {
    window.clearTimeout(runtimePollTimer);
    runtimePollTimer = null;
  }
}

async function pollRuntimeUntilSettled(runId, handlers = {}) {
  if (!runId) {
    return null;
  }
  stopRuntimePolling();
  const run = await loadRuntime(runId);
  if (!run) {
    return null;
  }
  if (run.status === 'succeeded') {
    await handlers.onSuccess?.(run);
    return run;
  }
  if (run.status === 'failed' || run.status === 'cancelled') {
    await handlers.onFailure?.(run);
    return run;
  }
  if (run.status === 'waiting_approval') {
    await handlers.onWaitingApproval?.(run);
    return run;
  }
  runtimePollTimer = window.setTimeout(() => {
    pollRuntimeUntilSettled(runId, handlers).catch((error) => {
      ragError.value = error.message || '运行态轮询失败';
    });
  }, 1500);
  return run;
}

async function handleRuntimeAction(action) {
  const runId = activeRuntime.value?.run_id;
  if (!runId) {
    return;
  }
  runtimeLoading.value = true;
  try {
    if (action === 'retry') {
      await retryAiRun(runId, {});
    } else if (action === 'resume') {
      await resumeAiRun(runId, {});
    } else if (action === 'cancel') {
      await cancelAiRun(runId, {});
    } else if (action === 'approve') {
      await approveAiRun(runId, { approved: true, note: 'web approve' });
    } else if (action === 'reject') {
      await approveAiRun(runId, { approved: false, note: 'web reject' });
    }
    await loadRuntime(runId);
  } catch (error) {
    mcpError.value = error.message || '运行态操作失败';
  } finally {
    runtimeLoading.value = false;
  }
}

function prettyFieldLabel(name) {
  const mapping = {
    keyword: '关键词',
    query: '问题内容',
    limit: '返回数量',
    word_id: '单词 ID',
    sentence_id: '句子 ID',
    retrieval_mode: '检索模式',
    expected_keywords: '期望关键词',
    preferred_source_type: '优先来源类型',
    report_type: '报告类型',
    include_compare: '包含对比',
    trend_days: '趋势天数',
    days: '统计天数',
    batch_size: '批次大小',
    delete_missing: '删除失效块',
    level: '难度等级',
    topic: '主题',
    genre: '文体',
  };
  return mapping[name] || name.replace(/_/g, ' ');
}

function buildFieldHint(field) {
  if (field.description) {
    return field.description;
  }
  if (field.enum.length) {
    return `可选：${field.enum.join(' / ')}`;
  }
  if (field.type === 'array' && field.itemsType === 'string') {
    return '支持换行或逗号分隔，每项会自动整理成数组。';
  }
  if (field.type === 'integer') {
    return '请输入整数。';
  }
  if (field.type === 'boolean') {
    return '开启或关闭这个选项。';
  }
  return '按当前技能需要填写即可。';
}

function getToolStatus(tool) {
  if (!capabilities.value?.mcp_available) {
    return '暂不可用';
  }
  const count = Object.keys(tool.input_schema?.properties || {}).length;
  return count ? '需填写参数' : '可直接使用';
}

function initializeToolForm(tool) {
  const nextForm = {};
  const props = tool?.input_schema?.properties || {};
  const exampleArgs = tool?.example_args || {};

  Object.entries(props).forEach(([name, field]) => {
    const seeded = exampleArgs[name] ?? field.default;
    if (field.type === 'boolean') {
      nextForm[name] = Boolean(seeded);
      return;
    }
    if (field.type === 'array' && field.items?.type === 'string') {
      nextForm[name] = Array.isArray(seeded) ? seeded.join('\n') : '';
      return;
    }
    if (seeded === 0) {
      nextForm[name] = 0;
      return;
    }
    nextForm[name] = seeded ?? '';
  });

  toolForm.value = nextForm;
  toolFieldErrors.value = {};
  mcpError.value = '';
}

function applyExampleArgs() {
  if (!selectedToolMeta.value) {
    return;
  }
  initializeToolForm(selectedToolMeta.value);
}

function normalizeStringArray(value) {
  return String(value || '')
    .split(/[\n,，]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildToolArgs() {
  const nextArgs = {};
  const errors = {};

  fieldDefinitions.value.forEach((field) => {
    const rawValue = toolForm.value[field.name];

    if (field.type === 'boolean') {
      nextArgs[field.name] = Boolean(rawValue);
      return;
    }

    if (field.type === 'array' && field.itemsType === 'string') {
      const parsed = normalizeStringArray(rawValue);
      if (field.required && !parsed.length) {
        errors[field.name] = '请至少填写一项内容。';
        return;
      }
      if (parsed.length) {
        nextArgs[field.name] = parsed;
      }
      return;
    }

    const textValue = String(rawValue ?? '').trim();
    if (!textValue) {
      if (field.required) {
        errors[field.name] = '这个字段是必填项。';
      }
      return;
    }

    if (field.type === 'integer') {
      const parsed = Number(textValue);
      if (!Number.isInteger(parsed)) {
        errors[field.name] = '请输入整数。';
        return;
      }
      nextArgs[field.name] = parsed;
      return;
    }

    nextArgs[field.name] = textValue;
  });

  toolFieldErrors.value = errors;
  return {
    valid: !Object.keys(errors).length,
    args: nextArgs,
  };
}

function summarizeGenericItem(item) {
  if (!item || typeof item !== 'object') {
    return {
      title: String(item ?? ''),
      subtitle: '',
      meta: '',
    };
  }

  const title = item.word || item.title || item.name || item.label || item.stem || `ID ${item.id || '--'}`;
  const subtitle = item.meaning_cn || item.summary || item.description || item.translation_cn || item.preview || '';
  const metaParts = [];

  if (item.part_of_speech) {
    metaParts.push(item.part_of_speech);
  }
  if (item.book?.name) {
    metaParts.push(item.book.name);
  }
  if (item.category) {
    metaParts.push(item.category);
  }
  if (item.difficulty_label) {
    metaParts.push(item.difficulty_label);
  }

  return {
    title,
    subtitle,
    meta: metaParts.join(' · '),
  };
}

function normalizeConversationDetail(source = {}) {
  return {
    ...source,
    latest_runtime_run: source.latest_runtime_run || null,
    messages: Array.isArray(source.messages) ? source.messages : [],
  };
}

async function refreshConversationList() {
  const payload = await getConversations({ limit: 10 });
  conversationList.value = payload?.list || [];
}

async function loadConversationDetailView(conversationPk) {
  if (!conversationPk) {
    conversationDetail.value = null;
    return;
  }
  const detail = await getConversationDetail(conversationPk);
  conversationDetail.value = normalizeConversationDetail(detail);
  if (detail?.latest_runtime_run?.run_id) {
    await loadRuntime(detail.latest_runtime_run.run_id);
  }
}

async function handleAskConversation() {
  const question = String(conversationQuestion.value || '').trim();
  if (!question) {
    ragError.value = '先输入一个问题，再开始连续会话。';
    return;
  }
  conversationLoading.value = true;
  ragError.value = '';
  try {
    const result = await askConversation({
      feature_type: conversationRoute.value,
      question,
    });
    conversationAnswer.value = result.answer || null;
    conversationRuntime.value = result.runtime_run || result || null;
    conversationId.value = result.conversation?.id || conversationId.value || 0;
    conversationQuestion.value = '';
    if (result.run_id) {
      await pollRuntimeUntilSettled(result.run_id, {
        onSuccess: async () => {
          if (conversationId.value) {
            await loadConversationDetailView(conversationId.value);
          }
          await refreshConversationList();
        },
      });
    }
    await refreshConversationList();
    if (conversationId.value) {
      await loadConversationDetailView(conversationId.value);
    }
  } catch (error) {
    ragError.value = error.message || '连续会话失败';
  } finally {
    conversationLoading.value = false;
  }
}

async function handleConversationFollowup() {
  const question = String(conversationFollowup.value || '').trim();
  if (!conversationId.value || !question) {
    ragError.value = '先选中会话并输入追问内容。';
    return;
  }
  conversationFollowupLoading.value = true;
  ragError.value = '';
  try {
    const result = await askConversation({
      conversation_id: conversationId.value,
      feature_type: conversationRoute.value,
      question,
    });
    conversationAnswer.value = result.answer || null;
    conversationRuntime.value = result.runtime_run || result || null;
    conversationFollowup.value = '';
    if (result.run_id) {
      await pollRuntimeUntilSettled(result.run_id, {
        onSuccess: async () => {
          await loadConversationDetailView(conversationId.value);
          await refreshConversationList();
        },
      });
    }
    await loadConversationDetailView(conversationId.value);
    await refreshConversationList();
  } catch (error) {
    ragError.value = error.message || '追问失败';
  } finally {
    conversationFollowupLoading.value = false;
  }
}

async function handleSelectConversation(id) {
  conversationId.value = id;
  await loadConversationDetailView(id);
}

function summarizeMcpResult(tool, payload) {
  if (!payload) {
    return null;
  }

  const toolName = tool?.name || '';

  if (toolName === 'get_today_task') {
    return {
      title: '今日学习任务',
      summary: payload.plan?.book?.name
        ? `当前计划词书：${payload.plan.book.name}`
        : '当前还没有学习计划，可以先去词书页或计划页设置。',
      metrics: [
        { label: '今日新词剩余', value: payload.summary?.new_words_remaining ?? 0 },
        { label: '今日复习剩余', value: payload.summary?.review_words_remaining ?? 0 },
        { label: '错词数量', value: payload.summary?.wrong_words ?? 0 },
        { label: '今日目标', value: payload.task?.new_word_target ?? payload.plan?.daily_target ?? 0 },
      ],
      items: payload.adaptive
        ? [
            {
              title: payload.adaptive.mode_label || '个性化建议',
              subtitle: payload.adaptive.focus_tip || '系统会结合当前学习状态动态调节今日节奏。',
              meta: `建议新词 ${payload.adaptive.recommended_new_word_target || 0} · 建议复习 ${payload.adaptive.recommended_review_word_target || 0}`,
            },
          ]
        : [],
      raw: payload,
    };
  }

  if (toolName === 'vector_rag_search' || toolName === 'rag_search') {
    const answerBrief = payload.answer_brief || payload.answer || {};
    return {
      title: 'RAG 问答结果',
      summary: answerBrief.summary || payload.answer?.summary || '已生成回答。',
      items: (answerBrief.points || []).map((point, index) => ({
        title: `要点 ${index + 1}`,
        subtitle: point,
        meta: '',
      })),
      followups: answerBrief.next_questions || [],
      raw: payload,
    };
  }

  if (Array.isArray(payload.list)) {
    return {
      title: `${tool?.display_name || '技能结果'} · ${payload.list.length} 条`,
      summary: tool?.summary || tool?.description || '已拿到当前技能的查询结果。',
      items: payload.list.map(summarizeGenericItem),
      raw: payload,
    };
  }

  if (Array.isArray(payload.recommended_points)) {
    return {
      title: payload.headline || tool?.display_name || '结果',
      summary: payload.summary || '',
      items: payload.recommended_points.map((item) => ({
        title: item.title,
        subtitle: item.reason || item.learning_tip || item.sample_sentence || '',
        meta: [item.category, item.difficulty_label].filter(Boolean).join(' · '),
      })),
      raw: payload,
    };
  }

  if (payload.word || payload.title || payload.summary) {
    return {
      title: payload.word || payload.title || tool?.display_name || '技能结果',
      summary: payload.meaning_cn || payload.summary || payload.description || '',
      items: payload.example_sentence
        ? [
            {
              title: '示例',
              subtitle: payload.example_sentence,
              meta: payload.example_translation || '',
            },
          ]
        : [],
      raw: payload,
    };
  }

  return {
    title: tool?.display_name || tool?.name || '技能结果',
    summary: '已经成功返回结果，原始内容保留在高级区。',
    metrics: Object.entries(payload)
      .filter(([, value]) => typeof value === 'number' || typeof value === 'string')
      .slice(0, 4)
      .map(([label, value]) => ({
        label: prettyFieldLabel(label),
        value,
      })),
    raw: payload,
  };
}

async function loadPage() {
  const [caps, mcpManifest, ragStatus, conversations] = await Promise.all([
    getCapabilities().catch(() => null),
    getMcpManifest().catch(() => null),
    getRagIndexStatus().catch(() => null),
    getConversations({ limit: 10 }).catch(() => ({ list: [] })),
  ]);

  capabilities.value = caps;
  manifest.value = mcpManifest;
  ragIndexStatus.value = ragStatus;
  conversationList.value = conversations?.list || [];

  if (!selectedTool.value && mcpManifest?.tools?.length) {
    selectedTool.value = mcpManifest.tools[0].name;
  }
}

async function handleRagSearch() {
  const query = String(ragQuery.value || '').trim();
  if (!query) {
    ragError.value = '先输入一个问题，再开始问资料。';
    return;
  }

  ragLoading.value = true;
  ragError.value = '';
  ragChatHistory.value.push({ role: 'user', content: query });

  try {
    const result = await vectorRagSearch({
      query,
      retrieval_mode: 'hybrid',
      limit: 6,
    });
    ragResult.value = result;
    if (result.run_id) {
      await pollRuntimeUntilSettled(result.run_id, {
        onSuccess: async (run) => {
          const payload = run.result || result;
          ragResult.value = payload;
          ragChatHistory.value.push({
            role: 'assistant',
            content: payload.answer_brief?.summary || payload.answer?.summary || 'AI 已返回结果。',
          });
        },
        onWaitingApproval: async () => {
          ragChatHistory.value.push({
            role: 'assistant',
            content: '当前任务正在等待审批后继续执行。',
          });
        },
      });
    } else {
      ragChatHistory.value.push({
        role: 'assistant',
        content: result.answer_brief?.summary || result.answer?.summary || 'AI 已返回结果。',
      });
    }
    ragQuery.value = '';
  } catch (error) {
    ragError.value = error.message || 'RAG 查询失败';
  } finally {
    ragLoading.value = false;
  }
}

function handleUseFollowup(text) {
  ragQuery.value = text;
}

function handleSelectTool(toolName) {
  selectedTool.value = toolName;
}

async function handleCallTool() {
  if (!selectedTool.value) {
    return;
  }

  const built = buildToolArgs();
  if (!built.valid) {
    mcpError.value = '请先把必填项和字段格式补正确。';
    return;
  }

  mcpLoading.value = true;
  mcpError.value = '';
  mcpResult.value = null;

  try {
    mcpResult.value = await callMcpTool({
      tool_name: selectedTool.value,
      args: built.args,
    });
    if (mcpResult.value?.run_id) {
      await loadRuntime(mcpResult.value.run_id);
    }
    if (mcpResult.value?.result?.status === 'pending_approval') {
      mcpError.value = '该技能需要审批，已挂起等待确认。';
    }
  } catch (error) {
    mcpError.value = error.message || 'MCP 调用失败';
  } finally {
    mcpLoading.value = false;
  }
}

watch(selectedToolMeta, (tool) => {
  if (tool) {
    initializeToolForm(tool);
  }
});

onMounted(loadPage);
onBeforeUnmount(stopRuntimePolling);
</script>

<template>
  <div class="page-stack">
    <PageSection tone="hero">
      <div class="hero-wrap">
        <div>
          <div class="hero-kicker">AI Study Space</div>
          <div class="hero-title">先拿结果，再在需要时展开依据和高级信息。</div>
          <div class="hero-copy">
            网页端沿用你已经确认过的产品方向：RAG 默认聊天式问答，MCP 默认技能卡 + 参数表单，技术细节不再占据首屏。
          </div>
        </div>
        <div class="hero-side-stack">
          <div class="chip-row compact">
            <span class="chip-light dark">{{ capabilities?.mcp_available ? 'MCP 可用' : 'MCP 降级' }}</span>
            <span class="chip-light dark">{{ capabilities?.langgraph_available ? '编排已接入' : '仅直接链路' }}</span>
            <span class="chip-light dark">RAG {{ ragStatusSummary }}</span>
            <span class="chip-light dark">{{ capabilities?.worker_healthy ? 'Runtime 健康' : 'Runtime 不健康' }}</span>
            <span class="chip-light dark">{{ capabilities?.auto_recover_enabled ? '自动恢复已开启' : '自动恢复未开启' }}</span>
          </div>
          <div class="info-grid compact-grid">
            <article v-for="item in capabilityItems" :key="item.label" class="info-card glass-card">
              <div class="info-label">{{ item.label }}</div>
              <div class="info-value">{{ item.value }}</div>
              <div class="info-description">{{ item.description }}</div>
            </article>
          </div>
        </div>
      </div>
    </PageSection>

    <PageSection title="连续会话" subtitle="统一会话 Agent 会把路由、上下文记忆和真实运行态绑到同一轮对话里。">
      <div v-if="capabilities?.strict_runtime && !capabilities?.worker_healthy" class="notice error">
        {{ capabilities?.degraded_reason || '标准 Agent 运行时不可用。' }}
      </div>
      <details v-if="capabilities" class="details-box">
        <summary>查看 Runtime 健康详情</summary>
        <div class="list-stack details-stack">
          <div class="list-line">
            <strong>在线 Worker</strong>
            <span class="line-meta">{{ capabilities.workers?.join('，') || '当前未探测到在线 worker' }}</span>
          </div>
          <div class="list-line">
            <strong>观测到的队列</strong>
            <span class="line-meta">{{ capabilities.observed_queues?.join('，') || '尚未探测到队列' }}</span>
          </div>
          <div class="list-line">
            <strong>自动恢复</strong>
            <span class="line-meta">每 {{ capabilities.auto_recover_every_seconds || 0 }} 秒最多恢复 {{ capabilities.auto_recover_limit || 0 }} 个 stale run</span>
          </div>
          <div class="list-line">
            <strong>当前 stale run</strong>
            <span class="line-meta">{{ capabilities.stale_run_count || 0 }}</span>
          </div>
        </div>
      </details>

      <div class="chip-row compact">
        <button v-for="item in ['rag', 'grammar', 'writing', 'translation']" :key="item" class="ghost-button small" :class="{ primary: conversationRoute === item }" type="button" @click="conversationRoute = item">
          {{ item }}
        </button>
      </div>

      <textarea v-model="conversationQuestion" class="text-area" rows="4" placeholder="先发起一次会话，例如：important 和 significant 怎么区分？" />
      <div class="button-row">
        <button class="primary-button" type="button" :disabled="conversationLoading" @click="handleAskConversation">
          {{ conversationLoading ? '会话中...' : '发起会话' }}
        </button>
      </div>

      <div v-if="conversationAnswer" class="result-card">
        <div class="action-card-title">{{ conversationAnswer.headline || '本轮回答' }}</div>
        <div class="action-card-description">{{ conversationAnswer.summary || conversationAnswer.answer?.summary || 'AI 已返回结果。' }}</div>
        <div v-if="conversationRuntime?.runtime_summary?.summary" class="soft-caption">{{ conversationRuntime.runtime_summary.summary }}</div>
      </div>

      <div v-if="conversationId" class="result-card">
        <div class="action-card-title">继续追问</div>
        <textarea v-model="conversationFollowup" class="text-area" rows="3" placeholder="例如：再给我一个更好记的例句。" />
        <div class="button-row">
          <button class="ghost-button primary" type="button" :disabled="conversationFollowupLoading" @click="handleConversationFollowup">
            {{ conversationFollowupLoading ? '追问中...' : '发送追问' }}
          </button>
        </div>
      </div>

      <div class="info-grid compact-grid">
        <article class="info-card">
          <div class="info-label">最近会话</div>
          <div v-if="!conversationList.length" class="info-description">还没有会话记录，先发起一次对话。</div>
          <div v-for="item in conversationList" :key="item.id" class="list-line">
            <button class="ghost-button small" type="button" @click="handleSelectConversation(item.id)">{{ item.title || `会话 ${item.id}` }}</button>
            <span class="line-meta">{{ item.feature_type }} · {{ item.updated_at || item.created_at || '' }}</span>
          </div>
        </article>
        <article class="info-card">
          <div class="info-label">会话详情</div>
          <div v-if="!conversationDetail" class="info-description">选中一条会话后，这里会展开完整消息历史。</div>
          <template v-else>
            <div class="soft-caption">{{ conversationDetail.title }} · {{ conversationDetail.messages?.length || 0 }} 条消息</div>
            <div v-if="conversationDetail.latest_runtime_run?.run_id" class="soft-caption">
              最近运行：{{ conversationDetail.latest_runtime_run.runtime_summary?.status_text || conversationDetail.latest_runtime_run.status }}
            </div>
            <div v-for="item in conversationDetail.messages" :key="item.id" class="list-line">
              <strong>{{ item.role }}</strong>
              <span class="line-meta">{{ item.content }}</span>
            </div>
          </template>
        </article>
      </div>

      <AiRuntimePanel
        v-if="activeRuntime && activeRuntime.feature_type === 'conversation'"
        :runtime="activeRuntime"
        :health="capabilities"
        :steps="activeRuntimeSteps"
        :artifacts="activeRuntimeArtifacts"
        :loading="runtimeLoading"
        @refresh="activeRuntime.run_id ? loadRuntime(activeRuntime.run_id) : null"
        @retry="handleRuntimeAction('retry')"
        @resume="handleRuntimeAction('resume')"
        @cancel="handleRuntimeAction('cancel')"
        @approve="handleRuntimeAction('approve')"
        @reject="handleRuntimeAction('reject')"
      />
    </PageSection>

    <PageSection title="RAG 问答" subtitle="像聊天一样提问。默认先给你直接答案，来源和检索过程按需展开。">
      <div class="rag-chat-shell">
        <div v-if="!ragChatHistory.length" class="empty-state">
          直接输入问题就可以开始，例如：`important 和 significant 怎么区分？`
        </div>
        <div v-for="(message, index) in ragChatHistory" :key="`${message.role}-${index}`" class="chat-bubble" :class="message.role">
          <div class="chat-role">{{ message.role === 'user' ? '你' : 'AI' }}</div>
          <div class="chat-content">{{ message.content }}</div>
        </div>
      </div>

      <div class="toolbar-grid">
        <input v-model="ragQuery" class="text-input span-2" placeholder="例如：important 和 significant 怎么区分？" />
        <button class="primary-button" type="button" :disabled="ragLoading" @click="handleRagSearch">
          {{ ragLoading ? '查询中...' : '发送问题' }}
        </button>
      </div>

      <div v-if="ragError" class="notice error">{{ ragError }}</div>

      <div v-if="ragResult" class="rag-answer-card">
        <div class="chip-row compact">
          <span class="chip-light">默认已收起检索过程</span>
          <span class="chip-light">主链路：Hybrid</span>
        </div>
        <div class="rag-answer-title">{{ ragBrief?.summary || 'AI 回答' }}</div>
        <div class="rag-answer-copy">这次回答默认走 `hybrid` 检索，普通模式只保留直接答案和继续追问建议。</div>

        <div v-if="ragBrief?.points?.length" class="list-stack">
          <div v-for="(point, index) in ragBrief.points" :key="`${index}-${point}`" class="list-line">
            <strong>要点 {{ index + 1 }}</strong>
            <span class="line-meta">{{ point }}</span>
          </div>
        </div>

        <div v-if="ragSourcePills.length" class="chip-row">
          <span v-for="item in ragSourcePills" :key="`${item.label}-${item.source_type || ''}`" class="chip-light">
            {{ item.label || item.title || item.value || item }}
          </span>
        </div>

        <div v-if="ragBrief?.next_questions?.length" class="button-row wrap">
          <button
            v-for="item in ragBrief.next_questions.slice(0, 3)"
            :key="item"
            class="ghost-button small"
            type="button"
            @click="handleUseFollowup(item)"
          >
            {{ item }}
          </button>
        </div>

        <details class="details-box">
          <summary>查看依据</summary>
          <div v-if="ragResult.documents?.length" class="list-stack details-stack">
            <div v-for="doc in ragResult.documents.slice(0, 6)" :key="`${doc.source_type}-${doc.source_id}`" class="list-line">
              <strong>{{ doc.title || doc.source_type || '来源片段' }}</strong>
              <span class="line-meta">{{ doc.content_preview || doc.content || '' }}</span>
            </div>
          </div>
          <pre class="pre-block">{{ JSON.stringify(ragResult.advanced_debug || {}, null, 2) }}</pre>
        </details>
      </div>

      <AiRuntimePanel
        v-if="activeRuntime && activeRuntime.feature_type !== 'mcp_tool_call'"
        :runtime="activeRuntime"
        :health="capabilities"
        :steps="activeRuntimeSteps"
        :artifacts="activeRuntimeArtifacts"
        :loading="runtimeLoading"
        @refresh="loadRuntime(activeRuntime.run_id)"
        @retry="handleRuntimeAction('retry')"
        @resume="handleRuntimeAction('resume')"
        @cancel="handleRuntimeAction('cancel')"
        @approve="handleRuntimeAction('approve')"
        @reject="handleRuntimeAction('reject')"
      />
    </PageSection>

    <PageSection title="MCP 技能中心" subtitle="普通用户只看技能卡、用途说明和表单调用；协议细节和原始结果收纳到高级区。">
      <div v-if="groupedTools.length" class="page-stack tool-catalog">
        <div v-for="group in groupedTools" :key="group.title" class="tool-group">
          <div class="tool-group-title">{{ group.title }}</div>
          <div class="action-card-list">
            <article
              v-for="tool in group.tools"
              :key="tool.name"
              class="action-card tool-card"
              :class="{ active: selectedTool === tool.name }"
              @click="handleSelectTool(tool.name)"
            >
              <div class="action-card-head">
                <div>
                  <div class="action-card-title">{{ tool.display_name || tool.name }}</div>
                  <div class="action-card-subtitle">{{ tool.summary || tool.description }}</div>
                </div>
                <div class="soft-pill">{{ getToolStatus(tool) }}</div>
              </div>
              <div class="action-card-description">{{ tool.details || '点击后可直接在网页端填写参数并调用。' }}</div>
              <details class="details-box" @click.stop>
                <summary>展开说明</summary>
                <div class="soft-caption">{{ tool.details || tool.description || '当前技能暂无补充说明。' }}</div>
                <pre v-if="tool.example_args" class="pre-block">{{ JSON.stringify(tool.example_args, null, 2) }}</pre>
              </details>
              <div class="button-row">
                <button class="ghost-button small primary" type="button" @click.stop="handleSelectTool(tool.name)">立即使用</button>
              </div>
            </article>
          </div>
        </div>
      </div>

      <div v-if="selectedToolMeta" class="result-card">
        <div class="chip-row compact">
          <span class="chip-light">表单模式</span>
          <span class="chip-light">无需手写 JSON</span>
        </div>
        <div class="action-card-title">{{ selectedToolMeta.display_name || selectedToolMeta.name }}</div>
        <div class="action-card-description">{{ selectedToolMeta.summary || selectedToolMeta.description }}</div>
        <div class="chip-row">
          <span class="chip-light">{{ selectedToolMeta.category || '技能' }}</span>
          <span class="chip-light">排序 {{ selectedToolMeta.ui_order || '--' }}</span>
          <span class="chip-light">{{ fieldDefinitions.length ? `${fieldDefinitions.length} 个参数` : '无需参数' }}</span>
        </div>

        <details class="details-box">
          <summary>展开说明</summary>
          <div class="soft-caption">{{ selectedToolMeta.details || '当前技能暂无更详细说明。' }}</div>
          <pre v-if="selectedToolMeta.example_args" class="pre-block">{{ JSON.stringify(selectedToolMeta.example_args, null, 2) }}</pre>
        </details>
      </div>

      <div v-if="selectedToolMeta" class="result-card">
        <div class="action-card-title">填写参数</div>
        <div class="action-card-description">常用字段会自动转成表单；数组字段支持逗号或换行分隔。</div>

        <div v-if="fieldDefinitions.length" class="field-grid">
          <label
            v-for="field in fieldDefinitions"
            :key="field.name"
            class="field-stack"
            :class="{ 'span-3': field.type === 'array' && field.itemsType === 'string' }"
          >
            <span class="field-label">
              {{ field.title }}
              <span v-if="field.required" class="field-required">*</span>
            </span>

            <select
              v-if="field.enum.length"
              v-model="toolForm[field.name]"
              class="select-input"
            >
              <option value="">请选择</option>
              <option v-for="item in field.enum" :key="item" :value="item">{{ item }}</option>
            </select>

            <label v-else-if="field.type === 'boolean'" class="toggle-card">
              <span>{{ buildFieldHint(field) }}</span>
              <input v-model="toolForm[field.name]" type="checkbox" class="checkbox-input" />
            </label>

            <textarea
              v-else-if="field.type === 'array' && field.itemsType === 'string'"
              v-model="toolForm[field.name]"
              class="text-area"
              rows="4"
              :placeholder="field.exampleValue ? Array.isArray(field.exampleValue) ? field.exampleValue.join('\n') : String(field.exampleValue) : '每行一个值，或使用逗号分隔'"
            />

            <input
              v-else
              v-model="toolForm[field.name]"
              class="text-input"
              :inputmode="field.type === 'integer' ? 'numeric' : 'text'"
              :placeholder="field.exampleValue !== undefined ? String(field.exampleValue) : field.type === 'integer' ? '请输入整数' : '请输入内容'"
            />

            <span class="form-help">{{ buildFieldHint(field) }}</span>
            <span v-if="toolFieldErrors[field.name]" class="field-error">{{ toolFieldErrors[field.name] }}</span>
          </label>
        </div>

        <div v-else class="empty-state">这个技能不需要额外参数，直接点击“立即使用”即可。</div>

        <div class="button-row">
          <button class="primary-button" type="button" :disabled="mcpLoading || !capabilities?.mcp_available" @click="handleCallTool">
            {{ mcpLoading ? '调用中...' : '立即使用' }}
          </button>
          <button class="ghost-button" type="button" @click="applyExampleArgs">填入示例参数</button>
        </div>
      </div>

      <div v-if="mcpError" class="notice error">{{ mcpError }}</div>

      <div v-if="mcpResultView" class="result-card">
        <div class="action-card-title">{{ mcpResultView.title }}</div>
        <div v-if="mcpResultView.summary" class="action-card-description">{{ mcpResultView.summary }}</div>

        <div v-if="mcpResultView.metrics?.length" class="info-grid compact-grid">
          <article v-for="item in mcpResultView.metrics" :key="item.label" class="info-card">
            <div class="info-label">{{ item.label }}</div>
            <div class="info-value">{{ item.value }}</div>
            <div v-if="item.description" class="info-description">{{ item.description }}</div>
          </article>
        </div>

        <div v-if="mcpResultView.items?.length" class="list-stack">
          <div v-for="(item, index) in mcpResultView.items.slice(0, 8)" :key="`${item.title}-${index}`" class="list-line">
            <strong>{{ item.title }}</strong>
            <span v-if="item.subtitle" class="line-meta">{{ item.subtitle }}</span>
            <span v-if="item.meta" class="soft-caption">{{ item.meta }}</span>
          </div>
        </div>

        <div v-if="mcpResultView.followups?.length" class="chip-row">
          <span v-for="item in mcpResultView.followups.slice(0, 3)" :key="item" class="chip-light">{{ item }}</span>
        </div>

        <details class="details-box">
          <summary>高级调试</summary>
          <pre class="pre-block">{{ JSON.stringify(mcpResultView.raw, null, 2) }}</pre>
        </details>
      </div>

      <AiRuntimePanel
        v-if="activeRuntime && activeRuntime.feature_type === 'mcp_tool_call'"
        :runtime="activeRuntime"
        :health="capabilities"
        :steps="activeRuntimeSteps"
        :artifacts="activeRuntimeArtifacts"
        :loading="runtimeLoading"
        @refresh="activeRuntime.run_id ? loadRuntime(activeRuntime.run_id) : null"
        @retry="handleRuntimeAction('retry')"
        @resume="handleRuntimeAction('resume')"
        @cancel="handleRuntimeAction('cancel')"
        @approve="handleRuntimeAction('approve')"
        @reject="handleRuntimeAction('reject')"
      />
    </PageSection>
  </div>
</template>
