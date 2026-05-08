const aiApi = require('../../services/modules/ai');
const learnApi = require('../../services/modules/learn');
const router = require('../../utils/router');
const speech = require('../../utils/speech');
const store = require('../../store/app-store');
const { withThemePage } = require('../../utils/theme-manager');
const { buildLocalWordTutor } = require('../../utils/word-tutor');

Page(withThemePage({
  data: {
    words: [],
    currentIndex: 0,
    targetCount: 0,
    adaptive: null,
    loading: true,
    audioBusy: false,
    playbackReady: speech.isSpeechPlaybackReady(),
    aiTutorEnabled: false,
    localTutor: null,
    aiTutor: null,
    aiTutorEvidence: null,
    activeTutor: null,
    aiTutorLoading: false,
    aiTutorError: '',
    aiQuizAnswerVisible: false,
    meaningVisible: false,
    decisionStage: 'initial'
  },

  onLoad() {
    this.loadedOnce = false;
    this.aiTutorCache = {};
    this.aiTutorDisabledUntil = 0;
    this.aiTutorRequestToken = 0;
  },

  onShow() {
    if (this.loadedOnce && this.data.words.length) {
      return;
    }
    this.loadWords();
  },

  async loadWords() {
    this.setData({ loading: true });
    try {
      const data = await learnApi.getLearnWords();
      const words = data.list || [];
      this.loadedOnce = true;
      this.setData({
        words,
        currentIndex: 0,
        targetCount: Number(data.target_count || words.length || 0),
        adaptive: data.adaptive || null,
        loading: false,
      }, () => {
        this.applyAiTutorForCurrentWord(true);
        this.autoPlayCurrentWord();
      });
    } catch (error) {
      wx.showToast({ title: '加载失败', icon: 'none' });
      this.setData({ loading: false });
    }
  },

  getCurrentWord() {
    return this.data.words[this.data.currentIndex] || null;
  },

  getInitialDecisionState() {
    return {
      aiQuizAnswerVisible: false,
      meaningVisible: false,
      decisionStage: 'initial'
    };
  },

  enterReviewStage() {
    if (this.data.decisionStage === 'reviewing') {
      return;
    }
    this.setData({
      decisionStage: 'reviewing',
      meaningVisible: true
    });
  },

  applyAiTutorForCurrentWord(silent = true) {
    const currentWord = this.getCurrentWord();
    const localTutor = buildLocalWordTutor(currentWord, this.data.words, {
      whyRecommended: currentWord && currentWord.adaptive_reason
        ? currentWord.adaptive_reason
        : '这是你当前学习序列里的单词，趁现在把词义和例句一起记稳更划算。',
      confusingPoints: currentWord && currentWord.adaptive_tags ? currentWord.adaptive_tags : []
    });
    const cachedTutor = currentWord ? this.aiTutorCache[currentWord.id] : null;
    this.setData({
      localTutor,
      activeTutor: this.data.aiTutorEnabled ? cachedTutor : localTutor,
      aiTutor: this.data.aiTutorEnabled ? cachedTutor : null,
      aiTutorEvidence: null,
      aiTutorLoading: false,
      aiTutorError: '',
      ...this.getInitialDecisionState()
    });
    if (this.data.aiTutorEnabled) {
      this.loadRemoteAiTutor(silent);
    }
  },

  async loadRemoteAiTutor(silent = true, force = false) {
    const currentWord = this.getCurrentWord();
    if (!currentWord) {
      return;
    }

    if (!this.data.aiTutorEnabled && !force) {
      return;
    }

    if (!force && this.aiTutorCache[currentWord.id]) {
      this.setData({
        aiTutor: this.aiTutorCache[currentWord.id],
        activeTutor: this.aiTutorCache[currentWord.id],
        aiTutorEvidence: this.aiTutorCache[`${currentWord.id}_evidence`] || null,
        aiTutorLoading: false,
        aiTutorError: '',
        aiQuizAnswerVisible: false
      });
      return;
    }

    if (this.aiTutorDisabledUntil && Date.now() < this.aiTutorDisabledUntil) {
      this.setData({
        aiTutor: null,
        activeTutor: null,
        aiTutorEvidence: null,
        aiTutorLoading: false,
        aiTutorError: 'AI讲词暂时不可用，请稍后再试'
      });
      return;
    }

    const token = ++this.aiTutorRequestToken;
      this.setData({
        aiTutorLoading: true,
        aiTutorError: '',
        aiTutor: null,
        activeTutor: null,
        aiTutorEvidence: null,
        aiQuizAnswerVisible: false
      });
    try {
      const data = await aiApi.explainWord({ word_id: currentWord.id });
      if (token !== this.aiTutorRequestToken) {
        return;
      }
      if (!data || !data.ai_strategy || !data.ai_strategy.ai_enabled) {
        this.setData({
          aiTutor: null,
          activeTutor: null,
          aiTutorLoading: false,
          aiTutorError: '后端 AI 讲词尚未启用，请先配置 AI_API_KEY、AI_MODEL 和 AI_BASE_URL'
        });
        return;
      }
      const tutor = data.tutor;
      if (!tutor) {
        throw new Error('AI讲词没有返回有效内容，请稍后重试');
      }
      this.aiTutorCache[currentWord.id] = tutor;
      this.aiTutorCache[`${currentWord.id}_evidence`] = data.evidence || null;
      this.setData({
        aiTutor: tutor,
        activeTutor: tutor,
        aiTutorEvidence: data.evidence || null,
        aiTutorLoading: false,
        aiTutorError: '',
        aiQuizAnswerVisible: false
      });
    } catch (error) {
      if (token !== this.aiTutorRequestToken) {
        return;
      }
      const message = (error && error.message) || '';
      if (message.indexOf('最新 AI 接口') > -1) {
        this.aiTutorDisabledUntil = Date.now() + 3 * 60 * 1000;
      }
      this.setData({
        aiTutor: null,
        activeTutor: null,
        aiTutorEvidence: null,
        aiTutorLoading: false,
        aiTutorError: message || 'AI讲词失败，请稍后重试'
      });
      if (!silent && message.indexOf('最新 AI 接口') === -1) {
        wx.showToast({ title: 'AI讲词失败', icon: 'none' });
      }
    }
  },

  handleAiTutorSwitch(event) {
    const enabled = !!event.detail.value;
    const currentWord = this.getCurrentWord();
    const cachedTutor = currentWord ? this.aiTutorCache[currentWord.id] : null;
    this.setData({
      aiTutorEnabled: enabled,
      aiTutor: enabled ? (cachedTutor || null) : null,
      aiTutorEvidence: enabled ? (this.aiTutorCache[`${currentWord.id}_evidence`] || null) : null,
      activeTutor: enabled ? (cachedTutor || null) : this.data.localTutor,
      aiTutorLoading: false,
      aiTutorError: '',
      aiQuizAnswerVisible: false
    }, () => {
      if (enabled && currentWord && !cachedTutor) {
        this.loadRemoteAiTutor(true);
      }
    });
  },

  handleEnableAiTutor() {
    if (this.data.aiTutorEnabled) {
      return;
    }
    this.handleAiTutorSwitch({ detail: { value: true } });
  },

  handleDisableAiTutor() {
    if (!this.data.aiTutorEnabled) {
      return;
    }
    this.handleAiTutorSwitch({ detail: { value: false } });
  },

  handleReloadAiTutor() {
    const currentWord = this.getCurrentWord();
    if (!currentWord) {
      return;
    }
    if (!this.data.aiTutorEnabled) {
      this.setData({ aiTutorEnabled: true, aiTutor: null, aiTutorEvidence: null, activeTutor: null, aiTutorError: '' }, () => {
        this.loadRemoteAiTutor(false, true);
      });
      return;
    }
    delete this.aiTutorCache[currentWord.id];
    this.aiTutorDisabledUntil = 0;
    this.loadRemoteAiTutor(false, true);
  },

  handleToggleAiQuizAnswer() {
    this.setData({
      aiQuizAnswerVisible: !this.data.aiQuizAnswerVisible
    });
  },

  handleToggleMeaning() {
    this.setData({
      meaningVisible: !this.data.meaningVisible
    });
  },

  handleBackToDecision() {
    this.setData({
      decisionStage: 'initial'
    });
  },

  autoPlayCurrentWord() {
    const settings = store.getState().settings || {};
    if (!settings.auto_play_audio) {
      return;
    }
    const currentWord = this.getCurrentWord();
    if (!currentWord) {
      return;
    }
    this.handlePlayWord();
  },

  async playText(text, audioUrl = '') {
    this.setData({ audioBusy: true });
    try {
      if (audioUrl) {
        await speech.playAudioUrl(audioUrl);
      } else {
        await speech.speakText(text, { lang: 'en-US' });
      }
    } catch (error) {
      wx.showToast({ title: (error.message || '播放失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ audioBusy: false });
    }
  },

  handlePlayWord() {
    const currentWord = this.getCurrentWord();
    if (!currentWord) {
      return;
    }
    const pronunciation = currentWord.pronunciation || {};
    this.playText(pronunciation.tts_text || currentWord.word, pronunciation.audio_url || '');
  },

  handlePlayExample() {
    const currentWord = this.getCurrentWord();
    if (!currentWord) {
      return;
    }
    const pronunciation = currentWord.pronunciation || {};
    this.playText(pronunciation.example_tts_text || currentWord.example_sentence || currentWord.word, '');
  },

  async record(actionType, result) {
    const currentWord = this.getCurrentWord();
    if (!currentWord) {
      return;
    }
    try {
      await learnApi.createLearningRecord({
        word_id: currentWord.id,
        source: 'learn',
        action_type: actionType,
        result,
        duration: 8
      });
      const nextIndex = this.data.currentIndex + 1;
      if (nextIndex >= this.data.words.length) {
        wx.showToast({ title: '今日学习完成', icon: 'success' });
        router.back();
        return;
      }
      this.setData({
        currentIndex: nextIndex,
        localTutor: null,
        aiTutor: this.data.aiTutorEnabled ? null : this.data.aiTutor,
        aiTutorEvidence: null,
        activeTutor: null,
        aiTutorError: '',
        aiQuizAnswerVisible: false,
        meaningVisible: false,
        decisionStage: 'initial'
      }, () => {
        this.applyAiTutorForCurrentWord(true);
        this.autoPlayCurrentWord();
      });
    } catch (error) {
      wx.showToast({ title: '提交失败', icon: 'none' });
    }
  },

  handleKnown() {
    this.record('known', 'correct');
  },

  handleUnknown() {
    if (this.data.decisionStage === 'initial') {
      this.enterReviewStage();
      return;
    }
    this.record('unknown', 'wrong');
  },

  async handleFavorite() {
    const currentWord = this.getCurrentWord();
    if (!currentWord) {
      return;
    }
    await learnApi.addFavorite({ word_id: currentWord.id, note: '学习页收藏' });
    wx.showToast({ title: '已收藏', icon: 'success' });
  },

  goDetail() {
    const currentWord = this.getCurrentWord();
    if (currentWord) {
      router.go(`/pages/word-detail/index?id=${currentWord.id}`);
    }
  }
}));
