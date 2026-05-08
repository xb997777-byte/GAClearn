const authApi = require('../../services/modules/auth');
const systemApi = require('../../services/modules/system');
const speech = require('../../utils/speech');
const store = require('../../store/app-store');
const { withThemePage } = require('../../utils/theme-manager');

const SPEECH_SPEED_OPTIONS = [1, 0.9, 0.8, 0.7];

function decorateSpeechSpeedOptions(activeSpeed) {
  const normalizedActiveSpeed = speech.normalizeSpeechSpeed(activeSpeed || 1);
  return SPEECH_SPEED_OPTIONS.map((speed) => ({
    value: speed,
    label: `${speed.toFixed(1)}x`,
    className: speed === normalizedActiveSpeed ? 'speed-chip active' : 'speed-chip'
  }));
}

function requestSubscribeMessageAsync(tmplIds) {
  return new Promise((resolve, reject) => {
    wx.requestSubscribeMessage({
      tmplIds,
      success: resolve,
      fail: reject
    });
  });
}

Page(withThemePage({
  data: {
    user: null,
    settings: null,
    features: {},
    saving: false,
    personalizedRagBuilding: false,
    playbackReady: speech.isSpeechPlaybackReady(),
    speechSpeedOptions: decorateSpeechSpeedOptions(1)
  },

  onShow() {
    this.loadPage();
  },

  async loadPage() {
    try {
      const [user, bootstrap] = await Promise.all([
        authApi.getMe(),
        systemApi.getBootstrap().catch(() => ({ features: {} }))
      ]);
      const settings = Object.assign({}, store.getState().settings || {}, (user && user.settings) || {});
      store.setSettings(settings);
      this.setData({
        user,
        settings,
        features: (bootstrap && bootstrap.features) || {},
        speechSpeedOptions: decorateSpeechSpeedOptions(settings.speech_speed)
      });
    } catch (error) {
      wx.showToast({ title: '加载设置失败', icon: 'none' });
    }
  },

  async savePatch(patch, successTitle) {
    const nextSettings = Object.assign({}, this.data.settings || {}, patch || {});
    this.setData({
      settings: nextSettings,
      saving: true
    });
    store.setSettings(nextSettings);
    try {
      const saved = await authApi.updateSettings(patch || {});
      const finalSettings = Object.assign({}, nextSettings, saved || {});
      store.setSettings(finalSettings);
      this.setData({
        settings: finalSettings,
        speechSpeedOptions: decorateSpeechSpeedOptions(finalSettings.speech_speed)
      });
      if (successTitle) {
        wx.showToast({ title: successTitle, icon: 'success' });
      }
    } catch (error) {
      wx.showToast({ title: (error.message || '保存失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ saving: false });
    }
  },

  handleReminderTimeChange(event) {
    this.savePatch({ reminder_time: event.detail.value }, '提醒时间已更新');
  },

  handleAutoAudioChange(event) {
    this.savePatch({ auto_play_audio: !!event.detail.value }, '发音设置已更新');
  },

  handleSpeechSpeedSelect(event) {
    const speedValue = speech.normalizeSpeechSpeed(event.currentTarget.dataset.speed);
    this.savePatch({ speech_speed: speedValue }, '语速已更新');
  },

  handleReviewEnabledChange(event) {
    this.savePatch({ review_enabled: !!event.detail.value }, '复习设置已更新');
  },

  handlePersonalizedRagToggle(event) {
    const enabled = !!event.detail.value;
    this.savePatch(
      { personalized_rag_enabled: enabled },
      enabled ? '个性化 RAG 已开启' : '个性化 RAG 已关闭'
    );
  },

  async handleRebuildPersonalizedRag() {
    if (this.data.personalizedRagBuilding) {
      return;
    }
    if (!(this.data.settings && this.data.settings.personalized_rag_enabled)) {
      wx.showToast({ title: '请先开启个性化 RAG', icon: 'none' });
      return;
    }

    this.setData({ personalizedRagBuilding: true });
    try {
      const result = await authApi.rebuildPersonalizedRag();
      const nextSettings = Object.assign({}, this.data.settings || {}, (result && result.settings) || {});
      store.setSettings(nextSettings);
      this.setData({ settings: nextSettings });
      wx.showToast({ title: '个性知识库已刷新', icon: 'success' });
    } catch (error) {
      wx.showToast({ title: (error.message || '构建失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ personalizedRagBuilding: false });
    }
  },

  async handleSubscribeReminders() {
    const tmplIds = (this.data.features && this.data.features.subscribe_template_ids) || [];
    if (!tmplIds.length) {
      wx.showToast({ title: '后端未配置提醒模板', icon: 'none' });
      return;
    }
    try {
      const result = await requestSubscribeMessageAsync(tmplIds);
      const acceptedIds = tmplIds.filter((id) => result[id] === 'accept');
      await this.savePatch(
        {
          reminder_subscription_status: acceptedIds.length ? 'accepted' : 'rejected',
          reminder_template_ids: acceptedIds
        },
        acceptedIds.length ? '提醒订阅已开启' : '未接受提醒订阅'
      );
    } catch (error) {
      wx.showToast({ title: (error.errMsg || error.message || '订阅失败').slice(0, 20), icon: 'none' });
    }
  },

  async handlePlayDemo() {
    try {
      await speech.speakText('Today is a good day to keep learning English.', { lang: 'en-US' });
    } catch (error) {
      wx.showToast({ title: (error.message || '播放失败').slice(0, 20), icon: 'none' });
    }
  },

  async handlePlacementRetest() {
    wx.navigateTo({ url: '/pages/exam/index?mode=placement' });
  },

  async handlePracticeTest() {
    wx.navigateTo({ url: '/pages/exam/index?mode=practice' });
  }
}));
