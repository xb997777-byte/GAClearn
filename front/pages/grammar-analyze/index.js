const {
  VIEW_MODE_META,
  buildLegendMap,
  buildGuideCards,
  buildVisualState
} = require('../../utils/grammar-visual');
const grammarApi = require('../../services/modules/grammar');
const router = require('../../utils/router');
const speech = require('../../utils/speech');
const { withThemePage } = require('../../utils/theme-manager');

const SAMPLE_SENTENCES = [
  'The teacher who checks our essays every week offers clear advice before class.',
  'If you review the notes carefully, the whole paragraph becomes much easier to understand.',
  'To improve her speaking, she records a short summary after every lesson.'
];

Page(withThemePage({
  data: {
    customSentenceInput: '',
    exampleSentences: SAMPLE_SENTENCES,
    aiTeacherPreviewItems: [
      '拆句后自动讲主干、从句和时态重点',
      '结合当前句子推荐相关语法点和相似例句',
      '自动生成一题微练习，学完马上巩固'
    ],
    analyzingCustom: false,
    currentSentence: null,
    legend: [],
    legendMap: {},
    viewMode: 'complete',
    viewModeTitle: VIEW_MODE_META.complete.title,
    viewModeDescription: VIEW_MODE_META.complete.description,
    sentenceTokens: [],
    guideCards: [],
    coreGuideCards: [],
    supportGuideCards: [],
    selectedAnnotation: null,
    selectedGuideCard: null,
    questionInput: '',
    questionAnswer: '',
    questionReferences: [],
    questionFollowups: [],
    askingQuestion: false,
    miniQuizSelection: '',
    miniQuizResult: null,
    sentenceAudioBusy: false,
    playbackReady: speech.isSpeechPlaybackReady()
  },

  onLoad() {
    this.currentDetail = null;
    this.baseGuideCards = [];
  },

  handleCustomSentenceInput(event) {
    this.setData({
      customSentenceInput: event.detail.value || ''
    });
  },

  handleQuestionInput(event) {
    this.setData({
      questionInput: event.detail.value || ''
    });
  },

  async handleCustomAnalyze() {
    const sentence = (this.data.customSentenceInput || '').trim();
    if (!sentence) {
      wx.showToast({ title: '请输入要拆解的英文句子', icon: 'none' });
      return;
    }

    this.setData({ analyzingCustom: true });
    try {
      const detail = await grammarApi.analyzeSentence(sentence);
      this.currentDetail = detail;
      this.baseGuideCards = buildGuideCards(detail);
      this.applySentenceDetail(detail);
      wx.pageScrollTo({
        selector: '#ai-teacher-section',
        duration: 280
      });
    } catch (error) {
      wx.showToast({ title: (error.message || '自动拆句失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ analyzingCustom: false });
    }
  },

  applySentenceDetail(detail) {
    const preservedId = this.data.selectedAnnotation ? this.data.selectedAnnotation.id : 0;
    const visualState = buildVisualState(detail, this.data.viewMode, preservedId, this.baseGuideCards);

    this.setData({
      currentSentence: detail,
      legend: detail.legend || [],
      legendMap: buildLegendMap(detail.legend || []),
      questionAnswer: '',
      questionReferences: [],
      questionFollowups: [],
      miniQuizSelection: '',
      miniQuizResult: null,
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

  handleSampleTap(event) {
    const sentence = event.currentTarget.dataset.sentence || '';
    if (!sentence) {
      return;
    }
    this.setData({ customSentenceInput: sentence }, () => {
      this.handleCustomAnalyze();
    });
  },

  async handlePlaySentence() {
    const sentence = (this.data.currentSentence && this.data.currentSentence.sentence) || (this.data.customSentenceInput || '').trim();
    if (!sentence) {
      wx.showToast({ title: '请先输入句子', icon: 'none' });
      return;
    }
    this.setData({ sentenceAudioBusy: true });
    try {
      await speech.speakText(sentence, { lang: 'en-US' });
    } catch (error) {
      wx.showToast({ title: (error.message || '朗读失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ sentenceAudioBusy: false });
    }
  },

  async handleAskQuestion() {
    const question = (this.data.questionInput || '').trim();
    const sentence = (this.data.currentSentence && this.data.currentSentence.sentence) || (this.data.customSentenceInput || '').trim();
    if (!question) {
      wx.showToast({ title: '请输入你想追问的问题', icon: 'none' });
      return;
    }
    this.setData({ askingQuestion: true });
    try {
      const data = await grammarApi.askQuestion({
        sentence,
        question
      });
      this.setData({
        questionAnswer: (data && data.answer) || '暂无回答',
        questionReferences: (data && data.references) || [],
        questionFollowups: (data && data.followup_questions) || []
      });
    } catch (error) {
      wx.showToast({ title: (error.message || '语法问答失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ askingQuestion: false });
    }
  },

  handleSuggestedQuestionTap(event) {
    const question = event.currentTarget.dataset.question || '';
    if (!question) {
      return;
    }
    this.setData({ questionInput: question }, () => {
      this.handleAskQuestion();
    });
  },

  handleRelatedSentenceTap(event) {
    const sentenceId = Number(event.currentTarget.dataset.sentenceId || 0);
    if (!sentenceId) {
      return;
    }
    router.go(`/pages/grammar-examples/index?sentenceId=${sentenceId}`);
  },

  handleMiniQuizOption(event) {
    const option = event.currentTarget.dataset.option || '';
    const quiz = this.data.currentSentence && this.data.currentSentence.tutor
      ? this.data.currentSentence.tutor.mini_quiz
      : null;
    if (!quiz || !option || this.data.miniQuizResult) {
      return;
    }

    const isCorrect = option === quiz.answer;
    this.setData({
      miniQuizSelection: option,
      miniQuizResult: {
        isCorrect,
        answer: quiz.answer || '',
        explanation: quiz.explanation || ''
      }
    });
  },

  handleResetInput() {
    this.currentDetail = null;
    this.baseGuideCards = [];
    this.setData({
      customSentenceInput: '',
      currentSentence: null,
      legend: [],
      legendMap: {},
      sentenceTokens: [],
      guideCards: [],
      coreGuideCards: [],
      supportGuideCards: [],
      selectedAnnotation: null,
      selectedGuideCard: null,
      viewMode: 'complete',
      viewModeTitle: VIEW_MODE_META.complete.title,
      viewModeDescription: VIEW_MODE_META.complete.description,
      questionInput: '',
      questionAnswer: '',
      questionReferences: [],
      questionFollowups: [],
      miniQuizSelection: '',
      miniQuizResult: null
    });
  }
}));
