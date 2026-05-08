const store = require('./store/app-store');

App({
  onLaunch() {
    store.hydrate();
  },

  globalData: {
    appName: '英语单词学习',
  },

  setTabBarSelected(index) {
    const pages = typeof getCurrentPages === 'function' ? getCurrentPages() : [];
    const currentPage = pages.length ? pages[pages.length - 1] : null;
    if (!currentPage || typeof currentPage.getTabBar !== 'function') {
      return;
    }
    const tabBar = currentPage.getTabBar();
    if (tabBar && typeof tabBar.setData === 'function') {
      tabBar.setData({ selected: index });
    }
  },
});
