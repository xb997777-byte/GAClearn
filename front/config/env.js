const BASE_URL = 'http://127.0.0.1:8001';

const STORAGE_KEYS = {
  token: 'wxapp_token',
  userInfo: 'wxapp_user_info',
  settings: 'wxapp_settings',
  plan: 'wxapp_current_plan',
  aiIntent: 'wxapp_ai_center_intent'
};

module.exports = {
  APP_NAME: '英语单词学习',
  BASE_URL,
  API_PREFIX: '/api/v1',
  REQUEST_TIMEOUT: 8000,
  STORAGE_KEYS
};
