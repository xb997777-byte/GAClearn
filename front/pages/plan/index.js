const aiApi = require('../../services/modules/ai');
const booksApi = require('../../services/modules/books');
const plansApi = require('../../services/modules/plans');
const store = require('../../store/app-store');
const router = require('../../utils/router');
const { withThemePage } = require('../../utils/theme-manager');

const DEFAULT_REVIEW_BATCH_SIZE = 8;
const MIN_REVIEW_BATCH_SIZE = 1;
const MAX_REVIEW_BATCH_SIZE = 50;
const REVIEW_BATCH_OPTIONS = [5, 8, 12, 20, 30, 50];

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

function buildAiPlanRunSnapshot(runId, sourcePage) {
  return {
    run_id: runId || '',
    source_page: sourcePage || 'plan',
    feature_type: 'plan_replan',
    updated_at: Date.now()
  };
}

function buildPollingControlError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}

function normalizeReviewBatchSize(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_REVIEW_BATCH_SIZE;
  }
  return Math.min(MAX_REVIEW_BATCH_SIZE, Math.max(MIN_REVIEW_BATCH_SIZE, Math.round(parsed)));
}

Page(withThemePage({
  data: {
    minDailyTarget: 1,
    maxDailyTarget: 200,
    bookId: 0,
    book: null,
    currentPlan: null,
    hasCurrentPlan: false,
    selectedBookIsCurrent: false,
    planStatusText: '',
    saveButtonText: '保存并开始',
    selectedTarget: 20,
    targetInputValue: '20',
    targetInputError: '',
    targetOptions: [],
    todayTask: null,
    todayNewWordTarget: 0,
    todayReviewWordTarget: 0,
    reviewBatchSize: DEFAULT_REVIEW_BATCH_SIZE,
    reviewBatchOptions: [],
    reviewBatchInputValue: String(DEFAULT_REVIEW_BATCH_SIZE),
    reviewBatchInputError: '',
    scrollIntoViewTarget: '',
    pageLoading: true,
    planActionLoading: false,
    aiPlanLoading: false,
    aiPlanRefreshing: false,
    aiPlanApplying: false,
    aiPlanRunId: '',
    aiPlanRunDetail: null,
    aiPlanRunSteps: [],
    aiPlanRunArtifacts: [],
    aiPlanRuntimeCollapsed: true,
    aiPlanStatusText: '',
    aiPlanResultHighlight: false,
    aiPlanResult: null,
    planHistory: []
  },

  async onLoad(options) {
    const pageOptions = options || {};
    this.pendingOptions = pageOptions;
    this.pendingBookId = Number(pageOptions.bookId || 0);
    const storedPlan = store.getState().currentPlan;
    const selectedTarget = this.normalizeTargetValue(pageOptions.dailyTarget || (storedPlan && storedPlan.daily_target) || 20);
    const reviewBatchSize = normalizeReviewBatchSize((store.getState().settings || {}).review_batch_size);
    this.setData({
      selectedTarget,
      targetInputValue: String(selectedTarget),
      reviewBatchSize,
      reviewBatchInputValue: String(reviewBatchSize),
      targetInputError: '',
      reviewBatchInputError: '',
      pageLoading: true
    });
    this.refreshTargets(selectedTarget);
    this.refreshReviewBatchOptions(reviewBatchSize);
    await this.loadCurrentPlan();
    await this.loadTodayTask();
    await this.loadSelectedBook();
    await this.loadPlanHistory();
    this.initializeBook(this.data.currentPlan || storedPlan);
    this.setData({ pageLoading: false });
    this.resumeAiPlanRunIfNeeded();
  },

  async loadCurrentPlan() {
    try {
      const currentPlan = await plansApi.getCurrentPlan();
      store.setCurrentPlan(currentPlan);
      const shouldUsePlanTarget = !Number(this.pendingOptions && this.pendingOptions.dailyTarget);
      if (currentPlan && shouldUsePlanTarget) {
        const selectedTarget = this.normalizeTargetValue(currentPlan.daily_target || 20);
        this.setData({
          selectedTarget,
          targetInputValue: String(selectedTarget),
          targetInputError: ''
        });
        this.refreshTargets(selectedTarget);
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

  async loadTodayTask() {
    try {
      const todayTask = await plansApi.getTodayTask();
      const task = (todayTask && todayTask.task) || null;
      const reviewBatchSize = normalizeReviewBatchSize((store.getState().settings || {}).review_batch_size);
      this.setData({
        todayTask: task,
        todayNewWordTarget: Number((task && task.new_word_target) || (this.data.currentPlan && this.data.currentPlan.daily_target) || 0),
        todayReviewWordTarget: Number((task && task.review_word_target) || 0),
        reviewBatchSize,
        reviewBatchInputValue: String(reviewBatchSize),
        reviewBatchInputError: ''
      });
      this.refreshReviewBatchOptions(reviewBatchSize);
    } catch (error) {
      const reviewBatchSize = normalizeReviewBatchSize((store.getState().settings || {}).review_batch_size);
      this.setData({
        todayTask: null,
        todayNewWordTarget: Number((this.data.currentPlan && this.data.currentPlan.daily_target) || 0),
        todayReviewWordTarget: 0,
        reviewBatchSize,
        reviewBatchInputValue: String(reviewBatchSize),
        reviewBatchInputError: ''
      });
      this.refreshReviewBatchOptions(reviewBatchSize);
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

  refreshReviewBatchOptions(selectedValue) {
    this.setData({
      reviewBatchOptions: REVIEW_BATCH_OPTIONS.map((item) => ({
        value: item,
        className: item === Number(selectedValue) ? 'segmented-item active' : 'segmented-item'
      }))
    });
  },

  normalizeTargetValue(value) {
    const min = Number(this.data.minDailyTarget || 1);
    const max = Number(this.data.maxDailyTarget || 200);
    const parsed = Number(value);
    if (!Number.isFinite(parsed)) {
      return 20;
    }
    const normalized = Math.round(parsed);
    return Math.min(max, Math.max(min, normalized));
  },

  buildTargetValidation(value) {
    const raw = String(value || '').trim();
    const min = Number(this.data.minDailyTarget || 1);
    const max = Number(this.data.maxDailyTarget || 200);
    if (!raw) {
      return {
        valid: false,
        error: `请输入 ${min}-${max} 之间的整数`,
        normalized: null
      };
    }
    if (!/^\d+$/.test(raw)) {
      return {
        valid: false,
        error: '每日目标只能输入整数',
        normalized: null
      };
    }
    const normalized = Number(raw);
    if (normalized < min || normalized > max) {
      return {
        valid: false,
        error: `每日目标需在 ${min}-${max} 之间`,
        normalized
      };
    }
    return {
      valid: true,
      error: '',
      normalized
    };
  },

  buildReviewBatchValidation(value) {
    const raw = String(value || '').trim();
    if (!raw) {
      return {
        valid: false,
        error: `请输入 ${MIN_REVIEW_BATCH_SIZE}-${MAX_REVIEW_BATCH_SIZE} 之间的整数`,
        normalized: null
      };
    }
    if (!/^\d+$/.test(raw)) {
      return {
        valid: false,
        error: '复习题数只能输入整数',
        normalized: null
      };
    }
    const normalized = Number(raw);
    if (normalized < MIN_REVIEW_BATCH_SIZE || normalized > MAX_REVIEW_BATCH_SIZE) {
      return {
        valid: false,
        error: `复习题数需在 ${MIN_REVIEW_BATCH_SIZE}-${MAX_REVIEW_BATCH_SIZE} 之间`,
        normalized
      };
    }
    return {
      valid: true,
      error: '',
      normalized
    };
  },

  chooseTarget(event) {
    const value = Number(event.currentTarget.dataset.value);
    this.setData({
      selectedTarget: value,
      targetInputValue: String(value),
      targetInputError: ''
    });
    this.refreshTargets(value);
  },

  handleTargetInput(event) {
    const value = (event.detail.value || '').replace(/[^\d]/g, '');
    this.setData({
      targetInputValue: value,
      targetInputError: ''
    });
  },

  handleTargetBlur() {
    const validation = this.buildTargetValidation(this.data.targetInputValue);
    if (!validation.valid) {
      this.setData({
        targetInputError: validation.error
      });
      return;
    }
    this.setData({
      selectedTarget: validation.normalized,
      targetInputValue: String(validation.normalized),
      targetInputError: ''
    });
    this.refreshTargets(validation.normalized);
  },

  chooseReviewBatch(event) {
    const value = Number(event.currentTarget.dataset.value);
    this.setData({
      reviewBatchSize: value,
      reviewBatchInputValue: String(value),
      reviewBatchInputError: ''
    });
    this.refreshReviewBatchOptions(value);
  },

  handleReviewBatchInput(event) {
    const value = (event.detail.value || '').replace(/[^\d]/g, '');
    this.setData({
      reviewBatchInputValue: value,
      reviewBatchInputError: ''
    });
  },

  handleReviewBatchBlur() {
    const validation = this.buildReviewBatchValidation(this.data.reviewBatchInputValue);
    if (!validation.valid) {
      this.setData({
        reviewBatchInputError: validation.error
      });
      return;
    }
    this.setData({
      reviewBatchSize: validation.normalized,
      reviewBatchInputValue: String(validation.normalized),
      reviewBatchInputError: ''
    });
    this.refreshReviewBatchOptions(validation.normalized);
  },

  async runAiReplan() {
    if (this.data.aiPlanLoading || this.data.aiPlanRefreshing) {
      return;
    }
    this.clearAiPlanPolling();
    this.setData({
      aiPlanLoading: true,
      aiPlanRefreshing: true,
      aiPlanStatusText: 'AI 正在生成自适应计划...'
    });
    try {
      const run = await aiApi.replanStudyPlan({
        trend_days: 7,
        force_refresh: true,
        prefer_fast: false
      });
      const runId = run && run.run_id;
      if (!runId) {
        throw new Error('AI 任务启动失败');
      }
      this.setData({
        aiPlanRunId: runId,
        aiPlanStatusText: run.status_text || 'AI 正在生成自适应计划...',
        aiPlanResultHighlight: false
      });
      store.setAiPlanRun(buildAiPlanRunSnapshot(runId, 'plan'));
      await this.pollAiPlanRun(runId);
    } catch (error) {
      if (error && error.code === 'polling_cancelled') {
        return;
      }
      if (error && error.code === 'still_running') {
        this.setData({
          aiPlanLoading: false,
          aiPlanRefreshing: false,
          aiPlanStatusText: 'AI 仍在后台生成，稍后回到本页会自动继续'
        });
        wx.showToast({ title: 'AI 仍在后台生成', icon: 'none' });
        return;
      }
      this.setData({
        aiPlanStatusText: '',
        aiPlanRunId: '',
        aiPlanLoading: false,
        aiPlanRefreshing: false
      });
      store.setAiPlanRun(null);
      store.setAiPlanResult(null);
      wx.showToast({ title: (error.message || 'AI 计划生成失败').slice(0, 20), icon: 'none' });
    }
  },

  clearAiPlanPolling() {
    this.aiPlanPollingAborted = true;
    if (this.aiPlanPollTimer) {
      clearTimeout(this.aiPlanPollTimer);
      this.aiPlanPollTimer = null;
    }
    if (this.aiPlanPollResolver) {
      const resolve = this.aiPlanPollResolver;
      this.aiPlanPollResolver = null;
      resolve();
    }
  },

  async pollAiPlanRun(runId) {
    this.aiPlanPollingAborted = false;
    const maxAttempts = 240;
    for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
      if (this.aiPlanPollingAborted) {
        throw buildPollingControlError('polling_cancelled', '轮询已暂停');
      }
      const [run, stepsPayload, artifactsPayload] = await Promise.all([
        aiApi.getPlanReplanRun(runId),
        aiApi.getAiRunSteps(runId).catch(() => ({ steps: [] })),
        aiApi.getAiRunArtifacts(runId).catch(() => ({ artifacts: [] }))
      ]);
      const status = run && run.status;
      this.setData({
        aiPlanRunId: runId,
        aiPlanRunDetail: run || null,
        aiPlanRunSteps: (stepsPayload && stepsPayload.steps) || [],
        aiPlanRunArtifacts: (artifactsPayload && artifactsPayload.artifacts) || [],
        aiPlanStatusText: (run && run.status_text) || (status === 'succeeded' ? '已完成' : 'AI 正在生成自适应计划...')
      });
      if (status === 'succeeded' && run.result) {
        const result = run.result || null;
        store.setAiPlanRun(null);
        this.setData({
          aiPlanResult: result,
          aiPlanLoading: false,
          aiPlanRefreshing: false,
          aiPlanStatusText: (result.runtime_summary && result.runtime_summary.status_text) || '已完成',
          aiPlanRunId: '',
          aiPlanResultHighlight: true
        });
        store.setAiPlanResult(result);
        const degraded = !!(result && result.degraded_notice && result.degraded_notice.enabled);
        wx.showToast({
          title: degraded ? '已生成保底 AI 计划' : 'AI 计划已生成',
          icon: degraded ? 'none' : 'success'
        });
        this.scrollToAiPlanResult();
        return;
      }
      if (status === 'waiting_approval') {
        store.setAiPlanRun(buildAiPlanRunSnapshot(runId, 'plan'));
        this.setData({
          aiPlanLoading: false,
          aiPlanRefreshing: false,
          aiPlanStatusText: (run && run.status_text) || '等待审批',
          aiPlanRuntimeCollapsed: false
        });
        return;
      }
      if (status === 'failed') {
        store.setAiPlanRun(null);
        store.setAiPlanResult(null);
        throw new Error((run && run.error_message) || 'AI 计划生成失败');
      }
      await this.waitAiPlanPoll();
      if (this.aiPlanPollingAborted) {
        throw buildPollingControlError('polling_cancelled', '轮询已暂停');
      }
    }
    this.setData({
      aiPlanLoading: false,
      aiPlanRefreshing: false
    });
    throw buildPollingControlError('still_running', 'AI 计划仍在生成中，稍后回到本页会自动继续');
  },

  scrollToAiPlanResult() {
    if (this.aiPlanHighlightTimer) {
      clearTimeout(this.aiPlanHighlightTimer);
      this.aiPlanHighlightTimer = null;
    }
    this.setData({ aiPlanResultHighlight: true }, () => {
      if (this.data.scrollIntoViewTarget === 'plan-ai-result') {
        this.setData({ scrollIntoViewTarget: '' }, () => {
          this.setData({ scrollIntoViewTarget: 'plan-ai-result' });
        });
      } else {
        this.setData({ scrollIntoViewTarget: 'plan-ai-result' });
      }
      this.aiPlanHighlightTimer = setTimeout(() => {
        this.setData({
          aiPlanResultHighlight: false,
          scrollIntoViewTarget: ''
        });
        this.aiPlanHighlightTimer = null;
      }, 2500);
    });
  },

  waitAiPlanPoll(delayMs) {
    return new Promise((resolve) => {
      this.aiPlanPollResolver = resolve;
      this.aiPlanPollTimer = setTimeout(() => {
        this.aiPlanPollTimer = null;
        this.aiPlanPollResolver = null;
        resolve();
      }, delayMs || 1500);
    });
  },

  async resumeAiPlanRunIfNeeded() {
    const pendingRun = store.getAiPlanRun();
    if (!pendingRun || !pendingRun.run_id || this.aiPlanPollTimer) {
      return;
    }
    this.clearAiPlanPolling();
    this.setData({
      aiPlanLoading: true,
      aiPlanRefreshing: true,
      aiPlanRunId: pendingRun.run_id,
      aiPlanStatusText: '正在恢复上一次 AI 计划生成任务...'
    });
    try {
      await this.pollAiPlanRun(pendingRun.run_id);
    } catch (error) {
      if (error && error.code === 'polling_cancelled') {
        return;
      }
      if (error && error.code === 'still_running') {
        this.setData({
          aiPlanLoading: false,
          aiPlanRefreshing: false,
          aiPlanStatusText: 'AI 仍在后台生成，稍后回到本页会自动继续'
        });
        return;
      }
      store.setAiPlanRun(null);
      store.setAiPlanResult(null);
      this.setData({
        aiPlanLoading: false,
        aiPlanRefreshing: false,
        aiPlanStatusText: '',
        aiPlanRunId: ''
      });
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
      store.setAiPlanResult(null);
      this.syncSavedPlan(plan);
      await this.loadTodayTask();
      await this.loadPlanHistory();
      wx.showToast({ title: 'AI 调整已应用', icon: 'success' });
    } catch (error) {
      wx.showToast({ title: (error.message || '应用失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ aiPlanApplying: false });
    }
  },

  toggleAiPlanRuntime() {
    this.setData({
      aiPlanRuntimeCollapsed: !this.data.aiPlanRuntimeCollapsed
    });
  },

  async handleAiPlanRuntimeAction(event) {
    const action = event.currentTarget.dataset.action;
    const runId = this.data.aiPlanRunId || (this.data.aiPlanRunDetail && this.data.aiPlanRunDetail.run_id);
    if (!action || !runId || this.data.aiPlanRefreshing) {
      return;
    }
    this.setData({
      aiPlanRefreshing: true
    });
    try {
      if (action === 'retry') {
        await aiApi.retryAiRun(runId, {});
      } else if (action === 'resume') {
        await aiApi.resumeAiRun(runId, {});
      } else if (action === 'cancel') {
        await aiApi.cancelAiRun(runId, {});
      } else if (action === 'approve') {
        await aiApi.approveAiRun(runId, { approved: true, note: 'miniapp plan approve' });
      } else if (action === 'reject') {
        await aiApi.approveAiRun(runId, { approved: false, note: 'miniapp plan reject' });
      } else {
        return;
      }
      await this.pollAiPlanRun(runId);
    } catch (error) {
      wx.showToast({ title: (error.message || '运行态操作失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({
        aiPlanRefreshing: false
      });
    }
  },

  goAiCenterPlan() {
    if (this.data.aiPlanResult) {
      store.setAiPlanResult(this.data.aiPlanResult);
    }
    store.setAiCenterIntent({ tab: 'agent', view: 'analysis' });
    router.go('/pages/ai-center/index?tab=agent&view=analysis');
  },

  goBooks() {
    wx.switchTab({ url: '/pages/books/index' });
  },

  syncSavedPlan(plan) {
    store.setCurrentPlan(plan);
    if (plan && plan.daily_target) {
      store.setSettings({ daily_target: plan.daily_target });
    }
    const selectedTarget = this.normalizeTargetValue((plan && plan.daily_target) || this.data.selectedTarget);
    this.setData({
      currentPlan: plan || null,
      hasCurrentPlan: !!plan,
      selectedTarget,
      targetInputValue: String(selectedTarget),
      targetInputError: '',
      todayNewWordTarget: selectedTarget
    });
    this.refreshTargets(selectedTarget);
    this.initializeBook(plan);
  },

  async handleSavePlan() {
    if (!this.data.bookId) {
      wx.showToast({ title: '请先去词书页选择词书', icon: 'none' });
      return;
    }

    const validation = this.buildTargetValidation(this.data.targetInputValue);
    if (!validation.valid) {
      this.setData({ targetInputError: validation.error });
      wx.showToast({ title: validation.error.slice(0, 20), icon: 'none' });
      return;
    }
    const targetValue = validation.normalized;
    const reviewValidation = this.buildReviewBatchValidation(this.data.reviewBatchInputValue);
    if (!reviewValidation.valid) {
      this.setData({ reviewBatchInputError: reviewValidation.error });
      wx.showToast({ title: reviewValidation.error.slice(0, 20), icon: 'none' });
      return;
    }
    const reviewBatchSize = reviewValidation.normalized;
    this.setData({
      selectedTarget: targetValue,
      targetInputValue: String(targetValue),
      targetInputError: '',
      reviewBatchSize,
      reviewBatchInputValue: String(reviewBatchSize),
      reviewBatchInputError: ''
    });
    this.refreshTargets(targetValue);
    this.refreshReviewBatchOptions(reviewBatchSize);

    this.setData({ planActionLoading: true });
    try {
      const currentPlan = this.data.currentPlan;
      let plan;
      if (currentPlan && this.data.selectedBookIsCurrent) {
        plan = await plansApi.updateCurrentPlan({
          daily_target: targetValue
        });
        store.setSettings({ review_batch_size: reviewBatchSize });
        this.syncSavedPlan(plan);
        await this.loadTodayTask();
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
          daily_target: targetValue,
          keep_progress: keepProgress
        });
        store.setSettings({ review_batch_size: reviewBatchSize });
        this.syncSavedPlan(plan);
        await this.loadTodayTask();
        wx.showToast({ title: '词书已切换', icon: 'success' });
        router.relaunch('/pages/home/index');
        return;
      }

      plan = await plansApi.createPlan({
        book_id: this.data.bookId,
        daily_target: targetValue
      });
      store.setSettings({ review_batch_size: reviewBatchSize });
      this.syncSavedPlan(plan);
      await this.loadTodayTask();
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
      await this.loadTodayTask();
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
      await this.loadTodayTask();
      wx.showToast({ title: '计划已恢复', icon: 'success' });
    } catch (error) {
      wx.showToast({ title: (error.message || '恢复失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ planActionLoading: false });
    }
  },

  onHide() {
    this.clearAiPlanPolling();
    if (this.aiPlanHighlightTimer) {
      clearTimeout(this.aiPlanHighlightTimer);
      this.aiPlanHighlightTimer = null;
    }
    this.setData({
      aiPlanLoading: false,
      aiPlanRefreshing: false
    });
  },

  onUnload() {
    this.clearAiPlanPolling();
    if (this.aiPlanHighlightTimer) {
      clearTimeout(this.aiPlanHighlightTimer);
      this.aiPlanHighlightTimer = null;
    }
    this.setData({
      aiPlanLoading: false,
      aiPlanRefreshing: false
    });
  },

  onShow() {
    if (!this.data.pageLoading) {
      this.loadCurrentPlan();
      this.loadTodayTask();
    }
    this.resumeAiPlanRunIfNeeded();
  }
}));
