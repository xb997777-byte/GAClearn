const aiApi = require('../../services/modules/ai');
const booksApi = require('../../services/modules/books');
const plansApi = require('../../services/modules/plans');
const store = require('../../store/app-store');
const router = require('../../utils/router');
const { withThemePage } = require('../../utils/theme-manager');

function showActionSheetAsync(itemList) {
  return new Promise((resolve, reject) => {
    wx.showActionSheet({
      itemList,
      success: resolve,
      fail: reject
    });
  });
}

function getPlanStatusText(plan) {
  const status = plan && plan.status;
  if (status === 'paused') {
    return '已暂停';
  }
  if (status === 'completed') {
    return '已完成';
  }
  return '进行中';
}

Page(withThemePage({
  data: {
    bookId: 0,
    book: null,
    currentPlan: null,
    hasCurrentPlan: false,
    selectedBookIsCurrent: false,
    planStatusText: '',
    saveButtonText: '保存并开始',
    selectedTarget: 20,
    targetOptions: [],
    pageLoading: true,
    planActionLoading: false,
    aiPlanLoading: false,
    aiPlanApplying: false,
    aiPlanResult: null,
    planHistory: []
  },

  async onLoad(options) {
    const pageOptions = options || {};
    this.pendingOptions = pageOptions;
    this.pendingBookId = Number(pageOptions.bookId || 0);
    const storedPlan = store.getState().currentPlan;
    const selectedTarget = Number(pageOptions.dailyTarget || (storedPlan && storedPlan.daily_target) || 20);
    this.setData({
      selectedTarget,
      pageLoading: true
    });
    this.refreshTargets(selectedTarget);
    await this.loadCurrentPlan();
    await this.loadSelectedBook();
    await this.loadPlanHistory();
    this.initializeBook(this.data.currentPlan || storedPlan);
    this.setData({ pageLoading: false });
  },

  async loadCurrentPlan() {
    try {
      const currentPlan = await plansApi.getCurrentPlan();
      store.setCurrentPlan(currentPlan);
      const shouldUsePlanTarget = !Number(this.pendingOptions && this.pendingOptions.dailyTarget);
      if (currentPlan && shouldUsePlanTarget) {
        this.setData({ selectedTarget: Number(currentPlan.daily_target || 20) });
        this.refreshTargets(Number(currentPlan.daily_target || 20));
      }
      this.setData({
        currentPlan: currentPlan || null,
        hasCurrentPlan: !!currentPlan
      });
      this.refreshPlanPresentation();
    } catch (error) {
      const fallbackPlan = store.getState().currentPlan || null;
      this.setData({
        currentPlan: fallbackPlan,
        hasCurrentPlan: !!fallbackPlan
      });
      this.refreshPlanPresentation();
    }
  },

  async loadPlanHistory() {
    try {
      const data = await plansApi.getPlanHistory(6);
      this.setData({ planHistory: (data && data.list) || [] });
    } catch (error) {
      this.setData({ planHistory: [] });
    }
  },

  async loadSelectedBook() {
    if (!this.pendingBookId) {
      return;
    }
    try {
      const book = await booksApi.getBookDetail(this.pendingBookId);
      this.setData({
        bookId: Number(book.id || this.pendingBookId),
        book: book || null
      });
      this.refreshPlanPresentation();
    } catch (error) {
      // ignore selected book fallback and keep current plan book
    }
  },

  initializeBook(currentPlan) {
    if (this.pendingBookId && Number(this.data.bookId || 0) === this.pendingBookId && this.data.book) {
      this.refreshPlanPresentation();
      return;
    }
    const planBook = currentPlan && currentPlan.book ? currentPlan.book : null;
    this.setData({
      bookId: planBook ? Number(planBook.id) : 0,
      book: planBook || null
    });
    this.refreshPlanPresentation();
  },

  refreshPlanPresentation() {
    const currentPlan = this.data.currentPlan;
    const currentBookId = currentPlan && currentPlan.book ? Number(currentPlan.book.id) : 0;
    const selectedBookIsCurrent = !!(currentBookId && currentBookId === Number(this.data.bookId || 0));
    let saveButtonText = '保存并开始';
    if (currentPlan && selectedBookIsCurrent) {
      saveButtonText = '保存调整';
    } else if (currentPlan) {
      saveButtonText = '切换到当前词书';
    }

    this.setData({
      hasCurrentPlan: !!currentPlan,
      selectedBookIsCurrent,
      planStatusText: currentPlan ? getPlanStatusText(currentPlan) : '',
      saveButtonText
    });
  },

  refreshTargets(selectedTarget) {
    const base = [10, 20, 30, 50];
    this.setData({
      targetOptions: base.map((item) => ({
        value: item,
        className: item === Number(selectedTarget) ? 'segmented-item active' : 'segmented-item'
      }))
    });
  },

  chooseTarget(event) {
    const value = Number(event.currentTarget.dataset.value);
    this.setData({ selectedTarget: value });
    this.refreshTargets(value);
  },

  async runAiReplan() {
    if (this.data.aiPlanLoading) {
      return;
    }
    this.setData({ aiPlanLoading: true });
    try {
      const result = await aiApi.replanStudyPlan({ trend_days: 7 });
      this.setData({ aiPlanResult: result || null });
    } catch (error) {
      wx.showToast({ title: (error.message || 'AI 计划生成失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ aiPlanLoading: false });
    }
  },

  async applyAiPlanResult() {
    const patch = ((this.data.aiPlanResult || {}).plan_patch) || {};
    if (!patch || !patch.daily_target) {
      wx.showToast({ title: '当前没有可应用调整', icon: 'none' });
      return;
    }
    this.setData({ aiPlanApplying: true });
    try {
      const plan = await plansApi.applyAiPlanPatch({
        patch,
        summary: this.data.aiPlanResult.headline || 'apply ai patch',
        evidence: this.data.aiPlanResult.evidence || {}
      });
      this.syncSavedPlan(plan);
      await this.loadPlanHistory();
      wx.showToast({ title: 'AI 调整已应用', icon: 'success' });
    } catch (error) {
      wx.showToast({ title: (error.message || '应用失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ aiPlanApplying: false });
    }
  },

  goAiCenterPlan() {
    router.go('/pages/ai-center/index?tab=agent');
  },

  goBooks() {
    wx.switchTab({ url: '/pages/books/index' });
  },

  syncSavedPlan(plan) {
    store.setCurrentPlan(plan);
    if (plan && plan.daily_target) {
      store.setSettings({ daily_target: plan.daily_target });
    }
    this.setData({
      currentPlan: plan || null,
      hasCurrentPlan: !!plan
    });
    this.initializeBook(plan);
  },

  async handleSavePlan() {
    if (!this.data.bookId) {
      wx.showToast({ title: '请先去词书页选择词书', icon: 'none' });
      return;
    }

    this.setData({ planActionLoading: true });
    try {
      const currentPlan = this.data.currentPlan;
      let plan;
      if (currentPlan && this.data.selectedBookIsCurrent) {
        plan = await plansApi.updateCurrentPlan({
          daily_target: this.data.selectedTarget
        });
        this.syncSavedPlan(plan);
        wx.showToast({ title: '计划已更新', icon: 'success' });
        return;
      }

      if (currentPlan) {
        let keepProgress = false;
        try {
          const action = await showActionSheetAsync(['保留旧进度并切换', '重新开始当前词书']);
          keepProgress = action.tapIndex === 0;
        } catch (error) {
          return;
        }
        plan = await plansApi.switchBook({
          book_id: this.data.bookId,
          daily_target: this.data.selectedTarget,
          keep_progress: keepProgress
        });
        this.syncSavedPlan(plan);
        wx.showToast({ title: '词书已切换', icon: 'success' });
        router.relaunch('/pages/home/index');
        return;
      }

      plan = await plansApi.createPlan({
        book_id: this.data.bookId,
        daily_target: this.data.selectedTarget
      });
      this.syncSavedPlan(plan);
      wx.showToast({ title: '计划已保存', icon: 'success' });
      router.relaunch('/pages/home/index');
    } catch (error) {
      wx.showToast({ title: (error.message || '保存失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ planActionLoading: false });
    }
  },

  async handlePausePlan() {
    if (!this.data.currentPlan) {
      return;
    }
    this.setData({ planActionLoading: true });
    try {
      const plan = await plansApi.updateCurrentPlan({ status: 'paused' });
      this.syncSavedPlan(plan);
      wx.showToast({ title: '计划已暂停', icon: 'success' });
    } catch (error) {
      wx.showToast({ title: (error.message || '暂停失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ planActionLoading: false });
    }
  },

  async handleResumePlan() {
    if (!this.data.currentPlan) {
      return;
    }
    this.setData({ planActionLoading: true });
    try {
      const plan = await plansApi.updateCurrentPlan({ status: 'active' });
      this.syncSavedPlan(plan);
      wx.showToast({ title: '计划已恢复', icon: 'success' });
    } catch (error) {
      wx.showToast({ title: (error.message || '恢复失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ planActionLoading: false });
    }
  }
}));
