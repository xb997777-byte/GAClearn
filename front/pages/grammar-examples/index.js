const grammarApi = require('../../services/modules/grammar');
const router = require('../../utils/router');
const {
  DEFAULT_DIFFICULTIES,
  VIEW_MODE_META,
  buildLegendMap,
  buildGuideCards,
  buildVisualState
} = require('../../utils/grammar-visual');
const { withThemePage } = require('../../utils/theme-manager');

Page(withThemePage({
  data: {
    topics: [],
    sentences: [],
    recommendations: [],
    progress: null,
    currentSentence: null,
    currentSentenceId: null,
    legend: [],
    legendMap: {},
    keyword: '',
    selectedTopicId: 0,
    selectedDifficulty: 0,
    difficulties: DEFAULT_DIFFICULTIES,
    sentenceTotal: 0,
    viewMode: 'complete',
    viewModeTitle: VIEW_MODE_META.complete.title,
    viewModeDescription: VIEW_MODE_META.complete.description,
    sentenceTokens: [],
    guideCards: [],
    coreGuideCards: [],
    supportGuideCards: [],
    selectedAnnotation: null,
    selectedGuideCard: null,
    practiceSelection: '',
    practiceResult: null,
    initialized: false,
    loadingList: false,
    loadingDetail: false
  },

  onLoad(options) {
    this.pendingSentenceId = Number((options && (options.sentenceId || options.id)) || 0) || 0;
    this.currentDetail = null;
    this.baseGuideCards = [];
    this.viewedSentenceMap = {};
  },

  onShow() {
    if (!this.data.initialized) {
      this.loadInitialData();
      return;
    }
    this.loadProgressSilent();
  },

  async loadInitialData() {
    this.setData({ loadingList: true });
    try {
      const [topicsData, sentenceData, progressData] = await Promise.all([
        grammarApi.listTopics(),
        grammarApi.listSentences(this.buildSentenceQuery()),
        grammarApi.getProgress()
      ]);

      const sentences = sentenceData && sentenceData.list ? sentenceData.list : [];
      const targetSentenceId = this.resolveSentenceId(sentences, this.pendingSentenceId);

      this.setData({
        topics: topicsData && topicsData.list ? topicsData.list : [],
        sentences,
        sentenceTotal: sentenceData && sentenceData.pagination ? sentenceData.pagination.total : sentences.length,
        progress: progressData || null,
        initialized: true
      });

      if (targetSentenceId) {
        await this.loadSentenceDetail(targetSentenceId, { recordView: true });
      } else {
        this.resetDetailState();
        await this.refreshRecommendations();
      }
    } catch (error) {
      wx.showToast({ title: error.message || '语法句库加载失败', icon: 'none' });
    } finally {
      this.setData({ loadingList: false });
    }
  },

  buildSentenceQuery() {
    const params = {
      page: 1,
      page_size: 60
    };

    if (this.data.selectedTopicId) {
      params.point_id = this.data.selectedTopicId;
    }
    if (this.data.selectedDifficulty) {
      params.difficulty = this.data.selectedDifficulty;
    }
    if ((this.data.keyword || '').trim()) {
      params.keyword = this.data.keyword.trim();
    }

    return params;
  },

  resolveSentenceId(list, preferredId) {
    if (preferredId && (list || []).some((item) => item.id === preferredId)) {
      return preferredId;
    }
    if (this.data.currentSentenceId && (list || []).some((item) => item.id === this.data.currentSentenceId)) {
      return this.data.currentSentenceId;
    }
    return list && list.length ? list[0].id : null;
  },

  async refreshSentenceList(preferredSentenceId) {
    this.setData({ loadingList: true });
    try {
      const sentenceData = await grammarApi.listSentences(this.buildSentenceQuery());
      const sentences = sentenceData && sentenceData.list ? sentenceData.list : [];
      const targetSentenceId = this.resolveSentenceId(sentences, preferredSentenceId);

      this.setData({
        sentences,
        sentenceTotal: sentenceData && sentenceData.pagination ? sentenceData.pagination.total : sentences.length
      });

      if (targetSentenceId) {
        await this.loadSentenceDetail(targetSentenceId, {
          recordView: !this.viewedSentenceMap[targetSentenceId]
        });
      } else {
        this.resetDetailState();
        await this.refreshRecommendations();
      }
    } catch (error) {
      wx.showToast({ title: error.message || '句库筛选失败', icon: 'none' });
    } finally {
      this.setData({ loadingList: false });
    }
  },

  async loadSentenceDetail(sentenceId, options) {
    if (!sentenceId) {
      return;
    }

    const detailOptions = Object.assign({ recordView: true }, options || {});
    this.setData({ loadingDetail: true });

    try {
      const detail = await grammarApi.getSentenceDetail(sentenceId);
      this.currentDetail = detail;
      this.baseGuideCards = buildGuideCards(detail);
      this.applySentenceDetail(detail);
      await this.refreshRecommendations(sentenceId, detail.point ? detail.point.id : null);

      if (detailOptions.recordView) {
        this.recordView(sentenceId);
      }
    } catch (error) {
      wx.showToast({ title: error.message || '句子详情加载失败', icon: 'none' });
    } finally {
      this.setData({ loadingDetail: false });
    }
  },

  applySentenceDetail(detail) {
    const preservedId = this.data.selectedAnnotation ? this.data.selectedAnnotation.id : 0;
    const visualState = buildVisualState(detail, this.data.viewMode, preservedId, this.baseGuideCards);

    this.setData({
      currentSentence: detail,
      currentSentenceId: detail.id,
      legend: detail.legend || [],
      legendMap: buildLegendMap(detail.legend || []),
      practiceSelection: '',
      practiceResult: null,
      ...visualState
    });
  },

  syncVisualState(annotationId) {
    if (!this.currentDetail) {
      return;
    }

    const visualState = buildVisualState(
      this.currentDetail,
      this.data.viewMode,
      annotationId,
      this.baseGuideCards
    );
    this.setData(visualState);
  },

  resetDetailState() {
    this.currentDetail = null;
    this.baseGuideCards = [];
    this.setData({
      currentSentence: null,
      currentSentenceId: null,
      legend: [],
      legendMap: {},
      sentenceTokens: [],
      guideCards: [],
      coreGuideCards: [],
      supportGuideCards: [],
      selectedAnnotation: null,
      selectedGuideCard: null,
      practiceSelection: '',
      practiceResult: null,
      viewModeTitle: VIEW_MODE_META[this.data.viewMode].title,
      viewModeDescription: VIEW_MODE_META[this.data.viewMode].description
    });
  },

  async refreshRecommendations(currentSentenceId, pointId) {
    try {
      const sentence = this.currentDetail || this.data.currentSentence;
      const params = { limit: 6 };
      const resolvedSentenceId = currentSentenceId || (sentence ? sentence.id : 0);
      const resolvedPointId = pointId || (sentence && sentence.point ? sentence.point.id : this.data.selectedTopicId || 0);

      if (resolvedSentenceId) {
        params.current_sentence_id = resolvedSentenceId;
      }
      if (resolvedPointId) {
        params.point_id = resolvedPointId;
      }

      const data = await grammarApi.getRecommendations(params);
      this.setData({ recommendations: data && data.list ? data.list : [] });
    } catch (error) {
      this.setData({ recommendations: [] });
    }
  },

  async loadProgressSilent() {
    try {
      const progress = await grammarApi.getProgress();
      this.setData({ progress: progress || null });
    } catch (error) {}
  },

  async recordView(sentenceId) {
    if (!sentenceId || this.viewedSentenceMap[sentenceId]) {
      return;
    }

    this.viewedSentenceMap[sentenceId] = true;
    try {
      await grammarApi.createRecord({
        sentence_id: sentenceId,
        action_type: 'view',
        duration: 5
      });
      this.loadProgressSilent();
    } catch (error) {}
  },

  handleKeywordInput(event) {
    this.setData({ keyword: event.detail.value || '' });
  },

  handleSearchSubmit() {
    this.refreshSentenceList();
  },

  handleTopicTap(event) {
    const topicId = Number(event.currentTarget.dataset.topicId || 0);
    if (topicId === this.data.selectedTopicId) {
      return;
    }
    this.setData({ selectedTopicId: topicId }, () => {
      this.refreshSentenceList();
    });
  },

  handleDifficultyTap(event) {
    const difficulty = Number(event.currentTarget.dataset.difficulty || 0);
    if (difficulty === this.data.selectedDifficulty) {
      return;
    }
    this.setData({ selectedDifficulty: difficulty }, () => {
      this.refreshSentenceList();
    });
  },

  handleViewModeChange(event) {
    const mode = event.currentTarget.dataset.mode;
    if (!mode || mode === this.data.viewMode || !this.currentDetail) {
      return;
    }
    this.setData({ viewMode: mode }, () => {
      const selectedId = this.data.selectedAnnotation ? this.data.selectedAnnotation.id : 0;
      this.syncVisualState(selectedId);
    });
  },

  handleSegmentTap(event) {
    const annotationId = Number(event.currentTarget.dataset.annotationId || 0);
    if (!annotationId) {
      return;
    }
    this.syncVisualState(annotationId);
  },

  handleGuideCardTap(event) {
    const annotationId = Number(event.currentTarget.dataset.annotationId || 0);
    if (!annotationId) {
      return;
    }
    this.syncVisualState(annotationId);
  },

  async handlePickSentence(event) {
    const sentenceId = Number(event.currentTarget.dataset.sentenceId || 0);
    if (!sentenceId) {
      return;
    }
    await this.loadSentenceDetail(sentenceId, { recordView: true });
  },

  async handleJumpNeighbor(event) {
    const direction = event.currentTarget.dataset.direction;
    const navigation = this.data.currentSentence && this.data.currentSentence.navigation
      ? this.data.currentSentence.navigation
      : null;
    const targetId = direction === 'prev'
      ? navigation && navigation.previous_sentence_id
      : navigation && navigation.next_sentence_id;

    if (!targetId) {
      wx.showToast({
        title: direction === 'prev' ? '已经是本专题第一句了' : '已经是本专题最后一句了',
        icon: 'none'
      });
      return;
    }

    await this.loadSentenceDetail(targetId, { recordView: true });
  },

  async handleFeedback(event) {
    const action = event.currentTarget.dataset.action;
    const sentenceId = this.data.currentSentenceId;
    if (!action || !sentenceId) {
      return;
    }

    try {
      await grammarApi.createRecord({
        sentence_id: sentenceId,
        action_type: action,
        duration: 8
      });
      wx.showToast({
        title: action === 'understood' ? '已标记为理解' : '已记录为待加强',
        icon: 'success'
      });
      this.loadProgressSilent();
    } catch (error) {
      wx.showToast({ title: error.message || '提交失败', icon: 'none' });
    }
  },

  async handlePracticeSelect(event) {
    const option = event.currentTarget.dataset.option;
    const currentSentence = this.data.currentSentence;
    const practice = currentSentence && currentSentence.practice ? currentSentence.practice : null;
    if (!practice || this.data.practiceResult) {
      return;
    }

    const isCorrect = option === practice.answer;
    const practiceResult = {
      isCorrect,
      answer: practice.answer,
      explanation: practice.explanation || ''
    };

    this.setData({
      practiceSelection: option,
      practiceResult
    });

    try {
      await grammarApi.createRecord({
        sentence_id: currentSentence.id,
        action_type: 'practice',
        practice_type: practice.type || 'choice',
        result: isCorrect ? 'correct' : 'wrong',
        duration: 12,
        extra_payload: {
          selected_option: option
        }
      });
      this.loadProgressSilent();
    } catch (error) {}
  },

  handleRefreshRecommend() {
    this.refreshRecommendations();
  },

  handleGoAnalyze() {
    router.go('/pages/grammar-analyze/index');
  },

  handleGoGuide() {
    router.go('/pages/grammar-guide/index');
  }
}));
