<script setup>
import { computed, onMounted, watch } from 'vue';
import { RouterView, useRoute } from 'vue-router';
import AppSidebar from './components/AppSidebar.vue';
import AppTopbar from './components/AppTopbar.vue';
import MobileTabbar from './components/MobileTabbar.vue';
import { applyDocumentTheme } from './lib/theme';
import { useSessionStore } from './stores/session';

const route = useRoute();
const sessionStore = useSessionStore();

const hideChrome = computed(() => route.meta.hideChrome === true);
const shellClass = computed(() => (hideChrome.value ? 'app-shell auth-shell' : 'app-shell'));

onMounted(() => {
  sessionStore.hydrate();
  applyDocumentTheme(sessionStore.settings);
});

watch(
  () => sessionStore.settings,
  (settings) => {
    applyDocumentTheme(settings || {});
  },
  {
    deep: true,
    immediate: true,
  },
);
</script>

<template>
  <div :class="shellClass">
    <template v-if="!hideChrome">
      <AppSidebar />
      <div class="app-main">
        <AppTopbar />
        <main class="app-content">
          <RouterView />
        </main>
      </div>
      <MobileTabbar />
    </template>
    <RouterView v-else />
  </div>
</template>
