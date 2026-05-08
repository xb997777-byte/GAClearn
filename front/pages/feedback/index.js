const authApi = require('../../services/modules/auth');
const { withThemePage } = require('../../utils/theme-manager');

const CATEGORY_OPTIONS = [
  { value: 'experience', label: '使用体验' },
  { value: 'bug', label: '问题反馈' },
  { value: 'content', label: '内容纠错' },
  { value: 'ai', label: 'AI 功能' },
  { value: 'other', label: '其他' }
];

function decorateCategories(activeValue) {
  return CATEGORY_OPTIONS.map((item) => ({
    value: item.value,
    label: item.label,
    className: item.value === activeValue ? 'feedback-chip active' : 'feedback-chip'
  }));
}

function getSystemInfo() {
  try {
    if (wx.getDeviceInfo && wx.getWindowInfo && wx.getAppBaseInfo) {
      const deviceInfo = wx.getDeviceInfo();
      const windowInfo = wx.getWindowInfo();
      const appBaseInfo = wx.getAppBaseInfo();
      return {
        brand: deviceInfo.brand || '',
        model: deviceInfo.model || '',
        system: deviceInfo.system || '',
        platform: deviceInfo.platform || '',
        version: appBaseInfo.version || '',
        SDKVersion: appBaseInfo.SDKVersion || '',
        windowWidth: windowInfo.windowWidth || 0,
        windowHeight: windowInfo.windowHeight || 0
      };
    }
    const info = wx.getSystemInfoSync ? wx.getSystemInfoSync() : {};
    return {
      brand: info.brand || '',
      model: info.model || '',
      system: info.system || '',
      platform: info.platform || '',
      version: info.version || '',
      SDKVersion: info.SDKVersion || ''
    };
  } catch (error) {
    return {};
  }
}

Page(withThemePage({
  data: {
    category: 'experience',
    categoryOptions: decorateCategories('experience'),
    content: '',
    contentLength: 0,
    contact: '',
    submitting: false
  },

  handleCategorySelect(event) {
    const { value } = event.currentTarget.dataset;
    if (!value) {
      return;
    }
    this.setData({
      category: value,
      categoryOptions: decorateCategories(value)
    });
  },

  handleContentInput(event) {
    const content = event.detail.value || '';
    this.setData({
      content,
      contentLength: content.length
    });
  },

  handleContactInput(event) {
    this.setData({ contact: event.detail.value || '' });
  },

  async handleSubmit() {
    const content = String(this.data.content || '').trim();
    if (content.length < 5) {
      wx.showToast({ title: '请至少填写 5 个字', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    try {
      await authApi.submitFeedback({
        category: this.data.category,
        content,
        contact: String(this.data.contact || '').trim(),
        page: '/pages/feedback/index',
        app_version: (getApp().globalData && getApp().globalData.appVersion) || '',
        system_info: getSystemInfo()
      });
      wx.showToast({ title: '已提交', icon: 'success' });
      this.setData({
        content: '',
        contentLength: 0,
        contact: ''
      });
    } catch (error) {
      wx.showToast({ title: (error.message || '提交失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  }
}));
