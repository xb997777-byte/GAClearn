<script setup>
import { useRoute } from 'vue-router';

const route = useRoute();

const items = [
  { to: '/web/home', label: '首页', pin: 'H' },
  { to: '/web/books', label: '词书', pin: 'B' },
  { to: '/web/grammar', label: '语法', pin: 'G' },
  { to: '/web/ai', label: 'AI', pin: 'AI' },
  { to: '/web/profile', label: '我的', pin: 'ME' },
];
</script>

<template>
  <nav class="mobile-tabbar">
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="mobile-tab-item"
      :class="{ active: route.path.startsWith(item.to) }"
    >
      <span class="mobile-tab-glyph">{{ item.pin }}</span>
      <span class="mobile-tab-label">{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>
