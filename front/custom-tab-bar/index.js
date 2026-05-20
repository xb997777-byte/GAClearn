const { getCurrentThemeId, getTabBarThemeData } = require('../utils/theme-manager');

Component({
  data: {
    selected: 0,
    tabBarStyle: '',
    tabTextStyle: '',
    tabActiveTextStyle: '',
    tabIconStyle: '',
    tabActiveIconStyle: '',
    tabActiveSurfaceStyle: '',
    list: [
      { pagePath: '/pages/home/index', text: '首页', short: '首' },
      { pagePath: '/pages/books/index', text: '词书', short: '书' },
      { pagePath: '/pages/grammar/index', text: '语法', short: '语' },
      { pagePath: '/pages/ai-center/index', text: 'AI', short: 'AI' },
      { pagePath: '/pages/profile/index', text: '我的', short: '我' },
    ],
  },

  lifetimes: {
    attached() {
      this.applyTheme(getTabBarThemeData(getCurrentThemeId()));
    }
  },

  methods: {
    applyTheme(themeData) {
      this.setData(themeData || getTabBarThemeData(getCurrentThemeId()));
    },

    switchTab(event) {
      const { path, index } = event.currentTarget.dataset;
      if (this.data.selected === index) {
        return;
      }
      this.setData({ selected: index });
      wx.switchTab({ url: path });
    },
  },
});
