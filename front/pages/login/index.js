const authApi = require('../../services/modules/auth');
const plansApi = require('../../services/modules/plans');
const systemApi = require('../../services/modules/system');
const router = require('../../utils/router');
const store = require('../../store/app-store');
const { withThemePage } = require('../../utils/theme-manager');

const DEFAULT_DEBUG_IDENTITY = 'local_tester';

function normalizeDebugIdentity(value) {
  const normalized = String(value || '')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '');
  return normalized || DEFAULT_DEBUG_IDENTITY;
}

function buildDebugCode(debugIdentity) {
  return `debug_${normalizeDebugIdentity(debugIdentity)}`;
}

function wxLoginAsync() {
  return new Promise((resolve, reject) => {
    wx.login({
      success: resolve,
      fail: reject
    });
  });
}

function wxGetUserProfileAsync() {
  return new Promise((resolve, reject) => {
    if (typeof wx.getUserProfile !== 'function') {
      reject(new Error('wx.getUserProfile unavailable'));
      return;
    }
    wx.getUserProfile({
      desc: '用于完善学习档案与跨设备同步',
      success: resolve,
      fail: reject
    });
  });
}

Page(withThemePage({
  data: {
    loading: false,
    hasToken: false,
    loginModeText: '正在检查登录模式...',
    featureTips: [],
    isMockLoginMode: false,
    debugIdentity: DEFAULT_DEBUG_IDENTITY
  },

  onShow() {
    const { token } = store.getState();
    this.setData({
      hasToken: !!token
    });
    this.loadBootstrap();
  },

  async loadBootstrap() {
    try {
      const bootstrap = await systemApi.getBootstrap();
      const features = (bootstrap && bootstrap.features) || {};
      const wechatLoginMode = features.wechat_login_mode || 'auto';
      const isMockLoginMode = wechatLoginMode === 'mock' || (wechatLoginMode === 'auto' && !features.wechat_login_enabled);
      const loginModeText = isMockLoginMode
        ? '当前正在使用开发调试登录。只要使用同一个测试账号标识登录，就会回到同一份学习数据。'
        : '当前后端已启用真实微信登录，点击后会走 wx.login + code2session。';
      const featureTips = [
        isMockLoginMode ? '当前模式：调试登录' : '当前模式：真实微信登录',
        features.ai_enabled ? '语法 AI：已启用' : '语法 AI：未配置',
        features.subscribe_reminder_enabled ? '订阅提醒：可用' : '订阅提醒：未配置模板'
      ];
      this.setData({
        loginModeText,
        featureTips,
        isMockLoginMode
      });
    } catch (error) {
      this.setData({
        loginModeText: '未能读取系统配置，将优先尝试真实登录，失败后回退调试登录。',
        featureTips: ['请确认后端已启动'],
        isMockLoginMode: false
      });
    }
  },

  handleDebugIdentityInput(event) {
    this.setData({
      debugIdentity: normalizeDebugIdentity(event.detail.value || '')
    });
  },

  async handleLogin() {
    this.setData({ loading: true });
    try {
      let profile = {};
      try {
        const profileRes = await wxGetUserProfileAsync();
        profile = (profileRes && profileRes.userInfo) || {};
      } catch (error) {
        console.warn('[login] getUserProfile skipped', error);
      }

      let code = '';
      if (this.data.isMockLoginMode) {
        code = buildDebugCode(this.data.debugIdentity);
      } else {
        try {
          const loginRes = await wxLoginAsync();
          code = loginRes && loginRes.code ? loginRes.code : '';
        } catch (error) {
          console.warn('[login] wx.login failed, use debug code', error);
        }
        if (!code) {
          code = buildDebugCode(this.data.debugIdentity);
        }
      }

      const loginData = await authApi.wxLogin({
        code,
        nickname: profile.nickName || '英语学习者',
        avatar_url: profile.avatarUrl || '',
        gender: profile.gender !== undefined ? String(profile.gender) : ''
      });

      store.setToken(loginData.token);
      store.setUserInfo(loginData.user);
      if (loginData.user && loginData.user.settings) {
        store.setSettings(loginData.user.settings);
      }

      try {
        const currentPlan = await plansApi.getCurrentPlan();
        store.setCurrentPlan(currentPlan);
      } catch (error) {
        store.setCurrentPlan(null);
      }

      wx.showToast({ title: '登录成功', icon: 'success' });
      router.relaunch('/pages/home/index');
    } catch (error) {
      console.error('[login] failed', error);
      const message = error && error.message ? error.message : '登录失败，请确认后端已启动';
      wx.showToast({ title: message.slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ loading: false });
    }
  },

  handleClearSession() {
    store.clearAuth();
    this.setData({
      hasToken: false
    });
    wx.showToast({ title: '已清除本地登录状态', icon: 'none' });
  }
}));
