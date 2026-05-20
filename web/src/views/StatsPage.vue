<script setup>
import { computed, onMounted, ref } from 'vue';
import InfoGrid from '../components/InfoGrid.vue';
import PageSection from '../components/PageSection.vue';
import { checkin, getCheckinHistory, getOverview, getTrend } from '../services/stats';

const overview = ref(null);
const trend = ref([]);
const checkins = ref([]);
const checkingIn = ref(false);

const overviewItems = computed(() => {
  if (!overview.value) {
    return [];
  }
  return [
    { label: '累计学习', value: overview.value.learned_word_count, description: '总学习单词数' },
    { label: '累计复习', value: overview.value.review_count, description: '完成过的复习次数' },
    { label: '测试次数', value: overview.value.test_count, description: '词汇测试和分级测试总次数' },
    { label: '平均成绩', value: overview.value.average_test_score, description: '当前测试平均分' },
    { label: '收藏词数', value: overview.value.favorite_count, description: '主动留下的重点词汇' },
    { label: '连续打卡', value: overview.value.streak_days, description: '持续学习天数' },
  ];
});

const trendHighlights = computed(() => {
  const totalLearned = trend.value.reduce((sum, item) => sum + Number(item.learned_count || 0), 0);
  const totalReviews = trend.value.reduce((sum, item) => sum + Number(item.review_count || 0), 0);
  const totalTests = trend.value.reduce((sum, item) => sum + Number(item.test_count || 0), 0);
  const bestAccuracy = trend.value.reduce((best, item) => Math.max(best, Number(item.review_accuracy || 0)), 0);
  return [
    { label: '7 天新词', value: totalLearned, description: '最近一周推进的新词总量' },
    { label: '7 天复习', value: totalReviews, description: '最近一周完成的复习总量' },
    { label: '7 天测试', value: totalTests, description: '最近一周完成的测试总量' },
    { label: '最高复习正确率', value: `${bestAccuracy}%`, description: '最近一周表现最好的一天' },
  ];
});

async function loadPage() {
  const [overviewData, trendData, checkinsData] = await Promise.all([
    getOverview(),
    getTrend({ days: 7 }),
    getCheckinHistory(),
  ]);
  overview.value = overviewData;
  trend.value = trendData?.list || [];
  checkins.value = checkinsData?.list || [];
}

async function handleCheckin() {
  checkingIn.value = true;
  try {
    await checkin();
    await loadPage();
  } finally {
    checkingIn.value = false;
  }
}
</script>

<template>
  <div class="page-stack">
    <PageSection tone="hero">
      <div class="hero-wrap compact">
        <div>
          <div class="hero-kicker">学习趋势</div>
          <div class="hero-title">把每天的推进、复习和打卡节奏看清楚。</div>
          <div class="hero-copy">这里的数据和小程序完全共用，适合在大屏上回看最近的学习状态。</div>
        </div>
      </div>
    </PageSection>

    <PageSection title="学习统计" subtitle="网页端和小程序端共用同一份统计数据。">
      <InfoGrid v-if="overview" :items="overviewItems" />
      <div class="button-row">
        <button class="primary-button" type="button" :disabled="checkingIn" @click="handleCheckin">
          {{ checkingIn ? '打卡中...' : '今日打卡' }}
        </button>
      </div>
    </PageSection>

    <PageSection title="最近 7 天趋势" subtitle="先看整体，再看每天的节奏变化。">
      <InfoGrid :items="trendHighlights" />
      <div class="list-stack">
        <div v-for="item in trend" :key="item.date" class="list-line">
          <strong>{{ item.date }}</strong>
          <span class="line-meta">新词 {{ item.learned_count }} · 复习 {{ item.review_count }} · 语法 {{ item.grammar_count }} · 测试 {{ item.test_count }}</span>
          <span class="soft-caption">复习正确率 {{ item.review_accuracy || 0 }}%</span>
        </div>
      </div>
    </PageSection>

    <PageSection title="打卡记录" subtitle="持续打卡会在这里沉淀。">
      <div v-if="checkins.length" class="list-stack">
        <div v-for="item in checkins" :key="item.checkin_date" class="list-line">
          <strong>{{ item.checkin_date }}</strong>
          <span class="line-meta">{{ item.status || '已打卡' }}</span>
        </div>
      </div>
      <div v-else class="empty-state">当前还没有打卡记录，今天打卡后这里就会开始累计。</div>
    </PageSection>
  </div>
</template>
