const learnApi = require('../../services/modules/learn');
const router = require('../../utils/router');
const { withThemePage } = require('../../utils/theme-manager');

Page(withThemePage({
  data: {
    list: [],
  },

  onShow() {
    this.loadData();
  },

  async loadData() {
    const data = await learnApi.listFavorites();
    this.setData({ list: data.list || [] });
  },

  async handleDelete(event) {
    const { wordId } = event.currentTarget.dataset;
    await learnApi.removeFavorite(wordId);
    wx.showToast({ title: '已取消收藏', icon: 'success' });
    this.loadData();
  },

  goDetail(event) {
    const { wordId } = event.currentTarget.dataset;
    router.go(`/pages/word-detail/index?id=${wordId}`);
  },
}));
