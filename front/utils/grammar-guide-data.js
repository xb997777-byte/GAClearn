const BOOK_SOURCES = [
  {
    id: 'cambridge',
    title: 'English Grammar in Use',
    source: 'Cambridge',
    audience: '适合打基础、自学跟读',
    description: '强调从基础时态、疑问句、情态动词到从句、被动语态，按照单元逐步推进。',
    focus: '适合用来设计“先基础、后进阶”的语法学习顺序。'
  },
  {
    id: 'pearson',
    title: 'Azar-Hagen Grammar Series',
    source: 'Pearson',
    audience: '适合分级进阶学习',
    description: '以 Basic / Fundamentals / Understanding and Using 等层级递进，结构非常像一套完整教材。',
    focus: '适合把小程序语法内容拆成多个学习阶段，而不是全部平铺。'
  },
  {
    id: 'oxford',
    title: 'Practical English Usage',
    source: 'Oxford',
    audience: '适合中后期查难点',
    description: '更擅长处理易混点、疑难点和“为什么这样说”的问题。',
    focus: '适合在进阶阶段补充易错提醒和长难句疑难解释。'
  }
];

const LEARNING_PATHS = [
  {
    id: 'step-1',
    title: '第 1 步：先把最基础的句子读顺',
    description: '先学 be 动词、代词、冠词、一般现在时、疑问句和否定句，让最简单的句子不再卡壳。'
  },
  {
    id: 'step-2',
    title: '第 2 步：再把句子主干抓稳',
    description: '进入五大基本句型、过去将来时、情态动词和比较结构，训练“谁做了什么”的判断。'
  },
  {
    id: 'step-3',
    title: '第 3 步：开始理解复杂结构',
    description: '系统学习完成时、被动语态、非谓语、条件句和从句，建立多层句子阅读能力。'
  },
  {
    id: 'step-4',
    title: '第 4 步：最后专门攻长难句',
    description: '把倒装、强调、省略、平行结构和长难句拆解放在最后，作为真正的提高阶段。'
  }
];

const CHAPTER_DETAILS = {
  '01': {
    coreRule: '英语最小句子通常先看“谁”再看“做什么/是什么”。看到句子先别急着翻译，先找主语和谓语。',
    patterns: [
      '主语 + be 动词 + 表语',
      '主语 + 谓语动词',
      '主语 + 谓语动词 + 宾语'
    ],
    examples: [
      { en: 'Tom is busy today.', cn: 'Tom 今天很忙。' },
      { en: 'Birds fly.', cn: '鸟会飞。' }
    ],
    mistakes: [
      '一上来逐词翻译，没有先找到句子主干。',
      '把句首第一个词机械当成主语。'
    ],
    studyTip: '先问自己两个问题：这句话在说谁？这个人或事物处于什么状态、做了什么动作？'
  },
  '02': {
    coreRule: 'be 动词会随着主语的人称和数变化。人称代词是最基础的主语替换工具。',
    patterns: [
      'I am / You are / He is / She is / They are',
      '主语 + be + 形容词/名词/地点'
    ],
    examples: [
      { en: 'She is a new student.', cn: '她是一名新同学。' },
      { en: 'They are in the library.', cn: '他们在图书馆里。' }
    ],
    mistakes: [
      'He / She 后面误接 are。',
      '复数主语后面仍然使用 is。'
    ],
    studyTip: '把人称代词和 be 动词当成固定搭配先背熟，后面很多句型都靠它打底。'
  },
  '03': {
    coreRule: '冠词和限定词决定名词是不是第一次出现、是否特指、数量是单数还是复数。',
    patterns: [
      'a/an + 单数可数名词',
      'the + 特指名词',
      'this/that/these/those + 名词'
    ],
    examples: [
      { en: 'I saw a cat near the door.', cn: '我在门边看见了一只猫。' },
      { en: 'These books are useful.', cn: '这些书很有用。' }
    ],
    mistakes: [
      '把不可数名词前随意加 a/an。',
      '第一次提到和再次提到同一名词时，冠词不区分。'
    ],
    studyTip: '先学会判断名词是“泛指还是特指”“可数还是不可数”，冠词就好用很多。'
  },
  '04': {
    coreRule: '一般现在时主要表达习惯、事实、常态和普遍规律。第三人称单数要注意动词变化。',
    patterns: [
      '主语 + 动词原形',
      '第三人称单数 + 动词-s/es',
      'always / usually / often / every day'
    ],
    examples: [
      { en: 'I walk to school every day.', cn: '我每天步行去学校。' },
      { en: 'My brother studies English at night.', cn: '我哥哥晚上学英语。' }
    ],
    mistakes: [
      'he/she/it 后面忘记给动词加 s。',
      '把正在发生的动作也一律用一般现在时。'
    ],
    studyTip: '看到频率副词和规律性时间表达时，先优先考虑一般现在时。'
  },
  '05': {
    coreRule: '一般过去时描述过去已经完成的动作或状态，常和 yesterday、last week、ago 连用。',
    patterns: [
      '主语 + 动词过去式',
      'be 动词过去式 was / were'
    ],
    examples: [
      { en: 'We visited our teacher last Friday.', cn: '上周五我们去看了老师。' },
      { en: 'She was tired after the trip.', cn: '旅行后她很累。' }
    ],
    mistakes: [
      'did 已经出现时，后面动词还继续用过去式。',
      '不规则动词过去式记不牢。'
    ],
    studyTip: '看到明确过去时间，就先想过去式；练习时重点整理高频不规则动词。'
  },
  '06': {
    coreRule: '疑问句和否定句不是靠中文语感改，而是靠助动词和 be 动词调序或加 not。',
    patterns: [
      'Do/Does/Did + 主语 + 动词原形?',
      'Be 动词 + 主语 + 表语?',
      '主语 + do/does/did not + 动词原形'
    ],
    examples: [
      { en: 'Do you like music?', cn: '你喜欢音乐吗？' },
      { en: 'She does not live here.', cn: '她不住在这里。' }
    ],
    mistakes: [
      'Did you went...? 这类双重过去。',
      'be 动词句型提问时忘记把 be 提到前面。'
    ],
    studyTip: '先判断原句谓语是 be 还是实义动词，再决定怎么提问或否定。'
  },
  '07': {
    coreRule: '五大基本句型是后面所有长句的骨架。长句再复杂，也通常能还原到这些基础结构。',
    patterns: [
      '主谓',
      '主系表',
      '主谓宾',
      '主谓双宾',
      '主谓宾补'
    ],
    examples: [
      { en: 'The baby cried.', cn: '婴儿哭了。' },
      { en: 'They elected him monitor.', cn: '他们选他当班长。' }
    ],
    mistakes: [
      '把表语误判成宾语。',
      '双宾和宾补结构分不清。'
    ],
    studyTip: '读句子时先问：这个动词后面是接“东西”、接“人和东西”，还是在说明结果和状态？'
  },
  '08': {
    coreRule: '一般将来时既能表示未来计划，也能表示说话当下的预测。will 和 be going to 语气略有差别。',
    patterns: [
      '主语 + will + 动词原形',
      '主语 + be going to + 动词原形'
    ],
    examples: [
      { en: 'I will call you tonight.', cn: '我今晚会给你打电话。' },
      { en: 'They are going to move next month.', cn: '他们下个月要搬家。' }
    ],
    mistakes: [
      'be going to 后面漏掉 be 动词。',
      '未来时间词出现时，仍然机械用一般现在时。'
    ],
    studyTip: '临时决定偏向 will，已有计划或迹象更常用 be going to。'
  },
  '09': {
    coreRule: '情态动词表达能力、建议、义务、可能性等说话人态度，后面一律接动词原形。',
    patterns: [
      'can / could + 动词原形',
      'should + 动词原形',
      'must + 动词原形',
      'may / might + 动词原形'
    ],
    examples: [
      { en: 'You should review the notes again.', cn: '你应该再复习一遍笔记。' },
      { en: 'She can finish the task alone.', cn: '她能独自完成任务。' }
    ],
    mistakes: [
      '情态动词后面接 to do。',
      '把 must 和 should 的语气强度混掉。'
    ],
    studyTip: '学习情态动词时不要只背中文释义，要体会“说话人态度的强弱”。'
  },
  '10': {
    coreRule: '时间、地点、方式状语是主干外的补充层，用来告诉你动作何时、何地、如何发生。',
    patterns: [
      'at/in/on + 时间或地点',
      'with/by + 方式',
      '副词修饰动词'
    ],
    examples: [
      { en: 'She speaks English fluently in class.', cn: '她在课堂上英语说得很流利。' },
      { en: 'We met at the station after lunch.', cn: '午饭后我们在车站见面了。' }
    ],
    mistakes: [
      '看到介词短语很多，就误把它们都当主干的一部分。',
      '副词和形容词位置混乱。'
    ],
    studyTip: '先把主干读完，再把这些状语当作补充层往回加，阅读会清楚很多。'
  },
  '11': {
    coreRule: '比较级和最高级本质上是在比较对象和程度，先看“拿谁和谁比”，再看形式。',
    patterns: [
      'A is taller than B.',
      'A is more useful than B.',
      'A is the tallest in the group.'
    ],
    examples: [
      { en: 'This question is easier than the last one.', cn: '这道题比上一道更容易。' },
      { en: 'She is the most careful student in the class.', cn: '她是班里最认真的学生。' }
    ],
    mistakes: [
      '比较对象不一致，句子逻辑不通。',
      '短词长词的比较级形式混用。'
    ],
    studyTip: '做比较结构时一定把 than 前后真正比较的对象圈出来。'
  },
  '12': {
    coreRule: '被动语态强调“动作被做在谁身上”，基础形式是 be + 过去分词。',
    patterns: [
      'is/am/are + done',
      'was/were + done'
    ],
    examples: [
      { en: 'The window was broken yesterday.', cn: '窗户昨天被打破了。' },
      { en: 'English is spoken in many countries.', cn: '很多国家都说英语。' }
    ],
    mistakes: [
      '只写过去分词，不写 be 动词。',
      '把形容词和被动结构混淆。'
    ],
    studyTip: '先判断句子想强调的是“谁做了”还是“谁被怎样了”。'
  },
  '13': {
    coreRule: '完成时的核心不是“已经”两个字，而是把动作和另一个时间点联系起来。',
    patterns: [
      'have/has + 过去分词',
      'had + 过去分词'
    ],
    examples: [
      { en: 'I have finished my homework.', cn: '我已经完成作业了。' },
      { en: 'They had left before the rain started.', cn: '下雨前他们就离开了。' }
    ],
    mistakes: [
      '把一般过去和现在完成随意混用。',
      '过去完成时没有“过去中的过去”意识。'
    ],
    studyTip: '看到 before、already、yet、by the time 这类线索时，要主动考虑完成时。'
  },
  '14': {
    coreRule: '进行时突出动作正在进行或持续，完成进行时强调“从过去延续到现在/某时”的过程。',
    patterns: [
      'am/is/are + doing',
      'was/were + doing',
      'have/has been + doing'
    ],
    examples: [
      { en: 'She is preparing for the speech now.', cn: '她现在正在准备演讲。' },
      { en: 'I have been waiting here for an hour.', cn: '我已经在这里等了一个小时。' }
    ],
    mistakes: [
      '所有现在发生的动作都误写成一般现在时。',
      '完成进行时只记形式，不理解其“持续到现在”的意味。'
    ],
    studyTip: '看到 now、at the moment、for two hours 这类词时，要注意动作的过程感。'
  },
  '15': {
    coreRule: '被动语态系统化时，要先判断原句时态，再把对应的 be 动词变成被动形式。',
    patterns: [
      'is done / was done / will be done',
      'has been done / had been done'
    ],
    examples: [
      { en: 'The report will be sent tomorrow.', cn: '报告明天会被发出。' },
      { en: 'The plan has been changed twice.', cn: '这个计划已经被改过两次。' }
    ],
    mistakes: [
      '只会一般现在和一般过去的被动，遇到完成时就乱。',
      '主动句转被动时宾语和主语没有对应好。'
    ],
    studyTip: '练习时可以先写主动句，再手动把宾语提到前面，最容易看清被动转换。'
  },
  '16': {
    coreRule: '不定式和动名词都能当“整体成分”，但语义侧重点不同：to do 常偏目的/计划，doing 常偏行为本身。',
    patterns: [
      'to do 作主语/宾语/补语',
      'doing 作主语/宾语'
    ],
    examples: [
      { en: 'To learn a language takes time.', cn: '学一门语言需要时间。' },
      { en: 'She enjoys reading before bed.', cn: '她喜欢睡前阅读。' }
    ],
    mistakes: [
      '只背“某动词后接 to do / doing”，不理解语义差别。',
      '把非谓语误当成句子的谓语。'
    ],
    studyTip: '先判断这整个结构在句中充当什么成分，再看它内部怎么翻译。'
  },
  '17': {
    coreRule: '分词结构常用来压缩信息，修饰名词或补充背景。它看起来像动词，但通常不是主句谓语。',
    patterns: [
      'doing 修饰主动进行',
      'done 修饰被动完成',
      '分词短语作状语'
    ],
    examples: [
      { en: 'The girl standing by the window is my cousin.', cn: '站在窗边的那个女孩是我表妹。' },
      { en: 'Given more time, we could improve the design.', cn: '如果再多给一些时间，我们可以改进设计。' }
    ],
    mistakes: [
      '看到 doing/done 就立刻当谓语。',
      '分词修饰对象不明确，出现悬垂修饰。'
    ],
    studyTip: '先找主句真正的谓语，再判断分词结构是在修饰谁、补充什么信息。'
  },
  '18': {
    coreRule: '条件句和虚拟语气关键在于“真实还是假设”。真实条件看事实，虚拟条件看不真实情况。',
    patterns: [
      'If + 一般现在时, 主句 will + 动词原形',
      'If + 一般过去时, 主句 would + 动词原形',
      'If + had done, 主句 would have done'
    ],
    examples: [
      { en: 'If it rains tomorrow, we will stay inside.', cn: '如果明天下雨，我们就待在室内。' },
      { en: 'If I were you, I would ask for help.', cn: '如果我是你，我会去求助。' }
    ],
    mistakes: [
      '真实条件和虚拟条件的时态搭配混乱。',
      'If I was you 这类结构在正式英语中不规范。'
    ],
    studyTip: '先判断说话人是在谈现实可能，还是在谈假设、后悔、建议。'
  },
  '19': {
    coreRule: '名词性从句整体充当一个名词成分，可以做主语、宾语、表语或同位语。',
    patterns: [
      'that / whether / if 从句',
      'what / how / why / who 引导的从句'
    ],
    examples: [
      { en: 'What she said was true.', cn: '她说的话是真的。' },
      { en: 'I wonder whether he will come.', cn: '我想知道他会不会来。' }
    ],
    mistakes: [
      '从句内部还硬套疑问句语序。',
      'that 从句中 that 和 whether 的功能不区分。'
    ],
    studyTip: '把整段从句先当成一个“大名词块”，再看它在整句里占什么位置。'
  },
  '20': {
    coreRule: '定语从句修饰名词，状语从句补充时间、原因、条件、让步等逻辑关系。',
    patterns: [
      '名词 + who/which/that ...',
      'when / because / although / if 引导状语从句'
    ],
    examples: [
      { en: 'The book that you lent me is helpful.', cn: '你借给我的那本书很有帮助。' },
      { en: 'Although he was tired, he kept working.', cn: '虽然他很累，但他还是继续工作。' }
    ],
    mistakes: [
      '一遇到关系代词就忘了主句主干。',
      '状语从句只记连接词，不理解逻辑关系。'
    ],
    studyTip: '看从句时先问：它是在修饰前面的名词，还是在说明整句发生的背景和逻辑？'
  },
  '21': {
    coreRule: '强调、倒装和否定前置的本质是语序变化。先还原正常语序，再判断强调重点。',
    patterns: [
      'It is/was ... that ...',
      'Not only + 助动词 + 主语 + 动词',
      'Only then / Never / Seldom 开头的倒装'
    ],
    examples: [
      { en: 'It was Tom that solved the problem.', cn: '正是 Tom 解决了这个问题。' },
      { en: 'Not only did she apologize, but she also fixed the mistake.', cn: '她不仅道了歉，还改正了错误。' }
    ],
    mistakes: [
      '看到倒装就以为是疑问句。',
      '强调句和普通主系表结构混淆。'
    ],
    studyTip: '复杂语序先还原，别直接硬译。先恢复成正常陈述句，理解会快很多。'
  },
  '22': {
    coreRule: '高阶虚拟语气常出现在建议、命令、要求、愿望、假设的表达中，形式比基础条件句更复杂。',
    patterns: [
      'suggest / demand / insist that + 主语 + (should) do',
      'wish + 一般过去/过去完成'
    ],
    examples: [
      { en: 'The teacher suggested that we review the passage again.', cn: '老师建议我们再复习一遍这篇文章。' },
      { en: 'I wish I had started earlier.', cn: '我真希望我更早开始。' }
    ],
    mistakes: [
      'suggest 后面误写成 to do。',
      'wish 后面时态不后退。'
    ],
    studyTip: '看到建议、要求、愿望类动词时，先检查后面有没有虚拟结构。'
  },
  '23': {
    coreRule: '省略和替代是为了避免重复，阅读时要学会把被省掉的部分在脑中补回来。',
    patterns: [
      'when possible / if necessary',
      'so do I / neither do I',
      'one / ones / do so / so'
    ],
    examples: [
      { en: 'When necessary, we will change the schedule.', cn: '必要时我们会调整日程。' },
      { en: 'She likes the blue pen, and I do too.', cn: '她喜欢那支蓝笔，我也是。' }
    ],
    mistakes: [
      '看到省略结构就以为句子残缺。',
      '替代词指代对象不清。'
    ],
    studyTip: '遇到短而怪的句子时，先想想有没有什么重复成分被省略了。'
  },
  '24': {
    coreRule: '并列和平行结构要求形式一致，逻辑连接词决定前后是递进、转折、对比还是选择。',
    patterns: [
      'A and B / not only A but also B',
      'rather than / instead of / while / whereas'
    ],
    examples: [
      { en: 'The course improves both reading and writing.', cn: '这门课程同时提升阅读和写作。' },
      { en: 'She chose to stay rather than complain.', cn: '她选择留下，而不是抱怨。' }
    ],
    mistakes: [
      '并列两边词性或结构不一致。',
      'but、while、whereas 的逻辑差别不分。'
    ],
    studyTip: '看到并列词时，主动检查它两边连接的是不是同类成分。'
  },
  '25': {
    coreRule: '标点和插入语决定句子的切层方式。逗号后面的内容不一定是主干的一部分。',
    patterns: [
      '主句, 插入语, 主句',
      '破折号 / 括号补充说明'
    ],
    examples: [
      { en: 'The plan, to be honest, still needs work.', cn: '说实话，这个计划仍然需要打磨。' },
      { en: 'Her answer — though short — was clear.', cn: '她的回答虽然简短，却很清楚。' }
    ],
    mistakes: [
      '把插入语和主干混成一整块。',
      '一见逗号就停止理解，不继续往下串。'
    ],
    studyTip: '逗号、破折号、括号常常是在提醒你“这里是补充层”，先别让它打断主干。'
  },
  '26': {
    coreRule: '长难句拆解的顺序比词汇量更重要。先主干，再从句，再非谓语，最后修饰层。',
    patterns: [
      '第一步找主语和谓语',
      '第二步划出从句边界',
      '第三步识别非谓语',
      '第四步回填介词短语和修饰语'
    ],
    examples: [
      { en: 'The report that was submitted yesterday is being reviewed by the committee.', cn: '昨天提交的那份报告正在被委员会审阅。' },
      { en: 'Students hoping to improve quickly should first master the sentence core.', cn: '想要快速提升的学生应该先掌握句子主干。' }
    ],
    mistakes: [
      '还没找到主干就开始抠每个生词。',
      '看到多个从句和修饰语时失去层次感。'
    ],
    studyTip: '把长句当成“主干 + 多层补充”来处理，不要试图一眼一次性全部吃下。'
  }
};

const PATTERN_EXAMPLE_OVERRIDES = {
  '01': [
    {
      pattern: '主语 + be 动词 + 表语',
      example: { en: 'Tom is busy today.', cn: 'Tom 今天很忙。' }
    },
    {
      pattern: '主语 + 谓语动词',
      example: { en: 'Birds fly.', cn: '鸟会飞。' }
    },
    {
      pattern: '主语 + 谓语动词 + 宾语',
      example: { en: 'She reads English newspapers every morning.', cn: '她每天早上读英文报纸。' }
    }
  ],
  '03': [
    {
      pattern: 'a/an + 单数可数名词',
      example: { en: 'I saw a cat near the door.', cn: '我在门边看见了一只猫。' }
    },
    {
      pattern: 'the + 特指名词',
      example: { en: 'Please close the window beside you.', cn: '请关上你旁边那扇窗。' }
    },
    {
      pattern: 'this/that/these/those + 名词',
      example: { en: 'These books are useful.', cn: '这些书很有用。' }
    }
  ],
  '04': [
    {
      pattern: '主语 + 动词原形',
      example: { en: 'I walk to school every day.', cn: '我每天步行去学校。' }
    },
    {
      pattern: '第三人称单数 + 动词-s/es',
      example: { en: 'My brother studies English at night.', cn: '我哥哥晚上学英语。' }
    },
    {
      pattern: 'always / usually / often / every day',
      example: { en: 'She usually drinks milk before bed.', cn: '她通常睡前喝牛奶。' }
    }
  ],
  '06': [
    {
      pattern: 'Do/Does/Did + 主语 + 动词原形?',
      example: { en: 'Do you like music?', cn: '你喜欢音乐吗？' }
    },
    {
      pattern: 'Be 动词 + 主语 + 表语?',
      example: { en: 'Is she ready for the test?', cn: '她准备好考试了吗？' }
    },
    {
      pattern: '主语 + do/does/did not + 动词原形',
      example: { en: 'She does not live here.', cn: '她不住在这里。' }
    }
  ],
  '07': [
    {
      pattern: '主谓',
      example: { en: 'The baby cried.', cn: '婴儿哭了。' }
    },
    {
      pattern: '主系表',
      example: { en: 'The soup smells delicious.', cn: '这汤闻起来很香。' }
    },
    {
      pattern: '主谓宾',
      example: { en: 'She opened the window.', cn: '她打开了窗户。' }
    },
    {
      pattern: '主谓双宾',
      example: { en: 'My father bought me a dictionary.', cn: '我爸爸给我买了一本词典。' }
    },
    {
      pattern: '主谓宾补',
      example: { en: 'They elected him monitor.', cn: '他们选他当班长。' }
    }
  ],
  '09': [
    {
      pattern: 'can / could + 动词原形',
      example: { en: 'She can finish the task alone.', cn: '她能独自完成任务。' }
    },
    {
      pattern: 'should + 动词原形',
      example: { en: 'You should review the notes again.', cn: '你应该再复习一遍笔记。' }
    },
    {
      pattern: 'must + 动词原形',
      example: { en: 'We must wear school uniforms on Monday.', cn: '周一我们必须穿校服。' }
    },
    {
      pattern: 'may / might + 动词原形',
      example: { en: 'It might rain this evening.', cn: '今晚可能会下雨。' }
    }
  ],
  '10': [
    {
      pattern: 'at/in/on + 时间或地点',
      example: { en: 'We met at the station after lunch.', cn: '午饭后我们在车站见面了。' }
    },
    {
      pattern: 'with/by + 方式',
      example: { en: 'She traveled by train to Beijing.', cn: '她乘火车去了北京。' }
    },
    {
      pattern: '副词修饰动词',
      example: { en: 'She speaks English fluently in class.', cn: '她在课堂上英语说得很流利。' }
    }
  ],
  '11': [
    {
      pattern: 'A is taller than B.',
      example: { en: 'Tom is taller than Jack.', cn: 'Tom 比 Jack 高。' }
    },
    {
      pattern: 'A is more useful than B.',
      example: { en: 'This dictionary is more useful than that app.', cn: '这本词典比那个应用更有用。' }
    },
    {
      pattern: 'A is the tallest in the group.',
      example: { en: 'Jack is the tallest in our team.', cn: 'Jack 是我们队里最高的。' }
    }
  ],
  '14': [
    {
      pattern: 'am/is/are + doing',
      example: { en: 'She is preparing for the speech now.', cn: '她现在正在准备演讲。' }
    },
    {
      pattern: 'was/were + doing',
      example: { en: 'They were having dinner when I called.', cn: '我打电话时他们正在吃晚饭。' }
    },
    {
      pattern: 'have/has been + doing',
      example: { en: 'I have been waiting here for an hour.', cn: '我已经在这里等了一个小时。' }
    }
  ],
  '17': [
    {
      pattern: 'doing 修饰主动进行',
      example: { en: 'The girl standing by the window is my cousin.', cn: '站在窗边的那个女孩是我表妹。' }
    },
    {
      pattern: 'done 修饰被动完成',
      example: { en: 'The homework finished yesterday was handed in on time.', cn: '昨天完成的作业按时交上去了。' }
    },
    {
      pattern: '分词短语作状语',
      example: { en: 'Given more time, we could improve the design.', cn: '如果再多给一些时间，我们可以改进设计。' }
    }
  ],
  '18': [
    {
      pattern: 'If + 一般现在时, 主句 will + 动词原形',
      example: { en: 'If it rains tomorrow, we will stay inside.', cn: '如果明天下雨，我们就待在室内。' }
    },
    {
      pattern: 'If + 一般过去时, 主句 would + 动词原形',
      example: { en: 'If I were you, I would ask for help.', cn: '如果我是你，我会去求助。' }
    },
    {
      pattern: 'If + had done, 主句 would have done',
      example: { en: 'If she had left earlier, she would have caught the train.', cn: '如果她早点出发，她本来就能赶上火车。' }
    }
  ],
  '21': [
    {
      pattern: 'It is/was ... that ...',
      example: { en: 'It was Tom that solved the problem.', cn: '正是 Tom 解决了这个问题。' }
    },
    {
      pattern: 'Not only + 助动词 + 主语 + 动词',
      example: { en: 'Not only did she apologize, but she also fixed the mistake.', cn: '她不仅道了歉，还改正了错误。' }
    },
    {
      pattern: 'Only then / Never / Seldom 开头的倒装',
      example: { en: 'Only then did I understand the rule.', cn: '直到那时我才明白这个规则。' }
    }
  ],
  '23': [
    {
      pattern: 'when possible / if necessary',
      example: { en: 'When necessary, we will change the schedule.', cn: '必要时我们会调整日程。' }
    },
    {
      pattern: 'so do I / neither do I',
      example: { en: 'I enjoy reading, and so does my sister.', cn: '我喜欢阅读，我妹妹也是。' }
    },
    {
      pattern: 'one / ones / do so / so',
      example: { en: 'This red bag is mine, and the blue one is yours.', cn: '这个红包是我的，那个蓝色的是你的。' }
    }
  ],
  '26': [
    {
      pattern: '第一步找主语和谓语',
      example: { en: 'The report is being reviewed.', cn: '先抓主语 The report 和谓语 is being reviewed。' }
    },
    {
      pattern: '第二步划出从句边界',
      example: { en: 'The report that was submitted yesterday is being reviewed by the committee.', cn: '先划出 that was submitted yesterday 这一层从句。' }
    },
    {
      pattern: '第三步识别非谓语',
      example: { en: 'Students hoping to improve quickly should first master the sentence core.', cn: 'hoping to improve quickly 是修饰 Students 的非谓语结构。' }
    },
    {
      pattern: '第四步回填介词短语和修饰语',
      example: { en: 'The teacher gave us a useful example before the class started.', cn: '最后再补回 a useful 和 before the class started 这些补充层。' }
    }
  ]
};

function cloneExample(example) {
  if (!example) {
    return null;
  }
  return {
    en: example.en || '',
    cn: example.cn || ''
  };
}

function buildPatternExamples(chapter) {
  const overridePairs = PATTERN_EXAMPLE_OVERRIDES[chapter.no];
  if (overridePairs && overridePairs.length) {
    return overridePairs.map((item) => ({
      pattern: item.pattern,
      example: cloneExample(item.example)
    }));
  }

  const patterns = chapter.patterns || [];
  const examples = chapter.examples || [];
  return patterns.map((pattern, index) => ({
    pattern,
    example: cloneExample(examples[index] || examples[examples.length - 1] || null)
  }));
}

const GUIDE_SERIES_BASE = [
  {
    id: 'book-1',
    volume: '第 1 册',
    level: '入门基础',
    title: '先把最常见的简单句读顺',
    subtitle: '这一册的目标不是“学很多”，而是让最基本的句子不再读得磕绊。',
    audience: '适合刚开始补语法、基础比较薄弱、经常连简单句都读不稳的人',
    preview: '重点先放在 be 动词、代词、冠词、一般现在时、一般过去时、基本疑问句。',
    example: 'She is in the classroom, and she is reading a new book.',
    translation: '她在教室里，正在读一本新书。',
    chapters: [
      { no: '01', title: '句子最小骨架', desc: '主语、谓语、最基本的陈述句。' },
      { no: '02', title: 'be 动词与人称代词', desc: 'I am / she is / they are 这类最基础搭配。' },
      { no: '03', title: '冠词、名词与限定词', desc: 'a、an、the 以及 this、that、some、any。' },
      { no: '04', title: '一般现在时', desc: '习惯、事实、频率表达。' },
      { no: '05', title: '一般过去时', desc: '过去发生的动作与时间状语。' },
      { no: '06', title: '疑问句与否定句入门', desc: 'do / does / did 与 be 动词提问。' }
    ],
    learnings: [
      '先学会把句子拆成“谁 + 是什么 / 做什么”。',
      '把代词、冠词和最基础的时态用顺，降低阅读阻力。',
      '读到简单句时不再每个单词都停顿，而是能整体看懂。'
    ],
    pitfalls: [
      '第三人称单数和动词变化总是混。',
      'a / an / the 靠感觉乱用。',
      '疑问句一变语序就找不到主语和谓语。'
    ],
    checkpoint: '学完这一册后，应该能稳定读懂并写出最常见的基础句。'
  },
  {
    id: 'book-2',
    volume: '第 2 册',
    level: '基础句法',
    title: '把句子主干和常用扩展结构学扎实',
    subtitle: '这一册开始真正建立“句法意识”，也就是看到句子会先找骨架。',
    audience: '适合已经能读简单句，但一遇到稍长一点就容易散掉的人',
    preview: '重点进入五大基本句型、将来时、情态动词、比较结构、介词短语和基础被动语态。',
    example: 'The teacher gave us a useful example before the class started.',
    translation: '老师在上课前给了我们一个很有用的例子。',
    chapters: [
      { no: '07', title: '五大基本句型', desc: '主谓、主谓宾、主系表、双宾、宾补。' },
      { no: '08', title: '一般将来时', desc: 'will、be going to 与计划、预测表达。' },
      { no: '09', title: '情态动词基础', desc: 'can、must、should、may 的核心用法。' },
      { no: '10', title: '时间、地点、方式状语', desc: '介词短语和副词怎样补充主干。' },
      { no: '11', title: '比较级与最高级', desc: 'more / -er / the most 等比较表达。' },
      { no: '12', title: '被动语态入门', desc: '先学最常见的 is done / was done。' }
    ],
    learnings: [
      '开始形成“先主干、后补充”的阅读顺序。',
      '能区分宾语、表语、宾补，不会一长就糊。',
      '理解时间地点状语只是补充层，不要和主干抢。'
    ],
    pitfalls: [
      '把表语看成宾语，把宾补看成第二个宾语。',
      '只看到介词短语很多，就误以为句子很难。',
      '比较结构里忽略真正的比较对象。'
    ],
    checkpoint: '学完这一册后，看到中等长度句子时应该能先抓主干，再补细节。'
  },
  {
    id: 'book-3',
    volume: '第 3 册',
    level: '进阶结构',
    title: '系统进入从句、非谓语和复杂时态',
    subtitle: '这一册是从“看懂一般句子”走向“能处理复杂句子”的关键阶段。',
    audience: '适合基础句型已经比较稳，准备正式攻克阅读与写作复杂句的人',
    preview: '重点放在完成时、进行时、被动系统、非谓语、条件句和三大从句。',
    example: 'The student who had been waiting outside said that he wanted to ask a question.',
    translation: '一直在外面等着的那位学生说他想问一个问题。',
    chapters: [
      { no: '13', title: '现在完成时与过去完成时', desc: '动作和时间关系不再只靠 yesterday / now。' },
      { no: '14', title: '进行时与完成进行时', desc: '过程感、持续感和时间跨度。' },
      { no: '15', title: '被动语态系统化', desc: '不同时态下的被动形式和使用场景。' },
      { no: '16', title: '不定式与动名词', desc: 'to do、doing 在句中到底充当什么。' },
      { no: '17', title: '分词与分词短语', desc: '现在分词、过去分词如何修饰名词或整句。' },
      { no: '18', title: '条件句与虚拟语气', desc: '真实条件、假设条件和 if 的时态搭配。' },
      { no: '19', title: '名词性从句', desc: 'that / whether / what / how 这类从句整体当成一个成分。' },
      { no: '20', title: '定语从句与状语从句', desc: '从句到底在修饰谁、补充什么。' }
    ],
    learnings: [
      '正式建立多层句子结构的阅读能力。',
      '学会识别从句边界和非谓语边界，不再把长句读成一团。',
      '开始理解英语里时间关系、逻辑关系和压缩表达。'
    ],
    pitfalls: [
      '看到 who / which / that 就立刻卡死，主句主干丢失。',
      '分词和谓语混淆，to do 和 doing 只背形式不看功能。',
      '完成时只会套公式，不理解动作和时间的关系。'
    ],
    checkpoint: '学完这一册后，应该能比较稳定地拆开阅读理解中的多数复杂句。'
  },
  {
    id: 'book-4',
    volume: '第 4 册',
    level: '长难句提高',
    title: '专门训练阅读中的变形句和长难句',
    subtitle: '最后这一册才处理真正的难点，让前面三册打下的基础发挥作用。',
    audience: '适合考研、四六级、雅思、托福或需要系统提升阅读能力的人',
    preview: '重点进入强调、倒装、省略、平行结构、连接逻辑和长难句拆解方法。',
    example: 'Not only did the committee reject the proposal, but it also suggested that the plan be revised immediately.',
    translation: '委员会不仅否决了这项提案，还建议立刻修改这个方案。',
    chapters: [
      { no: '21', title: '强调句、倒装与否定前置', desc: '形式一变，怎样快速还原主干。' },
      { no: '22', title: '虚拟语气深化', desc: 'suggest、demand、wish 等高频考点。' },
      { no: '23', title: '省略与替代', desc: '避免看到省略句就失去结构感。' },
      { no: '24', title: '并列、平行与逻辑连接', desc: 'but、while、rather than、not only...but also...。' },
      { no: '25', title: '标点与插入语', desc: '逗号、破折号、括号、插入语如何切层。' },
      { no: '26', title: '长难句拆解方法', desc: '先主干、再从句、再非谓语、最后修饰层。' }
    ],
    learnings: [
      '学会面对阅读长句时先切层，不被表面长度吓住。',
      '把前面学过的时态、从句、非谓语真正串起来。',
      '形成接近实体教材后半部分的综合阅读能力训练。'
    ],
    pitfalls: [
      '还没找到主干，就被倒装、插入语和连接词带偏。',
      '明明每个点都学过，但放到一起就不会拆。',
      '过早学长难句技巧，反而掩盖了前面基础不稳的问题。'
    ],
    checkpoint: '学完这一册后，语法模块就能真正承担“长难句读懂”和“阅读理解辅助”的作用。'
  }
];

const GUIDE_SERIES = GUIDE_SERIES_BASE.map((series) => Object.assign({}, series, {
  chapters: (series.chapters || []).map((chapter) => {
    const mergedChapter = Object.assign({}, chapter, CHAPTER_DETAILS[chapter.no] || {});
    return Object.assign({}, mergedChapter, {
      patternExamples: buildPatternExamples(mergedChapter)
    });
  })
}));

function getGuideSeriesById(id) {
  return GUIDE_SERIES.find((item) => item.id === id) || null;
}

function getGuideSeriesSummaries() {
  return GUIDE_SERIES.map((item) => ({
    id: item.id,
    volume: item.volume,
    level: item.level,
    title: item.title,
    subtitle: item.subtitle,
    audience: item.audience,
    preview: item.preview,
    example: item.example,
    translation: item.translation,
    chapterCount: (item.chapters || []).length
  }));
}

module.exports = {
  BOOK_SOURCES,
  GUIDE_SERIES,
  LEARNING_PATHS,
  getGuideSeriesById,
  getGuideSeriesSummaries
};
