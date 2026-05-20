<script setup>
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useSessionStore } from '../stores/session';

const route = useRoute();
const router = useRouter();
const sessionStore = useSessionStore();

const pageTitle = computed(() => route.meta.title || 'GAClearn');
const displayName = computed(() => (sessionStore.userInfo && sessionStore.userInfo.nickname) || '学习者');
const planChip = computed(() => {
  const plan = sessionStore.currentPlan;
  if (plan?.book?.name) {
    return `${plan.book.name} · 日目标 ${plan.daily_target || 0}`;
  }
  return '还没有学习计划';
});
const pageLead = computed(() => {
  const name = route.name;
  if (name === 'home') return '先完成今天最重要的一步，再看细节。';
  if (name === 'plan') return '把节奏调顺之后，后面的学习会轻松很多。';
  if (name === 'learn') return '保持注意力在当前这个词，快速推进。';
  if (name === 'review') return '用短反馈和连贯节奏把旧词真正回收。';
  if (name === 'ai') return '先拿结果，再按需展开依据和高级信息。';
  return '网页端和小程序共用同一份学习记录与计划。';
});

function handleLogout() {
  sessionStore.clearAuth();
  router.replace('/web/login');
}
</script>

<template>
  <header class="app-topbar">
    <div class="topbar-main">
      <div class="topbar-kicker">Web Study Space</div>
      <h1 class="topbar-title">{{ pageTitle }}</h1>
      <div class="topbar-copy">{{ pageLead }}</div>
      <div class="topbar-badge-row">
        <span class="topbar-badge">共享进度</span>
        <span class="topbar-badge secondary">{{ planChip }}</span>
      </div>
    </div>
    <div class="topbar-actions">
      <div class="topbar-pill">
        <span class="topbar-pill-label">当前用户</span>
        <strong>{{ displayName }}</strong>
      </div>
      <button class="ghost-button small" type="button" @click="handleLogout">退出</button>
    </div>
  </header>
</template>
