const aiApi = require('../../services/modules/ai');
const reviewApi = require('../../services/modules/review');
const store = require('../../store/app-store');
const router = require('../../utils/router');
const speech = require('../../utils/speech');
const { withThemePage } = require('../../utils/theme-manager');

const DEFAULT_REVIEW_BATCH_SIZE = 8;
const MIN_REVIEW_BATCH_SIZE = 1;
const MAX_REVIEW_BATCH_SIZE = 50;

function normalizeReviewBatchSize(value) {
  const parsed = parseInt(value, 10);
  if (Number.isNaN(parsed)) {
    return DEFAULT_REVIEW_BATCH_SIZE;
  }
  return Math.min(Math.max(parsed, MIN_REVIEW_BATCH_SIZE), MAX_REVIEW_BATCH_SIZE);
}

function buildQuestionPresentation(question) {
  const questionType = question && question.question_type ? question.question_type : '';
  const helperText = String((question && question.helper_text) || '').trim();

  switch (questionType) {
    case 'word_to_meaning':
      return {
        prompt_label: '看单词，选正确释义',
        presentation_mode: 'word',
        helper_role: helperText ? 'pos' : ''
      };
    case 'meaning_to_word':
      return {
        prompt_label: '看中文，选正确单词',
        presentation_mode: 'meaning',
        helper_role: helperText ? 'pos' : ''
      };
    case 'example_to_word':
      return {
        prompt_label: '结合例句，选缺失单词',
        presentation_mode: 'sentence',
        helper_role: helperText ? 'translation' : ''
      };
    case 'spelling':
      return {
        prompt_label: '根据中文，拼出完整单词',
        presentation_mode: 'meaning',
        helper_role: helperText ? 'hint' : ''
      };
    case 'listening_to_word':
      return {
        prompt_label: '听发音，选正确单词',
        presentation_mode: 'listening',
        helper_role: helperText ? 'hint' : ''
      };
    default:
      return {
        prompt_label: '完成这道复习题',
        presentation_mode: 'word',
        helper_role: helperText ? 'hint' : ''
      };
  }
}

function decoratePlayableQuestion(question) {
  if (!question) {
    return null;
  }
  const nextQuestion = Object.assign({}, question);
  if (!nextQuestion.speech_text && nextQuestion.question_type === 'word_to_meaning' && nextQuestion.stem) {
    nextQuestion.speech_text = nextQuestion.stem;
    nextQuestion.speech_lang = 'en-US';
  }
  const presentation = buildQuestionPresentation(nextQuestion);
  nextQuestion.prompt_label = presentation.prompt_label;
  nextQuestion.presentation_mode = presentation.presentation_mode;
  nextQuestion.helper_role = presentation.helper_role;
  return nextQuestion;
}

Page(withThemePage({
  data: {
    sessionId: null,
    list: [],
    adaptive: null,
    reviewBatchSize: DEFAULT_REVIEW_BATCH_SIZE,
    currentIndex: 0,
    scrollIntoViewTarget: '',
    selectedValue: '',
    inputValue: '',
    audioBusy: false,
    autoPlayAudioEnabled: true,
    submitting: false,
    submitDisabled: true,
    answerFeedback: null,
    submitButtonText: '提交答案',
    options: [],
    hasQuestion: false,
    currentQuestion: null,
    feedbackAudioBusy: false,
    reviewAiTutor: null,
    reviewAiEvidence: null,
    reviewAiLoading: false,
    reviewAiError: '',
    reviewAiAnswerVisible: false
  },

  onLoad() {
    this.reviewAiCache = {};
    this.reviewAiRequestToken = 0;
    this.preparedQuestionIndex = -1;
    this.preparedQuestionPayload = null;
    this.questionTransitioning = false;
  },

  onHide() {
    this.reviewAiRequestToken += 1;
  },

  onUnload() {
    this.reviewAiRequestToken += 1;
  },

  onShow() {
    const settings = store.getState().settings || {};
    const reviewBatchSize = normalizeReviewBatchSize(settings.review_batch_size);
    this.setData({
      autoPlayAudioEnabled: !!settings.auto_play_audio,
      reviewBatchSize
    });
    this.loadTasks(reviewBatchSize);
  },

  async loadTasks(limitOverride) {
    const nextLimit = normalizeReviewBatchSize(
      typeof limitOverride === 'number' || typeof limitOverride === 'string'
        ? limitOverride
        : this.data.reviewBatchSize
    );
    try {
      const data = await reviewApi.getReviewTasks({ limit: nextLimit });
      const list = data.list || [];
      this.preparedQuestionIndex = -1;
      this.preparedQuestionPayload = null;
      this.setData({
        sessionId: data.session_id,
        list,
        adaptive: data.adaptive || null,
        reviewBatchSize: nextLimit,
        currentIndex: 0,
        scrollIntoViewTarget: '',
        selectedValue: '',
        inputValue: '',
        submitDisabled: true,
        hasQuestion: !!list.length
      });
      this.refreshQuestion(0, list, true, true);
    } catch (error) {
      wx.showToast({ title: '加载复习任务失败', icon: 'none' });
    }
  },

  resetReviewAiState() {
    this.reviewAiRequestToken += 1;
    this.setData({
      feedbackAudioBusy: false,
      reviewAiTutor: null,
      reviewAiEvidence: null,
      reviewAiLoading: false,
      reviewAiError: '',
      reviewAiAnswerVisible: false
    });
  },

  buildQuestionOptions(question, selectedValue = '') {
    if (!question || !question.options) {
      return [];
    }
    return question.options.map((item) => ({
      key: item.key,
      value: item.value,
      className: item.value === selectedValue ? 'option-card list-item choice-active' : 'option-card list-item'
    }));
  },

  prepareNextQuestion(index, sourceList) {
    const list = sourceList || this.data.list || [];
    const question = decoratePlayableQuestion(list[index] || null);
    if (!question) {
      this.preparedQuestionIndex = -1;
      this.preparedQuestionPayload = null;
      return;
    }
    this.preparedQuestionIndex = index;
    this.preparedQuestionPayload = {
      question,
      options: this.buildQuestionOptions(question)
    };
  },

  takePreparedQuestion(index, selectedValue = '') {
    if (selectedValue || this.preparedQuestionIndex !== index || !this.preparedQuestionPayload) {
      return null;
    }
    const payload = this.preparedQuestionPayload;
    this.preparedQuestionIndex = -1;
    this.preparedQuestionPayload = null;
    return payload;
  },

  scrollToTarget(target) {
    if (!target) {
      return;
    }
    if (this.data.scrollIntoViewTarget === target) {
      this.setData({ scrollIntoViewTarget: '' }, () => {
        this.setData({ scrollIntoViewTarget: target });
      });
      return;
    }
    this.setData({ scrollIntoViewTarget: target });
  },

  getSubmitDisabledState(partial = {}) {
    const currentQuestion = Object.prototype.hasOwnProperty.call(partial, 'currentQuestion')
      ? partial.currentQuestion
      : this.data.currentQuestion;
    const answerFeedback = Object.prototype.hasOwnProperty.call(partial, 'answerFeedback')
      ? partial.answerFeedback
      : this.data.answerFeedback;
    const selectedValue = Object.prototype.hasOwnProperty.call(partial, 'selectedValue')
      ? partial.selectedValue
      : this.data.selectedValue;
    const inputValue = Object.prototype.hasOwnProperty.call(partial, 'inputValue')
      ? partial.inputValue
      : this.data.inputValue;
    const submitting = Object.prototype.hasOwnProperty.call(partial, 'submitting')
      ? partial.submitting
      : this.data.submitting;
    if (submitting || !currentQuestion) {
      return true;
    }
    if (answerFeedback) {
      return false;
    }
    if (currentQuestion.answer_mode === 'input') {
      return !String(inputValue || '').trim();
    }
    return !selectedValue;
  },

  refreshQuestion(index, list, resetAi = true, autoPlay = false) {
    const sourceList = list || this.data.list;
    const prepared = this.takePreparedQuestion(index, this.data.selectedValue);
    const question = prepared ? prepared.question : decoratePlayableQuestion(sourceList[index] || null);
    const options = prepared ? prepared.options : this.buildQuestionOptions(question, this.data.selectedValue);
    const nextState = {
      currentQuestion: question,
      hasQuestion: !!question,
      answerFeedback: null,
      submitButtonText: '提交答案',
      scrollIntoViewTarget: '',
      options
    };
    nextState.submitDisabled = this.getSubmitDisabledState(nextState);
    this.setData({
      currentQuestion: nextState.currentQuestion,
      hasQuestion: nextState.hasQuestion,
      answerFeedback: nextState.answerFeedback,
      submitButtonText: nextState.submitButtonText,
      scrollIntoViewTarget: nextState.scrollIntoViewTarget,
      options: nextState.options,
      submitDisabled: nextState.submitDisabled
    });
    if (resetAi) {
      this.resetReviewAiState();
    }
    this.prepareNextQuestion(index + 1, sourceList);
    if (autoPlay) {
      this.autoPlayCurrentQuestion();
    }
  },

  chooseOption(event) {
    if (this.data.answerFeedback || this.data.submitting || this.questionTransitioning) {
      return;
    }
    const value = event.currentTarget.dataset.value;
    this.setData({
      selectedValue: value,
      submitDisabled: this.getSubmitDisabledState({ selectedValue: value })
    }, () => {
      this.refreshQuestion(this.data.currentIndex, null, false);
    });
  },

  handleInput(event) {
    if (this.data.answerFeedback || this.data.submitting || this.questionTransitioning) {
      return;
    }
    const value = event.detail.value || '';
    this.setData({
      inputValue: value,
      submitDisabled: this.getSubmitDisabledState({ inputValue: value })
    });
  },

  autoPlayCurrentQuestion() {
    const settings = store.getState().settings || {};
    if (!settings.auto_play_audio) {
      return;
    }
    this.playListeningAudio(true);
  },

  async playListeningAudio(silent = false) {
    const question = this.data.currentQuestion;
    if (!question || !question.speech_text) {
      if (!silent) {
        wx.showToast({ title: '当前题目没有音频', icon: 'none' });
      }
      return;
    }
    this.setData({ audioBusy: true });
    try {
      await speech.speakText(question.speech_text, {
        lang: question.speech_lang || 'en-US'
      });
    } catch (error) {
      if (!silent) {
        wx.showToast({ title: (error.message || '播放失败').slice(0, 20), icon: 'none' });
      }
    } finally {
      this.setData({ audioBusy: false });
    }
  },

  async playFeedbackExampleAudio(silent = false) {
    const feedback = this.data.answerFeedback;
    if (!feedback || !feedback.example_sentence) {
      if (!silent) {
        wx.showToast({ title: '当前没有例句音频', icon: 'none' });
      }
      return;
    }
    this.setData({ feedbackAudioBusy: true });
    try {
      await speech.speakText(feedback.example_sentence, {
        lang: feedback.speech_lang || 'en-US'
      });
    } catch (error) {
      if (!silent) {
        wx.showToast({ title: (error.message || '播放失败').slice(0, 20), icon: 'none' });
      }
    } finally {
      this.setData({ feedbackAudioBusy: false });
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
    if (!question || this.data.submitting || this.questionTransitioning) {
      return;
    }

    if (this.data.answerFeedback) {
      this.questionTransitioning = true;
      const nextIndex = this.data.currentIndex + 1;
      if (nextIndex >= this.data.list.length) {
        this.questionTransitioning = false;
        wx.showToast({ title: '本轮复习完成', icon: 'success' });
        router.back();
        return;
      }
      this.setData({
        currentIndex: nextIndex,
        selectedValue: '',
        inputValue: '',
        scrollIntoViewTarget: '',
        submitDisabled: true,
        feedbackAudioBusy: false
      }, () => {
        this.refreshQuestion(nextIndex, null, true, true);
        this.scrollToTarget('review-question-anchor');
        this.questionTransitioning = false;
      });
      return;
    }

    const userAnswer = question.answer_mode === 'input' ? this.data.inputValue : this.data.selectedValue;
    if (!userAnswer) {
      wx.showToast({ title: '请先完成作答', icon: 'none' });
      return;
    }

    this.setData({
      submitting: true,
      submitDisabled: true
    });
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
            revealedWord: answerResult.word || question.stem || '',
            panelClass: answerResult.is_correct ? 'answer-feedback correct' : 'answer-feedback wrong'
          })
        : {
            isCorrect: false,
            correctAnswer: '',
            userAnswer,
            revealedWord: question.stem || '',
            panelClass: 'answer-feedback wrong',
            title: '已提交',
            explanation: '本题结果已记录。',
            recovery_tip: ''
          };
      const nextState = {
        answerFeedback: feedback,
        submitButtonText: this.data.currentIndex + 1 >= this.data.list.length ? '完成复习' : '下一题'
      };
      nextState.submitDisabled = this.getSubmitDisabledState(nextState);
      this.setData({
        answerFeedback: nextState.answerFeedback,
        submitButtonText: nextState.submitButtonText,
        submitDisabled: nextState.submitDisabled,
        feedbackAudioBusy: false
      }, () => {
        this.scrollToTarget('review-feedback-anchor');
        if (feedback && feedback.example_sentence) {
          this.playFeedbackExampleAudio(true);
        }
      });
    } catch (error) {
      wx.showToast({ title: (error.message || '提交失败').slice(0, 20), icon: 'none' });
    } finally {
      this.setData({
        submitting: false,
        submitDisabled: this.getSubmitDisabledState({ submitting: false })
      });
    }
  }
}));
