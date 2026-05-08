const statsApi = require('../../services/modules/stats');
const { withThemePage } = require('../../utils/theme-manager');

Page(withThemePage({
  data: {
    overview: null,
    trend: [],
    checkins: [],
  },

  onShow() {
    this.loadData();
  },

  async loadData() {
    const [overview, trend, checkins] = await Promise.all([
      statsApi.getOverview(),
      statsApi.getTrend({ days: 7 }),
      statsApi.getCheckinHistory(),
    ]);
    this.setData({
      overview,
      trend: trend.list || [],
      checkins: checkins.list || [],
    });
  },

  async handleCheckin() {
    await statsApi.checkin();
    wx.showToast({ title: '打卡成功', icon: 'success' });
    this.loadData();
  },
}));
