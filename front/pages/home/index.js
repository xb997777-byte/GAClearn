const aiApi = require('../../services/modules/ai');
const authApi = require('../../services/modules/auth');
const plansApi = require('../../services/modules/plans');
const statsApi = require('../../services/modules/stats');
const router = require('../../utils/router');
const { withThemePage } = require('../../utils/theme-manager');

Page(withThemePage({
  data: {
    user: null,
    plan: null,
    task: null,
    summary: null,
    adaptive: null,
    overview: null,
    userName: '学习者',
    taskProgressText: '0/0',
    reviewRemainingText: '0',
    hasPlan: false,
    cefrLevel: '',
    planProgressPercent: 0,
    planProgressWidth: 'width:0%;',
    planProgressText: '0 / 0',
    planRemainingCountText: '0',
    studyCoachEnabled: false,
    studyCoach: null,
    studyCoachEvidence: null,
    studyCoachLoading: false,
    studyCoachError: '',
    studyCoachContextSources: []
  },

  onLoad() {
    this.studyCoachDisabledUntil = 0;
  },

  onShow() {
    getApp().setTabBarSelected(0);
    this.loadPage();
  },

  async loadPage(options = {}) {
    try {
      const [user, todayTask, overview] = await Promise.all([
        authApi.getMe(),
        plansApi.getTodayTask(),
        statsApi.getOverview()
      ]);
      const plan = todayTask.plan || null;
      const totalWordCount = Number((plan && plan.book && plan.book.word_count) || 0);
      const finishedWordCount = Number((plan && plan.finished_word_count) || 0);
      const remainingWordCount = Math.max(totalWordCount - finishedWordCount, 0);
      const planProgressPercent = totalWordCount
        ? Math.max(0, Math.min(100, Math.round((finishedWordCount / totalWordCount) * 100)))
        : 0;
      const shouldReloadCoach = this.data.studyCoachEnabled;
      this.setData({
        user,
        plan,
        task: todayTask.task,
        summary: todayTask.summary,
        adaptive: todayTask.adaptive || null,
        overview,
        userName: (user && user.nickname) || '学习者',
        taskProgressText: todayTask.task ? `${todayTask.task.learned_count}/${todayTask.task.new_word_target}` : '0/0',
        reviewRemainingText: `${todayTask.summary ? todayTask.summary.review_words_remaining : 0}`,
        hasPlan: !!plan,
        cefrLevel: (user && user.settings && user.settings.cefr_level) || '',
        planProgressPercent,
        planProgressWidth: `width:${planProgressPercent}%;`,
        planProgressText: totalWordCount ? `${finishedWordCount} / ${totalWordCount}` : `${finishedWordCount} / --`,
        planRemainingCountText: totalWordCount ? `${remainingWordCount}` : '--'
      });
      if (shouldReloadCoach) {
        this.loadStudyCoach(true, !!options.forceCoachRefresh);
      } else {
        this.setData({
          studyCoach: null,
          studyCoachEvidence: null,
          studyCoachLoading: false,
          studyCoachError: '',
          studyCoachContextSources: []
        });
      }
    } catch (error) {
      wx.showToast({ title: '加载失败，请重新登录', icon: 'none' });
    }
  },

  async loadStudyCoach(silent = false, forceRefresh = false) {
    if (this.studyCoachDisabledUntil && Date.now() < this.studyCoachDisabledUntil) {
      this.setData({
        studyCoach: null,
        studyCoachEvidence: null,
        studyCoachLoading: false,
        studyCoachError: 'AI学习教练暂时不可用，请稍后再试'
      });
      return;
    }

    this.setData({
      studyCoach: null,
      studyCoachEvidence: null,
      studyCoachLoading: true,
      studyCoachError: ''
    });

    try {
      const data = await aiApi.getStudyCoach({
        trend_days: 7,
        force_refresh: !!forceRefresh
      });
      if (!data || !data.ai_strategy || !data.ai_strategy.ai_enabled) {
        this.setData({
          studyCoach: null,
          studyCoachEvidence: null,
          studyCoachLoading: false,
          studyCoachError: '后端 AI 学习教练尚未启用，请先配置 AI_API_KEY、AI_MODEL 和 AI_BASE_URL'
        });
        return;
      }
      this.setData({
        studyCoach: data.coach || null,
        studyCoachEvidence: data.evidence || null,
        studyCoachLoading: false,
        studyCoachError: '',
        studyCoachContextSources: Array.isArray(data.context_sources) ? data.context_sources : []
      });
    } catch (error) {
      const message = (error && error.message) || 'AI教练加载失败';
      if (message.indexOf('最新 AI 接口') > -1) {
        this.studyCoachDisabledUntil = Date.now() + 3 * 60 * 1000;
      }
      this.setData({
        studyCoach: null,
        studyCoachLoading: false,
        studyCoachError: message || 'AI学习教练加载失败，请稍后重试'
      });
      if (!silent && message.indexOf('最新 AI 接口') === -1) {
        wx.showToast({ title: 'AI教练加载失败', icon: 'none' });
      }
    }
  },

  handleEnableStudyCoach() {
    this.setData({
      studyCoachEnabled: true,
      studyCoach: null,
      studyCoachEvidence: null,
      studyCoachError: ''
    }, () => {
      this.studyCoachDisabledUntil = 0;
      this.loadStudyCoach(false);
    });
  },

  handleDisableStudyCoach() {
    this.setData({
      studyCoachEnabled: false,
      studyCoach: null,
      studyCoachEvidence: null,
      studyCoachLoading: false,
      studyCoachError: '',
      studyCoachContextSources: []
    });
  },

  handleReloadStudyCoach() {
    if (!this.data.studyCoachEnabled) {
      this.handleEnableStudyCoach();
      return;
    }
    this.studyCoachDisabledUntil = 0;
    this.loadPage({ forceCoachRefresh: true });
  },

  async handleStartTask() {
    try {
      await plansApi.startTodayTask();
      router.go('/pages/learn/index');
    } catch (error) {
      wx.showToast({ title: '启动任务失败', icon: 'none' });
    }
  },

  goBooks() {
    wx.switchTab({ url: '/pages/books/index' });
  },

  goPlan() {
    router.go('/pages/plan/index');
  },

  goGrammar() {
    wx.switchTab({ url: '/pages/grammar/index' });
  },

  goReview() {
    router.go('/pages/review/index');
  },

  goExam() {
    router.go('/pages/exam/index?mode=practice');
  },

  goPlacement() {
    router.go('/pages/exam/index?mode=placement');
  },

  goSettings() {
    router.go('/pages/settings/index');
  },

  goStats() {
    router.go('/pages/stats/index');
  },

  goAiCenter() {
    router.go('/pages/ai-center/index?tab=apps&workspace=conversation');
  },

  goWrongWords() {
    router.go('/pages/wrong-words/index');
  },

  goFavorites() {
    router.go('/pages/favorites/index');
  }
}));
