const grammarApi = require('../../services/modules/grammar');
const router = require('../../utils/router');
const { withThemePage } = require('../../utils/theme-manager');

const MODULES = [
  {
    id: 'guide',
    title: '语法总览',
    subtitle: '像一本语法书一样，从简单到困难，按顺序带你把语法体系学完整。',
    fit: '适合先打基础、按阶段系统推进的人',
    tags: ['循序渐进', '分册学习', '基础到提高'],
    url: '/pages/grammar-guide/index',
    theme: 'guide',
    buttonText: '查看总览'
  },
  {
    id: 'analyze',
    title: '自动拆句',
    subtitle: '输入任意英文句子，立刻拆出主干、修饰层和中文解释。',
    fit: '适合想查当前一句话到底怎么读的人',
    tags: ['自由输入', '即时分析', '颜色标注'],
    url: '/pages/grammar-analyze/index',
    theme: 'analyze',
    buttonText: '开始拆句'
  },
  {
    id: 'examples',
    title: '例句学语法',
    subtitle: '按专题、难度和句库例句来学，把语法规则放进真实句子里。',
    fit: '适合系统刷句子、按专题持续学习的人',
    tags: ['句库学习', '主干视图', '专项练习'],
    url: '/pages/grammar-examples/index',
    theme: 'examples',
    buttonText: '进入句库'
  }
];

Page(withThemePage({
  data: {
    modules: MODULES,
    progress: null,
    topicCount: 0,
    sentenceCount: 0,
    initialized: false
  },

  onShow() {
    getApp().setTabBarSelected(2);
    this.loadSummary();
  },

  async loadSummary() {
    try {
      const [progress, topicsData] = await Promise.all([
        grammarApi.getProgress(),
        grammarApi.listTopics()
      ]);

      const topics = topicsData && topicsData.list ? topicsData.list : [];
      const sentenceCount = topics.reduce((total, item) => total + Number(item.sentence_count || 0), 0);

      this.setData({
        progress: progress || null,
        topicCount: topics.length,
        sentenceCount,
        initialized: true
      });
    } catch (error) {
      this.setData({ initialized: true });
    }
  },

  handleOpenModule(event) {
    const url = event.currentTarget.dataset.url;
    if (!url) {
      return;
    }
    router.go(url);
  },

  handleContinueExamples() {
    router.go('/pages/grammar-guide/index');
  },

  goAiGrammar() {
    router.go('/pages/ai-center/index?tab=apps&workspace=grammar');
  }
}));
