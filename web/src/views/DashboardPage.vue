<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import PageSection from '../components/PageSection.vue';
import InfoGrid from '../components/InfoGrid.vue';
import ActionCardList from '../components/ActionCardList.vue';
import { getMe } from '../services/auth';
import { getTodayTask, startTodayTask } from '../services/plans';
import { getOverview } from '../services/stats';
import { getStudyCoach } from '../services/ai';
import { useSessionStore } from '../stores/session';

const router = useRouter();
const sessionStore = useSessionStore();

const user = ref(null);
const plan = ref(null);
const task = ref(null);
const summary = ref(null);
const adaptive = ref(null);
const overview = ref(null);
const studyCoach = ref(null);
const studyCoachLoading = ref(false);
const studyCoachError = ref('');

const greetingName = computed(() => user.value?.nickname || '学习者');
const hasPlan = computed(() => Boolean(plan.value?.id));

const heroStats = computed(() => [
  {
    label: '今日新词',
    value: task.value ? `${task.value.learned_count}/${task.value.new_word_target}` : '0/0',
    description: hasPlan.value ? '今天新词学习进度' : '先创建计划后这里会显示今日目标',
  },
  {
    label: '今日复习剩余',
    value: String(summary.value?.review_words_remaining || 0),
    description: '今天还没完成的复习量',
  },
  {
    label: '当前词书总进度',
    value: plan.value ? `${plan.value.finished_word_count} / ${plan.value.book?.word_count || '--'}` : '--',
    description: hasPlan.value ? '累计已学单词数' : '选择词书后开始累计',
  },
  {
    label: '每日目标',
    value: plan.value ? `${plan.value.daily_target} 个` : `${user.value?.settings?.daily_target || 0} 个`,
    description: hasPlan.value ? '当前学习节奏' : '这是你设置中的默认目标',
  },
]);

const quickActions = computed(() => {
  if (!hasPlan.value) {
    return [
      {
        title: '先选一本词书',
        subtitle: '网页端第一步是把学习计划建起来',
        description: '选好词书和每日目标后，网页和小程序就会共享同一份学习进度。',
        badge: '起步',
        tags: ['词书', '计划', '共享进度'],
        actions: [
          { label: '去选词书', primary: true, onClick: () => router.push('/web/books') },
          { label: '学习计划', onClick: () => router.push('/web/plan') },
        ],
      },
      {
        title: '先熟悉 AI 中心',
        subtitle: '在还没开始学之前也可以先体验 RAG 和技能中心',
        badge: '探索',
        tags: ['RAG', '技能卡'],
        actions: [
          { label: '打开 AI 中心', primary: true, onClick: () => router.push('/web/ai') },
        ],
      },
    ];
  }

  return [
    {
      title: '继续学习',
      subtitle: '从今天的新词任务接着往下学',
      description: '保持和小程序完全一致的任务语义，网页端继续学也会写回同一份后端记录。',
      badge: '主线',
      tags: ['新词', '自动记进度', '沉浸学习'],
      actions: [
        { label: '进入学习', primary: true, onClick: handleStartTask },
        { label: '学习计划', onClick: () => router.push('/web/plan') },
      ],
    },
    {
      title: '开始复习',
      subtitle: '复习页面会沿用你设置的每轮题数和自动发音策略',
      badge: '回收',
      tags: ['旧词', '批次练习'],
      actions: [
        { label: '去复习', primary: true, onClick: () => router.push('/web/review') },
        { label: '错词本', onClick: () => router.push('/web/wrong-words') },
      ],
    },
    {
      title: '查看 AI 中心',
      subtitle: 'RAG、MCP、AI 计划和语法 tutor 都能在网页端继续用',
      badge: '辅助',
      tags: ['问资料', '改计划', '技能中心'],
      actions: [
        { label: '打开 AI 中心', primary: true, onClick: () => router.push('/web/ai') },
        { label: '语法中心', onClick: () => router.push('/web/grammar') },
      ],
    },
  ];
});

const planSummaryItems = computed(() => {
  if (!plan.value) {
    return [];
  }
  return [
    { label: '当前词书', value: plan.value.book?.name || '--', description: plan.value.book?.category || '词书' },
    { label: '已学单词', value: plan.value.finished_word_count || 0, description: '当前计划累计完成量' },
    { label: '词书总量', value: plan.value.book?.word_count || 0, description: '这本词书一共有多少词' },
    { label: '计划状态', value: plan.value.status || 'active', description: '网页端和小程序共用同一计划状态' },
  ];
});

async function loadPage() {
  const [userData, todayTask, overviewData] = await Promise.all([
    getMe(),
    getTodayTask(),
    getOverview(),
  ]);
  user.value = userData;
  plan.value = todayTask.plan?.id ? todayTask.plan : null;
  task.value = todayTask.task || null;
  summary.value = todayTask.summary || null;
  adaptive.value = todayTask.adaptive || null;
  overview.value = overviewData || null;
  sessionStore.setUserInfo(userData);
  if (userData?.settings) {
    sessionStore.setSettings(userData.settings);
  }
  sessionStore.setCurrentPlan(plan.value);
}

async function handleStartTask() {
  try {
    await startTodayTask();
  } catch (error) {
    // ignore if already started
  }
  router.push('/web/learn');
}

async function handleLoadCoach(forceRefresh = false) {
  studyCoachLoading.value = true;
  studyCoachError.value = '';
  try {
    const result = await getStudyCoach({
      trend_days: 7,
      force_refresh: forceRefresh,
    });
    studyCoach.value = result?.coach || null;
  } catch (error) {
    studyCoachError.value = error.message || 'AI 学习教练加载失败';
  } finally {
    studyCoachLoading.value = false;
  }
}

onMounted(loadPage);
</script>

<template>
  <div class="page-stack">
    <PageSection tone="hero">
      <div class="hero-wrap">
        <div>
          <div class="hero-kicker">你好，{{ greetingName }}</div>
          <div class="hero-title">今天继续把单词、复习、测试和 AI 辅助一起推进。</div>
        <div class="hero-copy">
          网页端和小程序端共用同一份学习数据。你白天在小程序学过的内容，晚上回到网页依然会自动续上。
        </div>
      </div>
        <InfoGrid :items="heroStats" card-class="glass-card" />
      </div>
    </PageSection>

    <PageSection v-if="!hasPlan" title="还没有学习计划" subtitle="先建计划，网页端所有学习功能才会进入完整状态。">
      <div class="empty-state">
        你现在还没有绑定词书和今日任务。建议先去词书页或学习计划页创建第一份计划，然后再开始学习、复习和 AI 调整。
      </div>
      <div class="button-row">
        <button class="primary-button" type="button" @click="router.push('/web/books')">去选词书</button>
        <button class="ghost-button" type="button" @click="router.push('/web/plan')">去建计划</button>
      </div>
    </PageSection>

    <PageSection
      v-if="hasPlan"
      title="当前计划"
      :subtitle="`${plan.book?.name || '未选择词书'} · 每日目标 ${plan.daily_target} 个 · 已学 ${plan.finished_word_count} 个`"
    >
      <InfoGrid :items="planSummaryItems" />
      <div v-if="task || summary" class="notice">
        今日还剩 {{ summary?.new_words_remaining || 0 }} 个新词、{{ summary?.review_words_remaining || 0 }} 个复习任务、{{ summary?.wrong_words || 0 }} 个错词待处理。
      </div>
    </PageSection>

    <PageSection
      v-if="adaptive"
      title="今日个性化建议"
      :subtitle="adaptive.mode_label || '根据你的学习趋势自动调整今日节奏'"
    >
      <InfoGrid
        :items="[
          { label: '建议新词', value: adaptive.recommended_new_word_target, description: adaptive.focus_tip },
          { label: '建议复习', value: adaptive.recommended_review_word_target, description: '根据复习压力动态生成' },
          { label: '已到复习时间', value: adaptive.due_review_count, description: '现在可以直接开始复习' },
          { label: '近期正确率', value: `${adaptive.recent_accuracy_percent || '--'}%`, description: '最近学习质量' },
        ]"
      />
    </PageSection>

    <PageSection title="学习快捷入口" subtitle="把最常用的学习入口集中放在首页。">
      <ActionCardList :items="quickActions" />
    </PageSection>

    <PageSection title="AI 学习教练" subtitle="默认不自动请求。需要时你再手动生成，避免打断主学习流程。">
      <div class="button-row">
        <button class="primary-button" type="button" :disabled="studyCoachLoading" @click="handleLoadCoach(false)">
          {{ studyCoachLoading ? '生成中...' : '生成 AI 学习建议' }}
        </button>
        <button class="ghost-button" type="button" :disabled="studyCoachLoading" @click="handleLoadCoach(true)">
          强制刷新
        </button>
      </div>

      <div v-if="studyCoachError" class="notice error">{{ studyCoachError }}</div>

      <div v-if="studyCoach" class="coach-panel">
        <div class="coach-headline">{{ studyCoach.headline }}</div>
        <div class="coach-copy">{{ studyCoach.today_strategy }}</div>
        <div class="notice">{{ studyCoach.coach_tip }}</div>
        <div v-if="studyCoach.recommended_order?.length" class="list-stack">
          <div v-for="(item, index) in studyCoach.recommended_order" :key="item" class="list-line">
            {{ index + 1 }}. {{ item }}
          </div>
        </div>
        <div class="coach-motivation">{{ studyCoach.motivation_line }}</div>
      </div>
    </PageSection>

    <PageSection v-if="overview" title="学习数据" subtitle="统计模块已并入首页，详细趋势和打卡依然可以单独查看。">
      <InfoGrid
        :items="[
          { label: '累计学习', value: overview.learned_word_count, description: '总共学过多少单词' },
          { label: '复习次数', value: overview.review_count, description: '累计完成复习次数' },
          { label: '测试次数', value: overview.test_count, description: '练习与分级测试总次数' },
          { label: '平均分', value: overview.average_test_score, description: '当前测试平均成绩' },
          { label: '收藏词数', value: overview.favorite_count, description: '你主动保留下来的重点词' },
          { label: '错词数量', value: overview.wrong_word_count, description: '仍需重点回收的词汇' },
        ]"
      />
    </PageSection>
  </div>
</template>
