<script setup>
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { wxLogin } from '../services/auth';
import { getCurrentPlan } from '../services/plans';
import { getBootstrap } from '../services/system';
import { useSessionStore } from '../stores/session';

const router = useRouter();
const route = useRoute();
const sessionStore = useSessionStore();

const loading = ref(false);
const debugIdentity = ref('webtester');
const featureTips = ref([]);
const loginModeText = ref('正在检查登录模式...');
const loginError = ref('');

const redirectTarget = computed(() => route.query.redirect || '/web/home');

async function loadBootstrap() {
  try {
    const bootstrap = await getBootstrap();
    const features = (bootstrap && bootstrap.features) || {};
    loginModeText.value = features.wechat_login_enabled
      ? '当前后端已启用真实微信登录，但网页端首轮会继续使用共享学习身份登录，保证你可以直接和小程序共用同一份学习数据。'
      : '当前正在使用开发调试登录。网页端和小程序只要用同一个身份标识登录，就会回到同一份学习数据。';
    featureTips.value = [
      features.ai_enabled ? '语法 AI：已启用' : '语法 AI：未配置',
      features.subscribe_reminder_enabled ? '订阅提醒：可用' : '订阅提醒：需在小程序内开启',
      `登录模式：${features.wechat_login_mode || 'auto'}`,
    ];
  } catch (error) {
    loginModeText.value = '未能读取系统配置，将优先使用共享学习身份登录。';
    featureTips.value = ['请确认 Django 后端已经启动'];
  }
}

function normalizeIdentity(value) {
  return String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '') || 'webtester';
}

async function handleLogin() {
  loading.value = true;
  loginError.value = '';
  try {
    const code = `debug_${normalizeIdentity(debugIdentity.value)}`;
    const loginData = await wxLogin({
      code,
      nickname: `Web ${normalizeIdentity(debugIdentity.value)}`,
      avatar_url: '',
      gender: '',
    });
    sessionStore.setTokenMeta(loginData.token, loginData.expired_at || '');
    sessionStore.setUserInfo(loginData.user);
    if (loginData.user && loginData.user.settings) {
      sessionStore.setSettings(loginData.user.settings);
    }
    try {
      const currentPlan = await getCurrentPlan();
      sessionStore.setCurrentPlan(currentPlan && currentPlan.id ? currentPlan : null);
    } catch (error) {
      sessionStore.setCurrentPlan(null);
    }
    router.replace(String(redirectTarget.value));
  } catch (error) {
    loginError.value = error.message || '登录失败，请确认后端已启动';
  } finally {
    loading.value = false;
  }
}

loadBootstrap();
</script>

<template>
  <div class="login-screen">
    <div class="login-panel">
      <div class="login-kicker">GAClearn Web</div>
      <h1 class="login-title">让网页端和小程序端共用同一份学习进度</h1>
      <p class="login-description">
        这里先使用共享学习身份登录。你在小程序和网页里输入同一个身份标识，就会读到同一位用户的学习计划、复习进度、错词本和 AI 结果。
      </p>

      <div class="form-block">
        <label class="field-label" for="identity">共享学习身份</label>
        <input id="identity" v-model="debugIdentity" class="text-input" placeholder="例如 xb_home 或 webtester" />
      </div>

      <button class="primary-button wide" type="button" :disabled="loading" @click="handleLogin">
        {{ loading ? '登录中...' : '进入网页学习空间' }}
      </button>
      <div v-if="loginError" class="notice error">{{ loginError }}</div>

      <div class="info-panel">
        <div class="info-panel-title">当前登录说明</div>
        <p>{{ loginModeText }}</p>
        <ul class="plain-list">
          <li v-for="tip in featureTips" :key="tip">{{ tip }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>
