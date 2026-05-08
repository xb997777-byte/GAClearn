const aiApi = require('../../services/modules/ai');
const reviewApi = require('../../services/modules/review');
const router = require('../../utils/router');
const { withThemePage } = require('../../utils/theme-manager');

Page(withThemePage({
  data: {
    list: [],
    wrongWordsCoach: null,
    wrongWordsCoachEvidence: null,
    wrongWordsCoachLoading: false,
    wrongWordsCoachError: ''
  },

  onShow() {
    this.loadData();
  },

  async loadData() {
    try {
      const data = await reviewApi.listWrongWords();
      const list = data.list || [];
      this.setData({ list });
      if (list.length) {
        this.loadWrongWordsCoach(true);
      } else {
        this.setData({
          wrongWordsCoach: null,
          wrongWordsCoachEvidence: null,
          wrongWordsCoachLoading: false,
          wrongWordsCoachError: ''
        });
      }
    } catch (error) {
      wx.showToast({ title: '错词本加载失败', icon: 'none' });
    }
  },

  async loadWrongWordsCoach(silent = false) {
    if (!this.data.list.length) {
      return;
    }
    this.setData({
      wrongWordsCoachLoading: true,
      wrongWordsCoachError: ''
    });
    try {
      const data = await aiApi.getWrongWordsReview({ limit: 12 });
      this.setData({
        wrongWordsCoach: data.review || null,
        wrongWordsCoachEvidence: data.evidence || null,
        wrongWordsCoachLoading: false,
        wrongWordsCoachError: ''
      });
    } catch (error) {
      this.setData({
        wrongWordsCoachLoading: false,
        wrongWordsCoachError: error.message || 'AI复盘失败'
      });
      if (!silent) {
        wx.showToast({ title: 'AI复盘失败', icon: 'none' });
      }
    }
  },

  handleReloadWrongWordsCoach() {
    this.loadWrongWordsCoach();
  },

  async handleDelete(event) {
    const { wordId } = event.currentTarget.dataset;
    await reviewApi.deleteWrongWord(wordId);
    wx.showToast({ title: '已移除', icon: 'success' });
    this.loadData();
  },

  goDetail(event) {
    const { wordId } = event.currentTarget.dataset;
    router.go(`/pages/word-detail/index?id=${wordId}`);
  },

  goAiCenterConversation() {
    router.go('/pages/ai-center/index?tab=apps&workspace=conversation');
  }
}));
