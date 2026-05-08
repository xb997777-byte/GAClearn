const aiApi = require('../../services/modules/ai');
const reviewApi = require('../../services/modules/review');
const router = require('../../utils/router');
const speech = require('../../utils/speech');
const { withThemePage } = require('../../utils/theme-manager');

function decoratePlayableQuestion(question) {
  if (!question) {
    return null;
  }
  const nextQuestion = Object.assign({}, question);
  if (!nextQuestion.speech_text && nextQuestion.question_type === 'word_to_meaning' && nextQuestion.stem) {
    nextQuestion.speech_text = nextQuestion.stem;
    nextQuestion.speech_lang = 'en-US';
  }
  return nextQuestion;
}

Page(withThemePage({
  data: {
    sessionId: null,
    list: [],
    adaptive: null,
    currentIndex: 0,
    selectedValue: '',
    inputValue: '',
    audioBusy: false,
    submitting: false,
    answerFeedback: null,
    submitButtonText: '提交答案',
    options: [],
    hasQuestion: false,
    currentQuestion: null,
    reviewAiTutor: null,
    reviewAiEvidence: null,
    reviewAiLoading: false,
    reviewAiError: '',
    reviewAiAnswerVisible: false
  },

  onLoad() {
    this.reviewAiCache = {};
    this.reviewAiRequestToken = 0;
  },

  onShow() {
    this.loadTasks();
  },

  async loadTasks() {
    try {
      const data = await reviewApi.getReviewTasks({ limit: 8 });
      const list = data.list || [];
      this.setData({
        sessionId: data.session_id,
        list,
        adaptive: data.adaptive || null,
        currentIndex: 0,
        selectedValue: '',
        inputValue: '',
        hasQuestion: !!list.length
      });
      this.refreshQuestion(0, list);
    } catch (error) {
      wx.showToast({ title: '加载复习任务失败', icon: 'none' });
    }
  },

  resetReviewAiState() {
    this.setData({
      reviewAiTutor: null,
      reviewAiEvidence: null,
      reviewAiLoading: false,
      reviewAiError: '',
      reviewAiAnswerVisible: false
    });
  },

  refreshQuestion(index, list, resetAi = true) {
    const sourceList = list || this.data.list;
    const question = decoratePlayableQuestion(sourceList[index] || null);
    this.setData({
      currentQuestion: question,
      hasQuestion: !!question,
      answerFeedback: null,
      submitButtonText: '提交答案',
      options: question && question.options
        ? question.options.map((item) => ({
            key: item.key,
            value: item.value,
            className: item.value === this.data.selectedValue ? 'option-card list-item choice-active' : 'option-card list-item'
          }))
        : []
    });
    if (resetAi) {
      this.resetReviewAiState();
    }
  },

  chooseOption(event) {
    if (this.data.answerFeedback) {
      return;
    }
    const value = event.currentTarget.dataset.value;
    this.setData({ selectedValue: value });
    this.refreshQuestion(this.data.currentIndex, null, false);
  },

  handleInput(event) {
    if (this.data.answerFeedback) {
      return;
    }
    this.setData({ inputValue: event.detail.value || '' });
  },

  async playListeningAudio() {
    const question = this.data.currentQuestion;
    if (!question || !question.speech_text) {
      wx.showToast({ title: '当前题目没有音频', icon: 'none' });
      return;
    }
    this.setData({ audioBusy: true });
    try {
      await speech.speakText(question.speech_text, {
        lang: question.speech_lang || 'en-US'
      });
    } catch (error) {
      wx.showToast({ title: (error.message || '播放失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ audioBusy: false });
    }
  },

  async handleReviewAiTutor() {
    const question = this.data.currentQuestion;
    if (!question || !question.word_id) {
      wx.showToast({ title: '当前题目暂不支持 AI 讲词', icon: 'none' });
      return;
    }

    const cacheKey = String(question.word_id);
    if (this.reviewAiCache[cacheKey]) {
      this.setData({
        reviewAiTutor: this.reviewAiCache[cacheKey].tutor,
        reviewAiEvidence: this.reviewAiCache[cacheKey].evidence,
        reviewAiLoading: false,
        reviewAiError: '',
        reviewAiAnswerVisible: false
      });
      return;
    }

    const requestToken = ++this.reviewAiRequestToken;
    this.setData({
      reviewAiTutor: null,
      reviewAiEvidence: null,
      reviewAiLoading: true,
      reviewAiError: '',
      reviewAiAnswerVisible: false
    });

    try {
      const data = await aiApi.explainWord({ word_id: question.word_id });
      if (requestToken !== this.reviewAiRequestToken) {
        return;
      }
      if (!data || !data.tutor) {
        throw new Error('AI 讲词没有返回有效内容，请稍后再试');
      }
      this.reviewAiCache[cacheKey] = {
        tutor: data.tutor,
        evidence: data.evidence || null
      };
      this.setData({
        reviewAiTutor: data.tutor,
        reviewAiEvidence: data.evidence || null,
        reviewAiLoading: false,
        reviewAiError: '',
        reviewAiAnswerVisible: false
      });
    } catch (error) {
      if (requestToken !== this.reviewAiRequestToken) {
        return;
      }
      this.setData({
        reviewAiTutor: null,
        reviewAiEvidence: null,
        reviewAiLoading: false,
        reviewAiError: (error && error.message) || 'AI 讲词失败，请稍后再试',
        reviewAiAnswerVisible: false
      });
    }
  },

  handleClearReviewAiTutor() {
    this.resetReviewAiState();
  },

  toggleReviewAiAnswer() {
    this.setData({
      reviewAiAnswerVisible: !this.data.reviewAiAnswerVisible
    });
  },

  goAiWrongWords() {
    router.go('/pages/wrong-words/index');
  },

  async submitAnswer() {
    const question = this.data.currentQuestion;
    if (!question) {
      return;
    }

    if (this.data.answerFeedback) {
      const nextIndex = this.data.currentIndex + 1;
      if (nextIndex >= this.data.list.length) {
        wx.showToast({ title: '本轮复习完成', icon: 'success' });
        router.back();
        return;
      }
      this.setData({
        currentIndex: nextIndex,
        selectedValue: '',
        inputValue: ''
      });
      this.refreshQuestion(nextIndex);
      return;
    }

    const userAnswer = question.answer_mode === 'input' ? this.data.inputValue : this.data.selectedValue;
    if (!userAnswer) {
      wx.showToast({ title: '请先完成作答', icon: 'none' });
      return;
    }

    this.setData({ submitting: true });
    try {
      const data = await reviewApi.submitReview({
        session_id: this.data.sessionId,
        answers: [
          {
            word_id: question.word_id,
            user_answer: userAnswer,
            question_type: question.question_type
          }
        ]
      });
      const answerResult = data && data.answers && data.answers.length ? data.answers[0] : null;
      const feedback = answerResult && answerResult.answer_feedback
        ? Object.assign({}, answerResult.answer_feedback, {
            isCorrect: !!answerResult.is_correct,
            correctAnswer: answerResult.correct_answer,
            userAnswer: answerResult.user_answer,
            panelClass: answerResult.is_correct ? 'answer-feedback correct' : 'answer-feedback wrong'
          })
        : {
            isCorrect: false,
            correctAnswer: '',
            userAnswer,
            panelClass: 'answer-feedback wrong',
            title: '已提交',
            explanation: '本题结果已记录。',
            recovery_tip: ''
          };
      this.setData({
        answerFeedback: feedback,
        submitButtonText: this.data.currentIndex + 1 >= this.data.list.length ? '完成复习' : '下一题'
      });
    } catch (error) {
      wx.showToast({ title: (error.message || '提交失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({ submitting: false });
    }
  }
}));
