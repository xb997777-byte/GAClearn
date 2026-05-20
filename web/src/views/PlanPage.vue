<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import AiRuntimePanel from '../components/AiRuntimePanel.vue';
import PageSection from '../components/PageSection.vue';
import InfoGrid from '../components/InfoGrid.vue';
import { getBookDetail } from '../services/books';
import { applyAiPlanPatch, createPlan, getCurrentPlan, getPlanHistory, getTodayTask, switchBook, updateCurrentPlan } from '../services/plans';
import { approveAiRun, cancelAiRun, getAiRunArtifacts, getAiRunSteps, getPlanReplanRun, replanStudyPlan, resumeAiRun, retryAiRun } from '../services/ai';
import { useSessionStore } from '../stores/session';

const router = useRouter();
const route = useRoute();
const sessionStore = useSessionStore();

const pageLoading = ref(true);
const currentPlan = ref(null);
const currentBook = ref(null);
const selectedTarget = ref(20);
const reviewBatchSize = ref(8);
const todayTask = ref(null);
const planHistory = ref([]);
const aiPlanLoading = ref(false);
const aiPlanApplying = ref(false);
const aiPlanResult = ref(null);
const aiPlanStatusText = ref('');
const pageNotice = ref('');
const pageError = ref('');
const aiPlanRunDetail = ref(null);
const aiPlanSteps = ref([]);
const aiPlanArtifacts = ref([]);
let aiPollTimer = null;

const planMetrics = computed(() => {
  const task = todayTask.value || {};
  return [
    { label: '今天新词目标', value: Number(task.new_word_target || selectedTarget.value), description: '会和当前计划保持同步' },
    { label: '今天复习目标', value: Number(task.review_word_target || 0), description: '系统按到期词自动安排' },
    { label: '每轮复习题数', value: reviewBatchSize.value, description: '进入复习页时直接生效' },
  ];
});

async function loadPage() {
  pageLoading.value = true;
  try {
    const [planData, taskData, historyData] = await Promise.all([
      getCurrentPlan().catch(() => null),
      getTodayTask().catch(() => null),
      getPlanHistory(6).catch(() => ({ list: [] })),
    ]);
    currentPlan.value = planData && planData.id ? planData : null;
    todayTask.value = taskData && taskData.task ? taskData.task : null;
    planHistory.value = (historyData && historyData.list) || [];
    sessionStore.setCurrentPlan(currentPlan.value);
    if (currentPlan.value) {
      selectedTarget.value = Number(currentPlan.value.daily_target || 20);
      currentBook.value = currentPlan.value.book || null;
    }
    reviewBatchSize.value = Number((sessionStore.settings && sessionStore.settings.review_batch_size) || 8);
    const routeBookId = Number(route.query.bookId || 0);
    if (routeBookId) {
      currentBook.value = await getBookDetail(routeBookId);
    }
    const cachedRun = sessionStore.aiPlanRun;
    if (cachedRun && cachedRun.feature_type === 'plan_replan' && cachedRun.run_id) {
      aiPlanLoading.value = true;
      aiPlanStatusText.value = '正在恢复上一次 AI 计划生成状态...';
      pollAiPlan(cachedRun.run_id).catch((error) => {
        aiPlanStatusText.value = error.message || 'AI 计划生成失败';
        aiPlanLoading.value = false;
      });
    } else if (sessionStore.aiPlanResult) {
      aiPlanResult.value = sessionStore.aiPlanResult;
    }
  } finally {
    pageLoading.value = false;
  }
}

function clampReviewBatchSize(value) {
  const nextValue = Number(value || 8);
  if (!Number.isFinite(nextValue)) {
    return 8;
  }
  return Math.min(Math.max(Math.round(nextValue), 1), 50);
}

async function handleSavePlan() {
  pageNotice.value = '';
  pageError.value = '';
  reviewBatchSize.value = clampReviewBatchSize(reviewBatchSize.value);
  sessionStore.setSettings({
    review_batch_size: reviewBatchSize.value,
  });
  if (!currentBook.value) {
    pageError.value = '请先从词书页选择一本词书，再回来保存学习计划。';
    return;
  }
  if (!currentPlan.value) {
    const created = await createPlan({
      book_id: currentBook.value.id,
      daily_target: Number(selectedTarget.value),
    });
    currentPlan.value = created;
    sessionStore.setCurrentPlan(created);
    pageNotice.value = '学习计划已创建，同时已经把这台网页端的每轮复习题数保存到本地。';
    router.push('/web/home');
    return;
  }

  if (currentPlan.value.book && Number(currentPlan.value.book.id) !== Number(currentBook.value.id)) {
    const switched = await switchBook({
      book_id: currentBook.value.id,
      daily_target: Number(selectedTarget.value),
    });
    currentPlan.value = switched;
    sessionStore.setCurrentPlan(switched);
    pageNotice.value = '词书和每日目标已经更新，复习题数也会从下一轮开始生效。';
    return;
  }

  const updated = await updateCurrentPlan({
    daily_target: Number(selectedTarget.value),
  });
  currentPlan.value = updated;
  sessionStore.setCurrentPlan(updated);
  pageNotice.value = '当前计划已保存，网页端的复习题数会在进入复习页时直接生效。';
}

async function pollAiPlan(runId) {
  const run = await getPlanReplanRun(runId);
  const [steps, artifacts] = await Promise.all([
    getAiRunSteps(runId).catch(() => ({ steps: [] })),
    getAiRunArtifacts(runId).catch(() => ({ artifacts: [] })),
  ]);
  aiPlanRunDetail.value = run;
  aiPlanSteps.value = steps?.steps || [];
  aiPlanArtifacts.value = artifacts?.artifacts || [];
  aiPlanStatusText.value = run.runtime_summary?.summary || run.runtime_summary?.status_text || 'AI 正在生成计划';
  if (run.status === 'succeeded' && run.result) {
    aiPlanResult.value = run.result;
    sessionStore.setAiPlanResult(run.result);
    sessionStore.setAiPlanRun(null);
    aiPlanLoading.value = false;
    return;
  }
  if (run.status === 'waiting_approval') {
    sessionStore.setAiPlanRun({
      run_id: runId,
      feature_type: 'plan_replan',
      source_page: 'web_plan',
      updated_at: Date.now(),
    });
    aiPlanLoading.value = false;
    return;
  }
  if (run.status === 'failed') {
    sessionStore.setAiPlanRun(null);
    throw new Error(run.error_message || 'AI 计划生成失败');
  }
  aiPollTimer = window.setTimeout(() => {
    pollAiPlan(runId).catch((error) => {
      aiPlanStatusText.value = error.message || 'AI 计划生成失败';
      aiPlanLoading.value = false;
    });
  }, 1800);
}

async function handlePlanRuntimeAction(action) {
  const runId = aiPlanRunDetail.value?.run_id || sessionStore.aiPlanRun?.run_id;
  if (!runId) {
    return;
  }
  if (action === 'retry') {
    await retryAiRun(runId, {});
  } else if (action === 'resume') {
    await resumeAiRun(runId, {});
  } else if (action === 'cancel') {
    await cancelAiRun(runId, {});
  } else if (action === 'approve') {
    await approveAiRun(runId, { approved: true, note: 'web plan approve' });
  } else if (action === 'reject') {
    await approveAiRun(runId, { approved: false, note: 'web plan reject' });
  }
  await pollAiPlan(runId);
}

async function handleRunAiPlan() {
  aiPlanLoading.value = true;
  aiPlanStatusText.value = '正在生成 AI 自适应计划...';
  try {
    const data = await replanStudyPlan({
      trend_days: 7,
      force_refresh: true,
      prefer_fast: false,
    });
    if (data.run_id) {
      sessionStore.setAiPlanRun({
        run_id: data.run_id,
        feature_type: 'plan_replan',
        source_page: 'web_plan',
        updated_at: Date.now(),
      });
      await pollAiPlan(data.run_id);
    } else {
      aiPlanResult.value = data;
      sessionStore.setAiPlanResult(data);
    }
  } catch (error) {
    aiPlanStatusText.value = error.message || 'AI 计划生成失败';
  } finally {
    aiPlanLoading.value = false;
  }
}

async function handleApplyAiPlan() {
  if (!aiPlanResult.value || !aiPlanResult.value.plan_patch) {
    return;
  }
  aiPlanApplying.value = true;
  try {
    const updatedPlan = await applyAiPlanPatch({
      patch: aiPlanResult.value.plan_patch,
      summary: aiPlanResult.value.headline || 'apply ai patch',
      evidence: aiPlanResult.value.evidence || {},
    });
    currentPlan.value = updatedPlan || currentPlan.value;
    sessionStore.setCurrentPlan(updatedPlan || currentPlan.value);
    sessionStore.setAiPlanResult(null);
    await loadPage();
  } finally {
    aiPlanApplying.value = false;
  }
}

onMounted(() => {
  loadPage();
});

onUnmounted(() => {
  if (aiPollTimer) {
    window.clearTimeout(aiPollTimer);
    aiPollTimer = null;
  }
});
</script>

<template>
  <div class="page-stack">
    <PageSection v-if="pageLoading" title="学习计划" subtitle="正在加载学习计划..." />

    <template v-else>
      <PageSection v-if="currentBook" tone="hero">
        <div class="hero-wrap compact">
          <div>
            <div class="hero-kicker">当前主词书</div>
            <div class="hero-title">{{ currentBook.name }}</div>
            <div class="hero-copy">网页端会围绕这本词书继续推进学习、复习和 AI 计划调整。</div>
          </div>
          <div class="chip-row">
            <span class="chip-light dark">{{ currentBook.category }}</span>
            <span class="chip-light dark">{{ currentBook.word_count }} 词</span>
          </div>
        </div>
      </PageSection>

      <PageSection
        title="每日目标"
        subtitle="把今天的学习节奏一次配好：新词、复习和每轮题数都在这里。"
      >
        <InfoGrid :items="planMetrics" />
        <div class="notice">
          这里是每天真正会影响学习主流程的三个数字：今日新词、今日复习、每轮复习题数。设置好之后，小程序和网页都会围绕同一份计划推进。
        </div>
        <div class="toolbar-grid">
          <label class="field-stack">
            <span class="field-label">每天要学多少新单词</span>
            <input v-model.number="selectedTarget" class="text-input" type="number" min="1" max="200" />
          </label>
          <label class="field-stack">
            <span class="field-label">每轮复习多少旧单词</span>
            <input v-model.number="reviewBatchSize" class="text-input" type="number" min="1" max="50" />
          </label>
        </div>
        <div class="button-row">
          <button class="primary-button" type="button" @click="handleSavePlan">保存当前计划配置</button>
          <button class="ghost-button" type="button" @click="router.push('/web/books')">去词书页</button>
        </div>
        <div v-if="pageNotice" class="notice">{{ pageNotice }}</div>
        <div v-if="pageError" class="notice error">{{ pageError }}</div>
      </PageSection>

      <PageSection title="AI 重规划学习计划" subtitle="只保留真正的 AI 自适应生成计划。">
        <div class="button-row">
          <button class="primary-button" type="button" :disabled="aiPlanLoading" @click="handleRunAiPlan">
            {{ aiPlanLoading ? 'AI 正在生成...' : '生成 AI 自适应计划' }}
          </button>
          <button v-if="aiPlanResult" class="ghost-button" type="button" @click="router.push('/web/ai')">查看详细分析</button>
        </div>
        <div v-if="aiPlanStatusText" class="soft-caption strong">{{ aiPlanStatusText }}</div>

        <div v-if="aiPlanResult" class="plan-ai-card">
          <div class="chip-row compact">
            <span class="chip-light">AI 分析完成</span>
            <span class="chip-light">下一步请直接应用</span>
          </div>
          <div class="action-card-title">{{ aiPlanResult.headline }}</div>
          <div class="action-card-description">{{ aiPlanResult.summary }}</div>
          <InfoGrid
            :items="[
              { label: '建议日目标', value: aiPlanResult.new_plan?.suggested_daily_target || aiPlanResult.new_plan?.current_daily_target || '--', description: aiPlanResult.new_plan?.focus_mode_label || 'AI 建议的新节奏' },
              { label: '建议复习量', value: aiPlanResult.new_plan?.review_target || '--', description: '结合复习压力动态生成' },
            ]"
          />
          <div v-if="aiPlanResult.new_plan?.study_order?.length" class="list-stack">
            <div v-for="(item, index) in aiPlanResult.new_plan.study_order" :key="item" class="list-line">
              {{ index + 1 }}. {{ item }}
            </div>
          </div>
          <div class="button-row">
            <button class="primary-button" type="button" :disabled="aiPlanApplying" @click="handleApplyAiPlan">
              {{ aiPlanApplying ? '应用中...' : '应用这份 AI 调整' }}
            </button>
          </div>
        </div>

        <AiRuntimePanel
          v-if="aiPlanRunDetail"
          :runtime="aiPlanRunDetail"
          :steps="aiPlanSteps"
          :artifacts="aiPlanArtifacts"
          :loading="aiPlanLoading || aiPlanApplying"
          @refresh="pollAiPlan(aiPlanRunDetail.run_id)"
          @retry="handlePlanRuntimeAction('retry')"
          @resume="handlePlanRuntimeAction('resume')"
          @cancel="handlePlanRuntimeAction('cancel')"
          @approve="handlePlanRuntimeAction('approve')"
          @reject="handlePlanRuntimeAction('reject')"
        />
      </PageSection>

      <PageSection v-if="planHistory.length" title="最近计划变更" subtitle="方便确认 AI patch 是否真的落到了当前计划。">
        <div class="list-stack">
          <div v-for="item in planHistory" :key="item.id" class="list-line">
            <strong>{{ item.summary }}</strong>
            <span class="line-meta">{{ item.created_at }}</span>
          </div>
        </div>
      </PageSection>
    </template>
  </div>
</template>
