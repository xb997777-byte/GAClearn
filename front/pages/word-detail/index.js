const aiApi = require('../../services/modules/ai');
const learnApi = require('../../services/modules/learn');
const speech = require('../../utils/speech');
const { withThemePage } = require('../../utils/theme-manager');
const { buildLocalWordTutor } = require('../../utils/word-tutor');

Page(withThemePage({
  data: {
    word: null,
    favoriteText: '未收藏',
    playbackReady: speech.isSpeechPlaybackReady(),
    aiTutorEnabled: false,
    localTutor: null,
    aiTutor: null,
    aiTutorEvidence: null,
    activeTutor: null,
    aiTutorLoading: false,
    aiTutorError: '',
    aiQuizAnswerVisible: false
  },

  async onLoad(options) {
    this.aiTutorRequestToken = 0;
    if (!options.id) {
      return;
    }
    await this.loadWordDetail(Number(options.id));
  },

  async loadWordDetail(wordId) {
    try {
      const word = await learnApi.getLearnWordDetail(wordId);
      const localTutor = buildLocalWordTutor(word, [], {
        whyRecommended: '这是你当前查看的词条，先把核心词义和例句理解透会更高效。'
      });
      this.setData({
        word,
        favoriteText: word.progress && word.progress.is_favorite ? '已收藏' : '未收藏',
        localTutor,
        activeTutor: localTutor
      });
    } catch (error) {
      wx.showToast({ title: '单词加载失败', icon: 'none' });
    }
  },

  async loadAiTutor(wordId, silent = false) {
    if (!this.data.aiTutorEnabled) {
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
      const data = await aiApi.explainWord({ word_id: wordId });
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
      if (!data.tutor) {
        throw new Error('AI讲词没有返回有效内容，请稍后重试');
      }
      this.setData({
        aiTutor: data.tutor,
        activeTutor: data.tutor,
        aiTutorEvidence: data.evidence || null,
        aiTutorLoading: false,
        aiTutorError: ''
      });
    } catch (error) {
      if (token !== this.aiTutorRequestToken) {
        return;
      }
      this.setData({
        aiTutor: null,
        activeTutor: null,
        aiTutorEvidence: null,
        aiTutorLoading: false,
        aiTutorError: error.message || 'AI讲词失败，请稍后重试'
      });
      if (!silent) {
        wx.showToast({ title: 'AI讲词失败', icon: 'none' });
      }
    }
  },

  handleAiTutorSwitch(event) {
    const enabled = !!event.detail.value;
    const nextData = {
      aiTutorEnabled: enabled,
      aiQuizAnswerVisible: false,
      aiTutorError: '',
      aiTutorLoading: false,
      aiTutorEvidence: enabled ? (this.data.aiTutorEvidence || null) : null,
      activeTutor: enabled ? (this.data.aiTutor || null) : this.data.localTutor
    };

    this.setData(nextData, () => {
      if (enabled && !this.data.aiTutor && this.data.word) {
        this.loadAiTutor(this.data.word.id);
      }
    });
  },

  handleReloadAiTutor() {
    if (!this.data.word) {
      return;
    }
    if (!this.data.aiTutorEnabled) {
      this.setData({ aiTutorEnabled: true, aiTutor: null, aiTutorEvidence: null, activeTutor: null, aiTutorError: '' }, () => {
        this.loadAiTutor(this.data.word.id);
      });
      return;
    }
    this.loadAiTutor(this.data.word.id);
  },

  handleToggleAiQuizAnswer() {
    this.setData({
      aiQuizAnswerVisible: !this.data.aiQuizAnswerVisible
    });
  },

  async handlePlayWord() {
    if (!this.data.word) {
      return;
    }
    const pronunciation = this.data.word.pronunciation || {};
    try {
      if (pronunciation.audio_url) {
        await speech.playAudioUrl(pronunciation.audio_url);
      } else {
        await speech.speakText(pronunciation.tts_text || this.data.word.word, {
          lang: 'en-US'
        });
      }
    } catch (error) {
      wx.showToast({ title: (error.message || '播放失败').slice(0, 20), icon: 'none' });
    }
  },

  async handlePlayExample() {
    if (!this.data.word) {
      return;
    }
    try {
      await speech.speakText(
        (this.data.word.pronunciation && this.data.word.pronunciation.example_tts_text) ||
        this.data.word.example_sentence ||
        this.data.word.word,
        { lang: 'en-US' }
      );
    } catch (error) {
      wx.showToast({ title: (error.message || '播放失败').slice(0, 20), icon: 'none' });
    }
  }
}));
