const { STORAGE_KEYS } = require('../config/env');
const { DEFAULT_CUSTOM_THEME } = require('../utils/custom-theme');

const DEFAULT_THEME_ID = 'busuu_ocean';
const LEGACY_THEME_MIGRATION_KEY = 'wxapp_theme_default_migrated_v1';

const state = {
  token: '',
  userInfo: null,
  settings: {
    daily_target: 20,
    reminder_time: '20:30:00',
    auto_play_audio: true,
    speech_speed: 1,
    review_enabled: true,
    theme_id: DEFAULT_THEME_ID,
    custom_theme: DEFAULT_CUSTOM_THEME,
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
    personalized_rag_last_error: ''
  },
  currentPlan: null,
  aiCenterIntent: null
};

function safeGet(key, fallback) {
  try {
    const value = wx.getStorageSync(key);
    return value === '' || value === undefined ? fallback : value;
  } catch (error) {
    return fallback;
  }
}

function safeSet(key, value) {
  try {
    wx.setStorageSync(key, value);
  } catch (error) {
    // ignore
  }
}

function safeRemove(key) {
  try {
    wx.removeStorageSync(key);
  } catch (error) {
    // ignore
  }
}

function hydrate() {
  state.token = safeGet(STORAGE_KEYS.token, '');
  if (String(state.token || '').indexOf('mock-token-') === 0) {
    state.token = '';
    safeRemove(STORAGE_KEYS.token);
  }
  state.userInfo = safeGet(STORAGE_KEYS.userInfo, null);
  const storedSettings = Object.assign({}, state.settings, safeGet(STORAGE_KEYS.settings, {}));
  const hasMigratedLegacyTheme = safeGet(LEGACY_THEME_MIGRATION_KEY, false);
  if (!hasMigratedLegacyTheme && storedSettings.theme_id === 'duo_forest') {
    storedSettings.theme_id = DEFAULT_THEME_ID;
    safeSet(STORAGE_KEYS.settings, storedSettings);
    safeSet(LEGACY_THEME_MIGRATION_KEY, true);
  }
  state.settings = storedSettings;
  state.currentPlan = safeGet(STORAGE_KEYS.plan, null);
  state.aiCenterIntent = safeGet(STORAGE_KEYS.aiIntent, null);
  return state;
}

function getState() {
  return state;
}

function setToken(token) {
  state.token = token || '';
  safeSet(STORAGE_KEYS.token, state.token);
}

function setUserInfo(userInfo) {
  state.userInfo = userInfo || null;
  safeSet(STORAGE_KEYS.userInfo, state.userInfo);
}

function setSettings(settings) {
  state.settings = Object.assign({}, state.settings, settings || {});
  safeSet(STORAGE_KEYS.settings, state.settings);
}

function setCurrentPlan(plan) {
  state.currentPlan = plan || null;
  safeSet(STORAGE_KEYS.plan, state.currentPlan);
}

function setAiCenterIntent(intent) {
  state.aiCenterIntent = intent || null;
  if (state.aiCenterIntent) {
    safeSet(STORAGE_KEYS.aiIntent, state.aiCenterIntent);
    return;
  }
  safeRemove(STORAGE_KEYS.aiIntent);
}

function consumeAiCenterIntent() {
  const intent = state.aiCenterIntent || null;
  state.aiCenterIntent = null;
  safeRemove(STORAGE_KEYS.aiIntent);
  return intent;
}

function clearAuth() {
  state.token = '';
  state.userInfo = null;
  state.currentPlan = null;
  state.aiCenterIntent = null;
  safeRemove(STORAGE_KEYS.token);
  safeRemove(STORAGE_KEYS.userInfo);
  safeRemove(STORAGE_KEYS.plan);
  safeRemove(STORAGE_KEYS.aiIntent);
}

module.exports = {
  hydrate,
  getState,
  setToken,
  setUserInfo,
  setSettings,
  setCurrentPlan,
  setAiCenterIntent,
  consumeAiCenterIntent,
  clearAuth
};
