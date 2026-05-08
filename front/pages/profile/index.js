const authApi = require('../../services/modules/auth');
const router = require('../../utils/router');
const store = require('../../store/app-store');
const {
  applyTheme,
  CUSTOM_THEME_ID,
  DEFAULT_CUSTOM_THEME,
  HUE_PRESETS,
  getCurrentThemeId,
  getThemeOptions,
  getThemePreview,
  normalizeCustomTheme,
  setCurrentTheme,
  setCustomTheme,
  syncTabBar,
  withThemePage
} = require('../../utils/theme-manager');

function buildNormalizedSettings(rawSettings) {
  const mergedSettings = Object.assign({}, store.getState().settings || {}, rawSettings || {});
  mergedSettings.custom_theme = normalizeCustomTheme(mergedSettings.custom_theme || DEFAULT_CUSTOM_THEME);
  return mergedSettings;
}

Page(withThemePage({
  data: {
    user: null,
    settings: null,
    displayName: '学习者',
    currentThemeId: getCurrentThemeId(),
    customThemeId: CUSTOM_THEME_ID,
    themeOptions: getThemeOptions(),
    activeTheme: getThemePreview(getCurrentThemeId()),
    customThemeDraft: normalizeCustomTheme(DEFAULT_CUSTOM_THEME),
    customThemePreview: getThemePreview(CUSTOM_THEME_ID, DEFAULT_CUSTOM_THEME),
    huePresets: HUE_PRESETS,
    themeSaving: false
  },

  onShow() {
    getApp().setTabBarSelected(4);
    this.refreshThemeState(getCurrentThemeId());
    this.loadData();
  },

  async loadData() {
    try {
      const user = await authApi.getMe();
      const mergedSettings = buildNormalizedSettings((user && user.settings) || {});
      const themeId = mergedSettings.theme_id || getCurrentThemeId();
      store.setSettings(mergedSettings);
      this.setData({
        user,
        settings: mergedSettings,
        displayName: (user && user.nickname) || '学习者'
      });
      this.refreshThemeState(themeId, mergedSettings.custom_theme);
    } catch (error) {
      wx.showToast({ title: '加载失败，请重新登录', icon: 'none' });
    }
  },

  refreshThemeState(themeId, customTheme) {
    const resolvedThemeId = themeId || getCurrentThemeId();
    const normalizedCustomTheme = normalizeCustomTheme(
      customTheme ||
      (this.data.settings && this.data.settings.custom_theme) ||
      (store.getState().settings || {}).custom_theme ||
      DEFAULT_CUSTOM_THEME
    );

    this.setData({
      currentThemeId: resolvedThemeId,
      activeTheme: getThemePreview(resolvedThemeId, normalizedCustomTheme),
      customThemeDraft: normalizedCustomTheme,
      customThemePreview: getThemePreview(CUSTOM_THEME_ID, normalizedCustomTheme)
    });
    applyTheme(this, resolvedThemeId);
    syncTabBar(this, resolvedThemeId);
  },

  updateCustomThemeDraft(patch) {
    const nextDraft = normalizeCustomTheme(Object.assign({}, this.data.customThemeDraft || DEFAULT_CUSTOM_THEME, patch || {}));
    this.setData({
      customThemeDraft: nextDraft,
      customThemePreview: getThemePreview(CUSTOM_THEME_ID, nextDraft)
    });
  },

  handleHuePresetSelect(event) {
    const { hue } = event.currentTarget.dataset;
    if (hue === undefined) {
      return;
    }
    this.updateCustomThemeDraft({ base_hue: Number(hue) });
  },

  handleCustomThemeSlider(event) {
    const { field } = event.currentTarget.dataset;
    if (!field) {
      return;
    }
    this.updateCustomThemeDraft({ [field]: Number(event.detail.value) });
  },

  handleCustomGradientSwitch(event) {
    this.updateCustomThemeDraft({ gradient_enabled: !!event.detail.value });
  },

  handleCustomThemeReset() {
    const resetTheme = normalizeCustomTheme(DEFAULT_CUSTOM_THEME);
    this.setData({
      customThemeDraft: resetTheme,
      customThemePreview: getThemePreview(CUSTOM_THEME_ID, resetTheme)
    });
  },

  async handleCustomThemeApply() {
    const draft = normalizeCustomTheme(this.data.customThemeDraft || DEFAULT_CUSTOM_THEME);
    const nextSettings = buildNormalizedSettings(Object.assign({}, this.data.settings || {}, {
      theme_id: CUSTOM_THEME_ID,
      custom_theme: draft
    }));

    setCustomTheme(draft);
    this.setData({
      settings: nextSettings,
      themeSaving: true
    });
    this.refreshThemeState(CUSTOM_THEME_ID, draft);

    try {
      const savedSettings = await authApi.updateSettings({
        theme_id: CUSTOM_THEME_ID,
        custom_theme: draft
      });
      const finalSettings = buildNormalizedSettings(savedSettings || nextSettings);
      store.setSettings(finalSettings);
      this.setData({
        settings: finalSettings
      });
      this.refreshThemeState(CUSTOM_THEME_ID, finalSettings.custom_theme);
      wx.showToast({ title: '自定义主题已应用', icon: 'success' });
    } catch (error) {
      wx.showToast({ title: '本地已应用，云端同步稍后重试', icon: 'none' });
    } finally {
      this.setData({ themeSaving: false });
    }
  },

  async handleThemeSelect(event) {
    const { themeId } = event.currentTarget.dataset;
    if (!themeId || themeId === this.data.currentThemeId) {
      return;
    }

    const nextThemeId = setCurrentTheme(themeId);
    const mergedSettings = buildNormalizedSettings(Object.assign({}, this.data.settings || {}, {
      theme_id: nextThemeId
    }));
    store.setSettings(mergedSettings);

    this.setData({
      settings: mergedSettings,
      themeSaving: true
    });
    this.refreshThemeState(nextThemeId, mergedSettings.custom_theme);

    try {
      const savedSettings = await authApi.updateSettings({ theme_id: nextThemeId });
      const finalSettings = buildNormalizedSettings(savedSettings || mergedSettings);
      store.setSettings(finalSettings);
      this.setData({
        settings: finalSettings
      });
      this.refreshThemeState(nextThemeId, finalSettings.custom_theme);
      wx.showToast({ title: '主题已切换', icon: 'success' });
    } catch (error) {
      wx.showToast({ title: '主题已切换，云端同步稍后重试', icon: 'none' });
    } finally {
      this.setData({ themeSaving: false });
    }
  },

  goFavorites() {
    router.go('/pages/favorites/index');
  },

  goWrongWords() {
    router.go('/pages/wrong-words/index');
  },

  goFeedback() {
    router.go('/pages/feedback/index');
  },

  goPlan() {
    router.go('/pages/plan/index');
  },

  logout() {
    store.clearAuth();
    wx.showToast({ title: '已退出登录', icon: 'success' });
    router.relaunch('/pages/login/index');
  }
}));
