const LOCAL_BASE_URL = 'http://127.0.0.1:8000';
const LAN_BASE_URL = 'http://172.20.10.14:8000';
const FORCE_LAN = false;

function resolveBaseUrl() {
  if (FORCE_LAN) {
    return LAN_BASE_URL;
  }
  if (typeof wx !== 'undefined' && wx && typeof wx.getSystemInfoSync === 'function') {
    try {
      const info = wx.getSystemInfoSync() || {};
      const platform = String(info.platform || '').toLowerCase();
      const brand = String(info.brand || '').toLowerCase();
      if (platform && platform !== 'devtools') {
        return LAN_BASE_URL;
      }
      if (brand && brand.indexOf('devtools') === -1 && platform !== 'devtools') {
        return LAN_BASE_URL;
      }
    } catch (error) {
      // ignore and fallback
    }
  }
  return LOCAL_BASE_URL;
}

const BASE_URL = resolveBaseUrl();

const STORAGE_KEYS = {
  token: 'wxapp_token',
  userInfo: 'wxapp_user_info',
  settings: 'wxapp_settings',
  plan: 'wxapp_current_plan',
  aiIntent: 'wxapp_ai_center_intent',
  aiPlanRun: 'wxapp_ai_plan_replan_run',
  aiPlanResult: 'wxapp_ai_plan_replan_result'
};

module.exports = {
  APP_NAME: '英语单词学习',
  BASE_URL,
  LOCAL_BASE_URL,
  LAN_BASE_URL,
  API_PREFIX: '/api/v1',
  REQUEST_TIMEOUT: 8000,
  STORAGE_KEYS
};
