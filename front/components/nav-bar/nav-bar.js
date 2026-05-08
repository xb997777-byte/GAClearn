function getLayoutMetrics() {
  let statusBarHeight = 20;
  try {
    if (typeof wx.getWindowInfo === 'function') {
      const windowInfo = wx.getWindowInfo();
      statusBarHeight = windowInfo.statusBarHeight || statusBarHeight;
    }
  } catch (error) {
    // fallback only when newer api is not available
  }

  if (statusBarHeight === 20) {
    try {
      const legacyInfo = wx.getSystemInfoSync();
      statusBarHeight = legacyInfo.statusBarHeight || statusBarHeight;
    } catch (error) {
      // keep default value
    }
  }

  let navHeight = 44;
  const menuRect = typeof wx.getMenuButtonBoundingClientRect === 'function'
    ? wx.getMenuButtonBoundingClientRect()
    : null;

  if (menuRect && statusBarHeight) {
    navHeight = menuRect.height + (menuRect.top - statusBarHeight) * 2;
  }

  return {
    statusBarHeight,
    navHeight
  };
}

Component({
  properties: {
    title: {
      type: String,
      value: ''
    },
    showBack: {
      type: Boolean,
      value: false
    },
    light: {
      type: Boolean,
      value: false
    }
  },

  data: {
    statusBarHeight: 20,
    navHeight: 44
  },

  lifetimes: {
    attached() {
      const metrics = getLayoutMetrics();
      this.setData(metrics);
    }
  },

  methods: {
    handleBack() {
      const pages = getCurrentPages();
      if (pages.length > 1) {
        wx.navigateBack({ delta: 1 });
      } else {
        wx.switchTab({ url: '/pages/home/index' });
      }
    }
  }
});
