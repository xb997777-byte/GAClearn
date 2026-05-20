<script setup>
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { useSessionStore } from '../stores/session';

const route = useRoute();
const sessionStore = useSessionStore();

const groups = [
  {
    title: '主导航',
    items: [
      { to: '/web/home', label: '首页', pin: 'HO', hint: '看今天该做什么' },
      { to: '/web/books', label: '词书', pin: 'BK', hint: '切换学习素材' },
      { to: '/web/grammar', label: '语法', pin: 'GR', hint: '系统补语法点' },
      { to: '/web/ai', label: 'AI 中心', pin: 'AI', hint: '问、改、练、写' },
      { to: '/web/profile', label: '我的', pin: 'ME', hint: '查看资产与设置' },
    ],
  },
  {
    title: '学习流程',
    items: [
      { to: '/web/plan', label: '学习计划', pin: 'PL', hint: '调节新词与复习节奏' },
      { to: '/web/learn', label: '学习单词', pin: 'WD', hint: '进入沉浸式学词' },
      { to: '/web/review', label: '复习', pin: 'RV', hint: '集中回收薄弱点' },
      { to: '/web/exam', label: '测试', pin: 'EX', hint: '检查掌握情况' },
      { to: '/web/stats', label: '统计', pin: 'ST', hint: '回看学习趋势' },
    ],
  },
];

const currentPath = computed(() => route.path);
const currentPlan = computed(() => sessionStore.currentPlan);
const learnerName = computed(() => sessionStore.userInfo?.nickname || '学习者');
const missionCopy = computed(() => {
  if (currentPlan.value?.book?.name) {
    return `当前围绕《${currentPlan.value.book.name}》推进，多端记录会自动汇总到同一份进度里。`;
  }
  return '先选词书并设定节奏，接下来首页、学习、复习和 AI 都会围绕同一份计划展开。';
});
const missionStats = computed(() => [
  {
    label: '日目标',
    value: `${currentPlan.value?.daily_target || sessionStore.settings.daily_target || 0}词`,
  },
  {
    label: '复习批次',
    value: `${sessionStore.settings.review_batch_size || 8}题`,
  },
]);
</script>

<template>
  <aside class="app-sidebar">
    <div class="brand-lockup">
      <div class="brand-mark">GL</div>
      <div class="brand-kicker">GAClearn</div>
      <div class="brand-title">多端连续学习空间</div>
      <div class="brand-copy">把今天要做的事收拢成一条清晰主线，网页端继续学也不会断掉节奏。</div>
    </div>

    <div class="sidebar-mission">
      <div class="sidebar-mission-kicker">Learning Pulse</div>
      <div class="sidebar-mission-title">{{ learnerName }}</div>
      <div class="sidebar-mission-copy">{{ missionCopy }}</div>
      <div class="sidebar-mission-grid">
        <div v-for="item in missionStats" :key="item.label" class="mission-chip">
          <span class="mission-chip-label">{{ item.label }}</span>
          <span class="mission-chip-value">{{ item.value }}</span>
        </div>
      </div>
    </div>

    <section v-for="group in groups" :key="group.title" class="sidebar-group">
      <div class="sidebar-group-title">{{ group.title }}</div>
      <RouterLink
        v-for="item in group.items"
        :key="item.to"
        :to="item.to"
        class="sidebar-link"
        :class="{ active: currentPath.startsWith(item.to) }"
      >
        <span class="sidebar-link-pin">{{ item.pin }}</span>
        <span class="sidebar-link-copy">
          <span class="sidebar-link-label">{{ item.label }}</span>
          <span class="sidebar-link-hint">{{ item.hint }}</span>
        </span>
      </RouterLink>
    </section>
  </aside>
</template>
