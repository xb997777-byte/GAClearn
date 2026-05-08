const examsApi = require('../../services/modules/exams');
const { withThemePage } = require('../../utils/theme-manager');

Page(withThemePage({
  data: {
    navTitle: '词汇测试',
    mode: 'practice',
    loading: true,
    testId: null,
    questions: [],
    currentIndex: 0,
    selectedValue: '',
    inputValue: '',
    currentQuestion: null,
    options: [],
    answersMap: {},
    completed: false,
    result: null
  },

  onLoad(options) {
    const mode = options && options.mode === 'placement' ? 'placement' : 'practice';
    this.setData({
      mode,
      navTitle: mode === 'placement' ? '分级测试' : '词汇测试'
    });
    this.loadTest(mode);
  },

  async loadTest(mode) {
    this.setData({ loading: true });
    try {
      const data = mode === 'placement'
        ? await examsApi.generatePlacementTest({ question_count: 18 })
        : await examsApi.generateTest({ question_count: 12 });
      this.setData({
        testId: data.test_id,
        questions: data.questions || [],
        currentIndex: 0,
        selectedValue: '',
        inputValue: '',
        answersMap: {},
        completed: false,
        result: null,
        loading: false
      });
      this.refreshQuestion(0, data.questions || []);
    } catch (error) {
      wx.showToast({ title: (error.message || '加载测试失败').slice(0, 20), icon: 'none' });
      this.setData({ loading: false });
    }
  },

  refreshQuestion(index, questions) {
    const source = questions || this.data.questions;
    const question = source[index] || null;
    const savedAnswer = (this.data.answersMap || {})[question ? question.question_id : 0] || {};
    this.setData({
      currentQuestion: question,
      selectedValue: question && savedAnswer.selected_option ? question.options[savedAnswer.selected_option] || '' : '',
      inputValue: savedAnswer.submitted_text || '',
      options: question && question.answer_mode === 'choice'
        ? Object.keys(question.options || {}).map((key) => ({
            key,
            value: question.options[key],
            className: savedAnswer.selected_option === key
              ? 'option-card list-item choice-active'
              : 'option-card list-item'
          }))
        : []
    });
  },

  chooseOption(event) {
    const value = event.currentTarget.dataset.value;
    this.setData({ selectedValue: value }, () => {
      const question = this.data.currentQuestion;
      if (!question) {
        return;
      }
      const selectedKey = Object.keys(question.options || {}).find((key) => question.options[key] === value) || '';
      this.setData({
        options: Object.keys(question.options || {}).map((key) => ({
          key,
          value: question.options[key],
          className: selectedKey === key ? 'option-card list-item choice-active' : 'option-card list-item'
        }))
      });
    });
  },

  handleInput(event) {
    this.setData({ inputValue: event.detail.value || '' });
  },

  saveCurrentAnswer() {
    const question = this.data.currentQuestion;
    if (!question) {
      return false;
    }
    if (question.answer_mode === 'choice' && !this.data.selectedValue) {
      wx.showToast({ title: '请先选择答案', icon: 'none' });
      return false;
    }
    if (question.answer_mode === 'input' && !this.data.inputValue) {
      wx.showToast({ title: '请先输入答案', icon: 'none' });
      return false;
    }

    const nextMap = Object.assign({}, this.data.answersMap, {
      [question.question_id]: {
        question_id: question.question_id,
        selected_option: question.answer_mode === 'choice'
          ? Object.keys(question.options || {}).find((key) => question.options[key] === this.data.selectedValue) || ''
          : '',
        submitted_text: question.answer_mode === 'input' ? this.data.inputValue : ''
      }
    });
    this.setData({ answersMap: nextMap });
    return true;
  },

  handleNext() {
    if (!this.saveCurrentAnswer()) {
      return;
    }
    const nextIndex = this.data.currentIndex + 1;
    if (nextIndex >= this.data.questions.length) {
      this.handleSubmit();
      return;
    }
    this.setData({ currentIndex: nextIndex }, () => {
      this.refreshQuestion(nextIndex);
    });
  },

  async handleSubmit() {
    if (!this.saveCurrentAnswer()) {
      return;
    }
    try {
      const answers = Object.keys(this.data.answersMap).map((key) => this.data.answersMap[key]);
      const result = this.data.mode === 'placement'
        ? await examsApi.submitPlacementTest({ test_id: this.data.testId, answers })
        : await examsApi.submitTest({ test_id: this.data.testId, answers });
      this.setData({
        completed: true,
        result
      });
    } catch (error) {
      wx.showToast({ title: (error.message || '提交失败').slice(0, 20), icon: 'none' });
    }
  },

  handleRestart() {
    this.loadTest(this.data.mode);
  }
}));
