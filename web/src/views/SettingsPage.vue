<script setup>
import { onMounted, ref } from 'vue';
import PageSection from '../components/PageSection.vue';
import { getSettings, rebuildPersonalizedRag, updateSettings } from '../services/auth';
import { speakText } from '../lib/speech';
import { useSessionStore } from '../stores/session';

const sessionStore = useSessionStore();
const noticeText = ref('');
const errorText = ref('');
const settings = ref({
  auto_play_audio: true,
  speech_speed: 1,
  review_enabled: true,
  review_batch_size: 8,
  personalized_rag_enabled: false,
  reminder_subscription_status: 'unknown',
});

async function loadSettings() {
  const userSettings = await getSettings();
  settings.value = {
    ...settings.value,
    ...(userSettings || {}),
    review_batch_size: Number(sessionStore.settings.review_batch_size || settings.value.review_batch_size || 8),
  };
  sessionStore.setSettings(settings.value);
}

async function saveServerPatch(patch) {
  noticeText.value = '';
  errorText.value = '';
  const saved = await updateSettings(patch);
  settings.value = {
    ...settings.value,
    ...(saved || {}),
  };
  sessionStore.setSettings(settings.value);
  noticeText.value = '设置已同步到后端。';
}

function saveLocalPatch(patch, message) {
  settings.value = {
    ...settings.value,
    ...(patch || {}),
  };
  sessionStore.setSettings(patch);
  noticeText.value = message;
  errorText.value = '';
}

async function handlePlayDemo() {
  await speakText('Today is a good day to keep learning English.', { lang: 'en-US' });
}

async function handleRebuildPersonalizedRag() {
  await rebuildPersonalizedRag();
  await loadSettings();
  noticeText.value = '个性化知识库刷新请求已经发出。';
}

onMounted(loadSettings);
</script>

<template>
  <div class="page-stack">
    <PageSection tone="hero">
      <div class="hero-wrap compact">
        <div>
          <div class="hero-kicker">学习设置</div>
          <div class="hero-title">把节奏、发音和个性知识库调成最适合你的状态。</div>
          <div class="hero-copy">这里改动的设置会直接影响网页端体验，其中服务端设置也会同步回小程序。</div>
        </div>
      </div>
    </PageSection>

    <PageSection title="学习设置" subtitle="网页端会和小程序共用同一份个性化设置。">
      <div class="field-grid">
        <label class="toggle-card">
          <span>自动播放发音</span>
          <input v-model="settings.auto_play_audio" type="checkbox" @change="saveServerPatch({ auto_play_audio: settings.auto_play_audio })" />
        </label>
        <label class="toggle-card">
          <span>启用复习</span>
          <input v-model="settings.review_enabled" type="checkbox" @change="saveServerPatch({ review_enabled: settings.review_enabled })" />
        </label>
      </div>
      <div class="toolbar-grid">
        <label class="field-stack">
          <span class="field-label">语速</span>
          <input v-model.number="settings.speech_speed" class="text-input" type="number" min="0.5" max="1.2" step="0.1" @change="saveServerPatch({ speech_speed: settings.speech_speed })" />
        </label>
        <label class="field-stack">
          <span class="field-label">每轮复习题数</span>
          <input
            v-model.number="settings.review_batch_size"
            class="text-input"
            type="number"
            min="1"
            max="50"
            @change="saveLocalPatch({ review_batch_size: Math.min(Math.max(Math.round(settings.review_batch_size || 8), 1), 50) }, '每轮复习题数已保存在当前网页端本地设置中。')"
          />
        </label>
      </div>
      <div class="button-row">
        <button class="ghost-button" type="button" @click="handlePlayDemo">试听发音</button>
      </div>
      <div v-if="noticeText" class="notice">{{ noticeText }}</div>
      <div v-if="errorText" class="notice error">{{ errorText }}</div>
    </PageSection>

    <PageSection title="个性化 RAG" subtitle="网页端可以继续刷新你的个人知识库。">
      <div class="info-grid">
        <article class="info-card">
          <div class="info-label">是否启用</div>
          <div class="info-value">{{ settings.personalized_rag_enabled ? '已开启' : '未开启' }}</div>
          <div class="info-description">先在这里控制开关，再刷新个人知识库。</div>
        </article>
        <article class="info-card">
          <div class="info-label">当前状态</div>
          <div class="info-value">{{ settings.personalized_rag_status || 'idle' }}</div>
          <div class="info-description">当前个人知识库构建状态</div>
        </article>
      </div>
      <div class="button-row">
        <button class="ghost-button" type="button" @click="saveServerPatch({ personalized_rag_enabled: !settings.personalized_rag_enabled })">
          {{ settings.personalized_rag_enabled ? '关闭个性化 RAG' : '开启个性化 RAG' }}
        </button>
        <button class="primary-button" type="button" @click="handleRebuildPersonalizedRag">创建 / 刷新我的个性知识库</button>
      </div>
      <div class="notice">微信订阅提醒等专属能力网页端只保留状态说明，真正开启仍需在小程序内完成。</div>
    </PageSection>
  </div>
</template>
