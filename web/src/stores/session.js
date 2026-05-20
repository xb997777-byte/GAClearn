import { defineStore } from 'pinia';
import { STORAGE_KEYS } from '../config/env';
import { safeGet, safeRemove, safeSet } from '../lib/storage';

const defaultSettings = {
  daily_target: 20,
  reminder_time: '20:30:00',
  auto_play_audio: true,
  speech_speed: 1,
  review_enabled: true,
  review_batch_size: 8,
  theme_id: 'busuu_ocean',
  custom_theme: {},
  cefr_level: '',
  placement_score: 0,
  placement_completed_at: '',
  reminder_subscription_status: 'unknown',
  reminder_template_ids: [],
  last_reminder_sent_at: '',
  personalized_rag_enabled: false,
  personalized_rag_status: 'idle',
  personalized_rag_chunk_count: 0,
  personalized_rag_updated_at: '',
  personalized_rag_last_error: '',
};

export const useSessionStore = defineStore('session', {
  state: () => ({
    hydrated: false,
    token: '',
    tokenExpiredAt: '',
    userInfo: null,
    settings: { ...defaultSettings },
    currentPlan: null,
    aiPlanRun: null,
    aiPlanResult: null,
    aiCenterIntent: null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    hydrate() {
      if (this.hydrated) {
        return;
      }
      this.token = safeGet(STORAGE_KEYS.token, '');
      this.tokenExpiredAt = safeGet(`${STORAGE_KEYS.token}_expired_at`, '');
      this.userInfo = safeGet(STORAGE_KEYS.userInfo, null);
      this.settings = {
        ...defaultSettings,
        ...safeGet(STORAGE_KEYS.settings, {}),
      };
      this.currentPlan = safeGet(STORAGE_KEYS.plan, null);
      this.aiPlanRun = safeGet(STORAGE_KEYS.aiPlanRun, null);
      this.aiPlanResult = safeGet(STORAGE_KEYS.aiPlanResult, null);
      this.aiCenterIntent = safeGet(STORAGE_KEYS.aiIntent, null);
      this.hydrated = true;
    },
    setToken(token) {
      this.token = token || '';
      safeSet(STORAGE_KEYS.token, this.token);
    },
    setTokenMeta(token, expiredAt = '') {
      this.setToken(token);
      this.tokenExpiredAt = expiredAt || '';
      if (this.tokenExpiredAt) {
        safeSet(`${STORAGE_KEYS.token}_expired_at`, this.tokenExpiredAt);
        return;
      }
      safeRemove(`${STORAGE_KEYS.token}_expired_at`);
    },
    setUserInfo(userInfo) {
      this.userInfo = userInfo || null;
      safeSet(STORAGE_KEYS.userInfo, this.userInfo);
    },
    setSettings(settings) {
      this.settings = {
        ...this.settings,
        ...(settings || {}),
      };
      safeSet(STORAGE_KEYS.settings, this.settings);
    },
    setCurrentPlan(plan) {
      this.currentPlan = plan || null;
      safeSet(STORAGE_KEYS.plan, this.currentPlan);
    },
    setAiPlanRun(run) {
      this.aiPlanRun = run || null;
      if (this.aiPlanRun) {
        safeSet(STORAGE_KEYS.aiPlanRun, this.aiPlanRun);
      } else {
        safeRemove(STORAGE_KEYS.aiPlanRun);
      }
    },
    setAiPlanResult(result) {
      this.aiPlanResult = result || null;
      if (this.aiPlanResult) {
        safeSet(STORAGE_KEYS.aiPlanResult, this.aiPlanResult);
      } else {
        safeRemove(STORAGE_KEYS.aiPlanResult);
      }
    },
    setAiCenterIntent(intent) {
      this.aiCenterIntent = intent || null;
      if (this.aiCenterIntent) {
        safeSet(STORAGE_KEYS.aiIntent, this.aiCenterIntent);
      } else {
        safeRemove(STORAGE_KEYS.aiIntent);
      }
    },
    clearAuth() {
      this.token = '';
      this.tokenExpiredAt = '';
      this.userInfo = null;
      this.currentPlan = null;
      this.aiPlanRun = null;
      this.aiPlanResult = null;
      this.aiCenterIntent = null;
      safeRemove(STORAGE_KEYS.token);
      safeRemove(`${STORAGE_KEYS.token}_expired_at`);
      safeRemove(STORAGE_KEYS.userInfo);
      safeRemove(STORAGE_KEYS.plan);
      safeRemove(STORAGE_KEYS.aiPlanRun);
      safeRemove(STORAGE_KEYS.aiPlanResult);
      safeRemove(STORAGE_KEYS.aiIntent);
    },
  },
});
