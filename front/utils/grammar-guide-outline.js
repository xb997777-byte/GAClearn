const BOOK_SOURCES = [
  {
    id: 'cambridge',
    title: 'English Grammar in Use',
    source: 'Cambridge',
    audience: '适合打基础',
    description: '按单元一步一步推进基础语法。'
  },
  {
    id: 'pearson',
    title: 'Azar-Hagen Grammar Series',
    source: 'Pearson',
    audience: '适合分级进阶',
    description: '更像完整教材体系，强调阶段递进。'
  },
  {
    id: 'oxford',
    title: 'Practical English Usage',
    source: 'Oxford',
    audience: '适合查难点',
    description: '适合中后期补易错点和疑难点。'
  }
];

const LEARNING_PATHS = [
  {
    id: 'step-1',
    title: '第 1 步：先稳住基础句',
    description: '先学最基本的人称、时态、疑问句和否定句。'
  },
  {
    id: 'step-2',
    title: '第 2 步：再抓主干结构',
    description: '进入五大基本句型、情态动词、比较结构。'
  },
  {
    id: 'step-3',
    title: '第 3 步：处理复杂结构',
    description: '系统进入完成时、非谓语、条件句和从句。'
  },
  {
    id: 'step-4',
    title: '第 4 步：最后攻长难句',
    description: '再专门处理倒装、强调、省略和平行结构。'
  }
];

const GUIDE_SUMMARIES = [
  {
    id: 'book-1',
    volume: '第 1 册',
    level: '入门基础',
    title: '先把最常见的简单句读顺',
    subtitle: '适合基础比较薄弱、经常连简单句都读不稳的人。',
    chapterCount: 6
  },
  {
    id: 'book-2',
    volume: '第 2 册',
    level: '基础句法',
    title: '把句子主干和常用扩展结构学扎实',
    subtitle: '适合已经能读简单句，但一长就容易散掉的人。',
    chapterCount: 6
  },
  {
    id: 'book-3',
    volume: '第 3 册',
    level: '进阶结构',
    title: '系统进入从句、非谓语和复杂时态',
    subtitle: '适合准备正式攻克阅读与写作复杂句的人。',
    chapterCount: 8
  },
  {
    id: 'book-4',
    volume: '第 4 册',
    level: '长难句提高',
    title: '专门训练阅读中的变形句和长难句',
    subtitle: '适合考研、四六级、雅思、托福等提高阶段。',
    chapterCount: 6
  }
];

module.exports = {
  BOOK_SOURCES,
  GUIDE_SUMMARIES,
  LEARNING_PATHS
};
