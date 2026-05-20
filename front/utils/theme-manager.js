const store = require('../store/app-store');
const {
  CUSTOM_THEME_ID,
  DEFAULT_CUSTOM_THEME,
  HUE_PRESETS,
  buildCustomTheme,
  buildFontSizeTokens,
  hexToRgba,
  normalizeCustomTheme
} = require('./custom-theme');

const DEFAULT_THEME_ID = 'busuu_ocean';

const THEMES = [
  {
    id: 'duo_forest',
    name: '绿林闯关',
    source: 'Duolingo',
    tone: '活力打卡',
    description: '高饱和绿配亮黄，更像游戏化连胜学习。',
    swatches: ['#58cc02', '#89e219', '#ffd84d', '#f6fff0'],
    pageStart: '#eefbe3',
    pageMid: '#f7ffe9',
    pageEnd: '#f6fbf2',
    heroStart: '#58cc02',
    heroEnd: '#2f9e44',
    cardBg: '#ffffff',
    cardBorder: '#d7efc6',
    textPrimary: '#163300',
    textSecondary: '#4b6b32',
    accent: '#58cc02',
    primaryStart: '#58cc02',
    primaryEnd: '#89e219',
    secondaryBg: '#edf9df',
    secondaryText: '#2f7f1e',
    ghostBg: '#ffffff',
    ghostText: '#356b24',
    chipBg: '#ebf8dc',
    chipText: '#2e7d20',
    segmentedBg: '#ecf8df',
    segmentedText: '#538237',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#58cc02',
    navBg: 'rgba(244, 252, 236, 0.94)',
    navText: '#234613',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#6a8357',
    tabActiveText: '#58cc02',
    tabIconBg: '#eef8e4',
    tabActiveBg: '#daf3bc',
    cardShadow: 'rgba(88, 204, 2, 0.12)',
    tabShadow: 'rgba(58, 131, 30, 0.14)'
  },
  {
    id: 'babbel_sunrise',
    name: '晨光暖橙',
    source: 'Babbel',
    tone: '教练陪练',
    description: '暖橙和奶油白更像耐心引导式课程。',
    swatches: ['#ff7a00', '#ffb347', '#ffe0bd', '#fff7ef'],
    pageStart: '#fff0e2',
    pageMid: '#fff7ee',
    pageEnd: '#fffaf6',
    heroStart: '#ff7a00',
    heroEnd: '#ff9b42',
    cardBg: '#ffffff',
    cardBorder: '#ffd9bb',
    textPrimary: '#5a2500',
    textSecondary: '#8b5b34',
    accent: '#ff7a00',
    primaryStart: '#ff7a00',
    primaryEnd: '#ffb347',
    secondaryBg: '#fff1e3',
    secondaryText: '#c15d00',
    ghostBg: '#ffffff',
    ghostText: '#7a4a21',
    chipBg: '#fff0e1',
    chipText: '#c75b00',
    segmentedBg: '#fff0e2',
    segmentedText: '#8a5d33',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#ff7a00',
    navBg: 'rgba(255, 245, 236, 0.94)',
    navText: '#5d2a05',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#8d6a4c',
    tabActiveText: '#ff7a00',
    tabIconBg: '#fff2e6',
    tabActiveBg: '#ffe0bf',
    cardShadow: 'rgba(255, 122, 0, 0.12)',
    tabShadow: 'rgba(193, 93, 0, 0.14)'
  },
  {
    id: 'busuu_ocean',
    name: '深海进阶',
    source: 'Busuu',
    tone: '沉稳蓝阶',
    description: '深蓝到天青的层次，适合系统化学习页面。',
    swatches: ['#0d6efd', '#3fa9f5', '#8dd7ff', '#eef7ff'],
    pageStart: '#eaf4ff',
    pageMid: '#f3f9ff',
    pageEnd: '#f7fbff',
    heroStart: '#0d6efd',
    heroEnd: '#144fcf',
    cardBg: '#ffffff',
    cardBorder: '#d5e5ff',
    textPrimary: '#0f2748',
    textSecondary: '#55718f',
    accent: '#0d6efd',
    primaryStart: '#0d6efd',
    primaryEnd: '#3fa9f5',
    secondaryBg: '#e9f3ff',
    secondaryText: '#0e60d8',
    ghostBg: '#ffffff',
    ghostText: '#47647f',
    chipBg: '#e8f3ff',
    chipText: '#0f67e0',
    segmentedBg: '#eaf4ff',
    segmentedText: '#5a7391',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#0d6efd',
    navBg: 'rgba(239, 247, 255, 0.94)',
    navText: '#143355',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#6d8197',
    tabActiveText: '#0d6efd',
    tabIconBg: '#eef4fb',
    tabActiveBg: '#d9ebff',
    cardShadow: 'rgba(13, 110, 253, 0.12)',
    tabShadow: 'rgba(13, 110, 253, 0.14)'
  },
  {
    id: 'memrise_neon',
    name: '夜光记忆',
    source: 'Memrise',
    tone: '霓虹记忆',
    description: '深靛背景里带电光感，适合强调沉浸式记忆。',
    swatches: ['#2d1b69', '#00d1ff', '#7cf29a', '#eff7ff'],
    pageStart: '#edf0ff',
    pageMid: '#f5f7ff',
    pageEnd: '#f8fbff',
    heroStart: '#2d1b69',
    heroEnd: '#00a8cc',
    cardBg: '#ffffff',
    cardBorder: '#dbe0ff',
    textPrimary: '#1a2145',
    textSecondary: '#586089',
    accent: '#00a8cc',
    primaryStart: '#2d1b69',
    primaryEnd: '#00d1ff',
    secondaryBg: '#ebf8ff',
    secondaryText: '#0c7ea0',
    ghostBg: '#ffffff',
    ghostText: '#4f567b',
    chipBg: '#ecf7ff',
    chipText: '#0678a2',
    segmentedBg: '#eef2ff',
    segmentedText: '#636b94',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#2d1b69',
    navBg: 'rgba(241, 244, 255, 0.94)',
    navText: '#20284d',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#6b7398',
    tabActiveText: '#2d1b69',
    tabIconBg: '#eef1ff',
    tabActiveBg: '#dfe6ff',
    cardShadow: 'rgba(45, 27, 105, 0.14)',
    tabShadow: 'rgba(45, 27, 105, 0.16)'
  },
  {
    id: 'drops_berry',
    name: '紫莓词块',
    source: 'Drops',
    tone: '方块高能',
    description: '紫粉撞色很适合词块、标签和轻量练习。',
    swatches: ['#6f2cff', '#b14cff', '#ff7acc', '#fff3ff'],
    pageStart: '#f5ecff',
    pageMid: '#fbf5ff',
    pageEnd: '#fffaff',
    heroStart: '#6f2cff',
    heroEnd: '#b14cff',
    cardBg: '#ffffff',
    cardBorder: '#ead7ff',
    textPrimary: '#35135c',
    textSecondary: '#70518d',
    accent: '#7c3aed',
    primaryStart: '#6f2cff',
    primaryEnd: '#c05cff',
    secondaryBg: '#f4ecff',
    secondaryText: '#7b35ee',
    ghostBg: '#ffffff',
    ghostText: '#654887',
    chipBg: '#f5edff',
    chipText: '#7f39f1',
    segmentedBg: '#f3ebff',
    segmentedText: '#7a5d97',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#6f2cff',
    navBg: 'rgba(248, 241, 255, 0.94)',
    navText: '#401b68',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#7b6a92',
    tabActiveText: '#7c3aed',
    tabIconBg: '#f3edff',
    tabActiveBg: '#e7d9ff',
    cardShadow: 'rgba(111, 44, 255, 0.13)',
    tabShadow: 'rgba(124, 58, 237, 0.16)'
  },
  {
    id: 'mondly_coral',
    name: '珊瑚轨道',
    source: 'Mondly',
    tone: '全球旅行',
    description: '珊瑚红配天蓝，像轻旅行和口语场景卡。',
    swatches: ['#ff6f61', '#ff9770', '#4cc9f0', '#fff6f4'],
    pageStart: '#fff0ec',
    pageMid: '#fff7f4',
    pageEnd: '#fbfdff',
    heroStart: '#ff6f61',
    heroEnd: '#ff9770',
    cardBg: '#ffffff',
    cardBorder: '#ffd7d0',
    textPrimary: '#5a231d',
    textSecondary: '#91615b',
    accent: '#ff6f61',
    primaryStart: '#ff6f61',
    primaryEnd: '#ff9770',
    secondaryBg: '#fff0ec',
    secondaryText: '#db5f53',
    ghostBg: '#ffffff',
    ghostText: '#82615c',
    chipBg: '#ffefeb',
    chipText: '#d85d50',
    segmentedBg: '#fff1ed',
    segmentedText: '#926963',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#ff6f61',
    navBg: 'rgba(255, 245, 241, 0.94)',
    navText: '#58261f',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#8f716e',
    tabActiveText: '#ff6f61',
    tabIconBg: '#fff1ee',
    tabActiveBg: '#ffd8d0',
    cardShadow: 'rgba(255, 111, 97, 0.12)',
    tabShadow: 'rgba(220, 95, 83, 0.15)'
  },
  {
    id: 'promova_blush',
    name: '柔桃会话',
    source: 'Promova',
    tone: '轻柔陪伴',
    description: '柔和桃粉更像陪伴式口语和自我表达练习。',
    swatches: ['#ff8fab', '#ffc2d1', '#ffe5ec', '#fff8fb'],
    pageStart: '#fff0f4',
    pageMid: '#fff7f9',
    pageEnd: '#fffafb',
    heroStart: '#ff8fab',
    heroEnd: '#ffb3c6',
    cardBg: '#ffffff',
    cardBorder: '#ffdbe4',
    textPrimary: '#5d2434',
    textSecondary: '#8d6571',
    accent: '#ff6b93',
    primaryStart: '#ff8fab',
    primaryEnd: '#ffb3c6',
    secondaryBg: '#fff1f5',
    secondaryText: '#db5f81',
    ghostBg: '#ffffff',
    ghostText: '#7f5e68',
    chipBg: '#fff0f4',
    chipText: '#d95a80',
    segmentedBg: '#fff1f5',
    segmentedText: '#946b77',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#ff6b93',
    navBg: 'rgba(255, 245, 248, 0.94)',
    navText: '#5a2736',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#8f7179',
    tabActiveText: '#ff6b93',
    tabIconBg: '#fff2f5',
    tabActiveBg: '#ffdbe5',
    cardShadow: 'rgba(255, 107, 147, 0.12)',
    tabShadow: 'rgba(219, 95, 129, 0.14)'
  },
  {
    id: 'elsa_mint',
    name: '发音薄荷',
    source: 'ELSA Speak',
    tone: '清透纠音',
    description: '冷静薄荷绿更适合发音、波形和口腔反馈类体验。',
    swatches: ['#00bfa6', '#4de2c5', '#b6fff1', '#f2fffb'],
    pageStart: '#e9fffa',
    pageMid: '#f4fffc',
    pageEnd: '#f9fffd',
    heroStart: '#00bfa6',
    heroEnd: '#0f8f83',
    cardBg: '#ffffff',
    cardBorder: '#c8f4eb',
    textPrimary: '#133f3b',
    textSecondary: '#5b807b',
    accent: '#00bfa6',
    primaryStart: '#00bfa6',
    primaryEnd: '#4de2c5',
    secondaryBg: '#e9fbf7',
    secondaryText: '#0f8d7c',
    ghostBg: '#ffffff',
    ghostText: '#547872',
    chipBg: '#e8fbf7',
    chipText: '#0a8c7b',
    segmentedBg: '#eafbf7',
    segmentedText: '#5f807a',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#00bfa6',
    navBg: 'rgba(241, 255, 251, 0.94)',
    navText: '#18423e',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#6e8784',
    tabActiveText: '#00bfa6',
    tabIconBg: '#eef9f6',
    tabActiveBg: '#d0f5ee',
    cardShadow: 'rgba(0, 191, 166, 0.12)',
    tabShadow: 'rgba(15, 141, 124, 0.14)'
  },
  {
    id: 'hellotalk_breeze',
    name: '海盐交流',
    source: 'HelloTalk',
    tone: '社交轻聊',
    description: '聊天气质更明显，适合例句互动和问答场景。',
    swatches: ['#2ec4b6', '#4dabf7', '#d9f7fa', '#f6feff'],
    pageStart: '#e8fbfd',
    pageMid: '#f2fcff',
    pageEnd: '#f8feff',
    heroStart: '#2ec4b6',
    heroEnd: '#4dabf7',
    cardBg: '#ffffff',
    cardBorder: '#cfeef3',
    textPrimary: '#133841',
    textSecondary: '#5d7d84',
    accent: '#2ea7d0',
    primaryStart: '#2ec4b6',
    primaryEnd: '#4dabf7',
    secondaryBg: '#eaf8fd',
    secondaryText: '#288cb0',
    ghostBg: '#ffffff',
    ghostText: '#53747a',
    chipBg: '#eaf8fd',
    chipText: '#278db1',
    segmentedBg: '#ebf8fd',
    segmentedText: '#648087',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#2ea7d0',
    navBg: 'rgba(241, 253, 255, 0.94)',
    navText: '#1b4148',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#6d888d',
    tabActiveText: '#2ea7d0',
    tabIconBg: '#eef7fb',
    tabActiveBg: '#d7eef9',
    cardShadow: 'rgba(46, 167, 208, 0.12)',
    tabShadow: 'rgba(40, 140, 176, 0.14)'
  },
  {
    id: 'grammar_notebook',
    name: '语法笔记',
    source: '实体语法书',
    tone: '纸面分层',
    description: '像手边做批注的语法讲义，适合总览与结构图。',
    swatches: ['#f4e8c1', '#d8c49a', '#5c4b2f', '#fffdf6'],
    pageStart: '#faf4e6',
    pageMid: '#fffaf0',
    pageEnd: '#fffdf8',
    heroStart: '#c8a96b',
    heroEnd: '#8c6a3b',
    cardBg: '#fffdf8',
    cardBorder: '#eadfbe',
    textPrimary: '#43311c',
    textSecondary: '#7d6a50',
    accent: '#8c6a3b',
    primaryStart: '#b79259',
    primaryEnd: '#8c6a3b',
    secondaryBg: '#f9f1de',
    secondaryText: '#8c6a3b',
    ghostBg: '#fffdf8',
    ghostText: '#6f5a3d',
    chipBg: '#f9f1de',
    chipText: '#8b6838',
    segmentedBg: '#f8f0de',
    segmentedText: '#7f6a4a',
    segmentedActiveBg: '#fffdf8',
    segmentedActiveText: '#8c6a3b',
    navBg: 'rgba(255, 251, 242, 0.94)',
    navText: '#49361f',
    tabBarBg: 'rgba(255, 253, 248, 0.98)',
    tabText: '#8a7760',
    tabActiveText: '#8c6a3b',
    tabIconBg: '#f7f1e5',
    tabActiveBg: '#eddfbf',
    cardShadow: 'rgba(140, 106, 59, 0.1)',
    tabShadow: 'rgba(111, 90, 61, 0.12)'
  },
  {
    id: 'library_sepia',
    name: '词典棕页',
    source: '纸质词典',
    tone: '经典查阅',
    description: '偏复古的牛津词典感，稳重且利于长时间阅读。',
    swatches: ['#6b4f3a', '#a67c52', '#e6d2b5', '#fffaf4'],
    pageStart: '#f6eee4',
    pageMid: '#fbf6ef',
    pageEnd: '#fffaf5',
    heroStart: '#6b4f3a',
    heroEnd: '#a67c52',
    cardBg: '#fffdf9',
    cardBorder: '#e6d6c4',
    textPrimary: '#3b291d',
    textSecondary: '#7b6858',
    accent: '#8a6242',
    primaryStart: '#8a6242',
    primaryEnd: '#a67c52',
    secondaryBg: '#f6ede2',
    secondaryText: '#835d3f',
    ghostBg: '#fffdf9',
    ghostText: '#695444',
    chipBg: '#f5ede2',
    chipText: '#835c3e',
    segmentedBg: '#f6ede2',
    segmentedText: '#7a6958',
    segmentedActiveBg: '#fffdf9',
    segmentedActiveText: '#8a6242',
    navBg: 'rgba(252, 248, 241, 0.94)',
    navText: '#412e21',
    tabBarBg: 'rgba(255, 253, 249, 0.98)',
    tabText: '#877667',
    tabActiveText: '#8a6242',
    tabIconBg: '#f4ede4',
    tabActiveBg: '#e7d8c6',
    cardShadow: 'rgba(106, 79, 58, 0.1)',
    tabShadow: 'rgba(106, 79, 58, 0.12)'
  },
  {
    id: 'exam_crimson',
    name: '冲刺绯红',
    source: '备考应用',
    tone: '目标推进',
    description: '更像考试冲刺版界面，强调完成度和时间紧迫感。',
    swatches: ['#d7263d', '#f46036', '#ffd3c8', '#fff7f5'],
    pageStart: '#fff0ee',
    pageMid: '#fff7f5',
    pageEnd: '#fffafb',
    heroStart: '#d7263d',
    heroEnd: '#f46036',
    cardBg: '#ffffff',
    cardBorder: '#ffd5cf',
    textPrimary: '#571d26',
    textSecondary: '#8c6368',
    accent: '#d7263d',
    primaryStart: '#d7263d',
    primaryEnd: '#f46036',
    secondaryBg: '#fff0ee',
    secondaryText: '#c12739',
    ghostBg: '#ffffff',
    ghostText: '#7b5b60',
    chipBg: '#fff0ee',
    chipText: '#c12739',
    segmentedBg: '#fff1ef',
    segmentedText: '#936c71',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#d7263d',
    navBg: 'rgba(255, 245, 243, 0.94)',
    navText: '#5b232b',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#91757a',
    tabActiveText: '#d7263d',
    tabIconBg: '#fff2f0',
    tabActiveBg: '#ffd9d4',
    cardShadow: 'rgba(215, 38, 61, 0.12)',
    tabShadow: 'rgba(193, 39, 57, 0.14)'
  },
  {
    id: 'midnight_reader',
    name: '深夜长句',
    source: '长难句精读',
    tone: '静夜专注',
    description: '夜读蓝更适合语法分析、结构走读和沉浸阅读。',
    swatches: ['#1d3557', '#457b9d', '#a8dadc', '#f2f7fb'],
    pageStart: '#eaf1f8',
    pageMid: '#f2f7fb',
    pageEnd: '#f8fbff',
    heroStart: '#1d3557',
    heroEnd: '#457b9d',
    cardBg: '#ffffff',
    cardBorder: '#d7e3ef',
    textPrimary: '#1c2b3b',
    textSecondary: '#5f7387',
    accent: '#457b9d',
    primaryStart: '#1d3557',
    primaryEnd: '#457b9d',
    secondaryBg: '#ebf2f8',
    secondaryText: '#3b6e90',
    ghostBg: '#ffffff',
    ghostText: '#586b7e',
    chipBg: '#ebf2f8',
    chipText: '#3b6e90',
    segmentedBg: '#ebf2f8',
    segmentedText: '#667a8e',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#1d3557',
    navBg: 'rgba(240, 245, 250, 0.94)',
    navText: '#233549',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#758596',
    tabActiveText: '#1d3557',
    tabIconBg: '#eef3f8',
    tabActiveBg: '#dae7f2',
    cardShadow: 'rgba(29, 53, 87, 0.12)',
    tabShadow: 'rgba(29, 53, 87, 0.14)'
  },
  {
    id: 'aurora_lab',
    name: '极光智学',
    source: 'AI 学习助手',
    tone: '未来感',
    description: '蓝青与淡紫的极光层次，更像智能分析和实时反馈。',
    swatches: ['#00c2ff', '#7b61ff', '#8bf3ff', '#f5f5ff'],
    pageStart: '#ecf8ff',
    pageMid: '#f4f7ff',
    pageEnd: '#fbfcff',
    heroStart: '#00a8cc',
    heroEnd: '#7b61ff',
    cardBg: '#ffffff',
    cardBorder: '#d9e6ff',
    textPrimary: '#1b2948',
    textSecondary: '#647095',
    accent: '#5c6cff',
    primaryStart: '#00a8cc',
    primaryEnd: '#7b61ff',
    secondaryBg: '#eef2ff',
    secondaryText: '#5461f4',
    ghostBg: '#ffffff',
    ghostText: '#5d678b',
    chipBg: '#edf1ff',
    chipText: '#5561f4',
    segmentedBg: '#edf1ff',
    segmentedText: '#6b7396',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#5c6cff',
    navBg: 'rgba(242, 247, 255, 0.94)',
    navText: '#223052',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#76819c',
    tabActiveText: '#5c6cff',
    tabIconBg: '#eef3ff',
    tabActiveBg: '#dde4ff',
    cardShadow: 'rgba(92, 108, 255, 0.12)',
    tabShadow: 'rgba(92, 108, 255, 0.14)'
  },
  {
    id: 'forest_review',
    name: '青苔复习',
    source: '间隔复习卡片',
    tone: '平静巩固',
    description: '低饱和森林系，适合复习、错词回看和长期坚持。',
    swatches: ['#5b8c5a', '#9bc995', '#dcefd7', '#f7fcf6'],
    pageStart: '#edf6ea',
    pageMid: '#f6fbf4',
    pageEnd: '#fbfefb',
    heroStart: '#5b8c5a',
    heroEnd: '#7ab874',
    cardBg: '#ffffff',
    cardBorder: '#d8e9d3',
    textPrimary: '#243c24',
    textSecondary: '#637b63',
    accent: '#5b8c5a',
    primaryStart: '#5b8c5a',
    primaryEnd: '#7ab874',
    secondaryBg: '#edf7ea',
    secondaryText: '#4a7a49',
    ghostBg: '#ffffff',
    ghostText: '#5d735d',
    chipBg: '#edf7ea',
    chipText: '#4b7a4a',
    segmentedBg: '#edf7ea',
    segmentedText: '#6a826a',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#5b8c5a',
    navBg: 'rgba(245, 251, 243, 0.94)',
    navText: '#2e472e',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#788c78',
    tabActiveText: '#5b8c5a',
    tabIconBg: '#eef6eb',
    tabActiveBg: '#ddebda',
    cardShadow: 'rgba(91, 140, 90, 0.12)',
    tabShadow: 'rgba(74, 122, 73, 0.14)'
  },
  {
    id: 'ink_sky',
    name: '墨蓝学术',
    source: '学术阅读',
    tone: '理性清晰',
    description: '比深夜模式更清爽，适合大量解释文本和统计页面。',
    swatches: ['#274c77', '#6096ba', '#a3cef1', '#f1f7fd'],
    pageStart: '#ebf3fb',
    pageMid: '#f4f8fc',
    pageEnd: '#f8fbfd',
    heroStart: '#274c77',
    heroEnd: '#6096ba',
    cardBg: '#ffffff',
    cardBorder: '#d7e4ef',
    textPrimary: '#1f2d3a',
    textSecondary: '#65798d',
    accent: '#3f78a9',
    primaryStart: '#274c77',
    primaryEnd: '#6096ba',
    secondaryBg: '#ebf3fb',
    secondaryText: '#3f78a9',
    ghostBg: '#ffffff',
    ghostText: '#607385',
    chipBg: '#ebf3fb',
    chipText: '#3f78a9',
    segmentedBg: '#ebf3fb',
    segmentedText: '#6a7d90',
    segmentedActiveBg: '#ffffff',
    segmentedActiveText: '#274c77',
    navBg: 'rgba(241, 246, 251, 0.94)',
    navText: '#26384b',
    tabBarBg: 'rgba(255, 255, 255, 0.98)',
    tabText: '#778899',
    tabActiveText: '#274c77',
    tabIconBg: '#edf3f8',
    tabActiveBg: '#dbe8f2',
    cardShadow: 'rgba(39, 76, 119, 0.12)',
    tabShadow: 'rgba(39, 76, 119, 0.14)'
  },
  {
    id: 'paper_dawn',
    name: '晨纸轻读',
    source: '轻学习应用',
    tone: '温柔清晨',
    description: '米白和雾蓝更柔和，适合晨读、背词和轻学习。',
    swatches: ['#f6bd60', '#84a59d', '#f7ede2', '#fffdf9'],
    pageStart: '#fff6ea',
    pageMid: '#fbfaf5',
    pageEnd: '#fffefb',
    heroStart: '#f6bd60',
    heroEnd: '#84a59d',
    cardBg: '#fffefb',
    cardBorder: '#efe4d1',
    textPrimary: '#4c3d2b',
    textSecondary: '#7c7367',
    accent: '#84a59d',
    primaryStart: '#f6bd60',
    primaryEnd: '#84a59d',
    secondaryBg: '#f9f2e4',
    secondaryText: '#7a9a92',
    ghostBg: '#fffefb',
    ghostText: '#70665a',
    chipBg: '#f9f2e4',
    chipText: '#7a9a92',
    segmentedBg: '#f9f2e6',
    segmentedText: '#84796a',
    segmentedActiveBg: '#fffefb',
    segmentedActiveText: '#84a59d',
    navBg: 'rgba(255, 252, 245, 0.94)',
    navText: '#514233',
    tabBarBg: 'rgba(255, 254, 251, 0.98)',
    tabText: '#8a8071',
    tabActiveText: '#84a59d',
    tabIconBg: '#f8f1e6',
    tabActiveBg: '#e6efe9',
    cardShadow: 'rgba(132, 165, 157, 0.11)',
    tabShadow: 'rgba(132, 165, 157, 0.13)'
  }
];

const THEME_EXPERIENCE_PROFILES = {
  playful: {
    themeFontClass: 'font-playful',
    themeMotionClass: 'motion-pop',
    grammarThemeClass: 'grammar-theme-playful',
    grammarCardHoverClass: 'hover-card-pop',
    grammarActionHoverClass: 'hover-action-bloom',
    fontBody: "'Trebuchet MS','Avenir Next','PingFang SC','Microsoft YaHei',sans-serif",
    fontDisplay: "'Trebuchet MS','Avenir Next','PingFang SC','Microsoft YaHei',sans-serif",
    fontLabel: '活力圆角体',
    interactionLabel: '弹跳卡片'
  },
  coach: {
    themeFontClass: 'font-coach',
    themeMotionClass: 'motion-glide',
    grammarThemeClass: 'grammar-theme-coach',
    grammarCardHoverClass: 'hover-card-slide',
    grammarActionHoverClass: 'hover-action-sweep',
    fontBody: "'Avenir Next','Segoe UI','PingFang SC','Microsoft YaHei',sans-serif",
    fontDisplay: "'Avenir Next','Trebuchet MS','PingFang SC','Microsoft YaHei',sans-serif",
    fontLabel: '教练无衬线',
    interactionLabel: '推进式反馈'
  },
  notebook: {
    themeFontClass: 'font-notebook',
    themeMotionClass: 'motion-sheet',
    grammarThemeClass: 'grammar-theme-notebook',
    grammarCardHoverClass: 'hover-card-sheet',
    grammarActionHoverClass: 'hover-action-underline',
    fontBody: "'Georgia','Times New Roman','Songti SC','STSong','Noto Serif CJK SC',serif",
    fontDisplay: "'Georgia','Times New Roman','Songti SC','STSong','Noto Serif CJK SC',serif",
    fontLabel: '书页衬线体',
    interactionLabel: '纸页翻阅'
  },
  editorial: {
    themeFontClass: 'font-editorial',
    themeMotionClass: 'motion-focus',
    grammarThemeClass: 'grammar-theme-editorial',
    grammarCardHoverClass: 'hover-card-focus',
    grammarActionHoverClass: 'hover-action-nudge',
    fontBody: "'Helvetica Neue','Gill Sans','PingFang SC','Microsoft YaHei',sans-serif",
    fontDisplay: "'Gill Sans','Avenir Next','PingFang SC','Microsoft YaHei',sans-serif",
    fontLabel: '杂志标题体',
    interactionLabel: '聚焦展开'
  }
};

const THEME_EXPERIENCE_MAP = {
  duo_forest: 'playful',
  drops_berry: 'playful',
  mondly_coral: 'playful',
  babbel_sunrise: 'coach',
  busuu_ocean: 'coach',
  promova_blush: 'coach',
  hellotalk_breeze: 'coach',
  forest_review: 'coach',
  paper_dawn: 'coach',
  grammar_notebook: 'notebook',
  library_sepia: 'notebook',
  exam_crimson: 'notebook',
  memrise_neon: 'editorial',
  elsa_mint: 'editorial',
  midnight_reader: 'editorial',
  aurora_lab: 'editorial',
  ink_sky: 'editorial'
};

function decorateTheme(theme) {
  const profileKey = THEME_EXPERIENCE_MAP[theme.id] || 'coach';
  return Object.assign({}, theme, THEME_EXPERIENCE_PROFILES[profileKey]);
}

const THEME_MAP = THEMES.reduce((map, theme) => {
  map[theme.id] = decorateTheme(theme);
  return map;
}, {});

function getThemeById(themeId) {
  return THEME_MAP[themeId] || THEME_MAP[DEFAULT_THEME_ID];
}

function getStoredCustomTheme() {
  const settings = store.getState().settings || {};
  return normalizeCustomTheme(settings.custom_theme || DEFAULT_CUSTOM_THEME);
}

function resolveTheme(themeId, customTheme) {
  if (themeId === CUSTOM_THEME_ID) {
    return buildCustomTheme(customTheme || getStoredCustomTheme());
  }
  return getThemeById(themeId);
}

function getCurrentThemeId() {
  const settings = store.getState().settings || {};
  if (settings.theme_id === CUSTOM_THEME_ID) {
    return CUSTOM_THEME_ID;
  }
  return getThemeById(settings.theme_id).id;
}

function buildThemeStyleFromTheme(theme) {
  const fontSizes = theme.fontSizes || buildFontSizeTokens(DEFAULT_CUSTOM_THEME.font_size_scale);
  return [
    `--theme-page-start:${theme.pageStart}`,
    `--theme-page-mid:${theme.pageMid}`,
    `--theme-page-end:${theme.pageEnd}`,
    `--theme-card-bg:${theme.cardBg}`,
    `--theme-card-border:${theme.cardBorder}`,
    `--theme-text-primary:${theme.textPrimary}`,
    `--theme-text-secondary:${theme.textSecondary}`,
    `--theme-accent:${theme.accent}`,
    `--theme-primary-start:${theme.primaryStart}`,
    `--theme-primary-end:${theme.primaryEnd}`,
    `--theme-secondary-bg:${theme.secondaryBg}`,
    `--theme-secondary-text:${theme.secondaryText}`,
    `--theme-ghost-bg:${theme.ghostBg}`,
    `--theme-ghost-text:${theme.ghostText}`,
    `--theme-chip-light-bg:${theme.chipBg}`,
    `--theme-chip-light-text:${theme.chipText}`,
    `--theme-segmented-bg:${theme.segmentedBg}`,
    `--theme-segmented-text:${theme.segmentedText}`,
    `--theme-segmented-active-bg:${theme.segmentedActiveBg}`,
    `--theme-segmented-active-text:${theme.segmentedActiveText}`,
    `--theme-nav-bg:${theme.navBg}`,
    `--theme-nav-text:${theme.navText}`,
    `--theme-nav-border:${theme.navBorder || 'transparent'}`,
    `--theme-nav-shadow:${theme.navShadow || 'none'}`,
    `--theme-hero-start:${theme.heroStart}`,
    `--theme-hero-end:${theme.heroEnd}`,
    `--theme-card-shadow:${theme.cardShadow}`,
    `--theme-divider:${theme.cardBorder}`,
    `--theme-page-glow-a:${hexToRgba(theme.primaryEnd, 0.18)}`,
    `--theme-page-glow-b:${hexToRgba(theme.primaryStart, 0.12)}`,
    `--theme-primary-shadow:${hexToRgba(theme.primaryStart, 0.22)}`,
    `--theme-secondary-shadow:${hexToRgba(theme.primaryStart, 0.06)}`,
    `--theme-tab-bar-bg:${theme.tabBarBg}`,
    `--theme-tab-text:${theme.tabText}`,
    `--theme-tab-active-text:${theme.tabActiveText}`,
    `--theme-tab-icon-bg:${theme.tabIconBg}`,
    `--theme-tab-active-bg:${theme.tabActiveBg}`,
    `--theme-tab-shadow:${theme.tabShadow}`,
    `--theme-font-body:${theme.fontBody}`,
    `--theme-font-display:${theme.fontDisplay}`,
    `--theme-font-size-base:${fontSizes.fontSizeBase}`,
    `--theme-font-size-title:${fontSizes.fontSizeTitle}`,
    `--theme-font-size-subtitle:${fontSizes.fontSizeSubtitle}`,
    `--theme-font-size-list-title:${fontSizes.fontSizeListTitle}`,
    `--theme-font-size-list-desc:${fontSizes.fontSizeListDesc}`,
    `--theme-font-size-button:${fontSizes.fontSizeButton}`,
    `--theme-font-size-metric:${fontSizes.fontSizeMetric}`,
    `--theme-font-size-word:${fontSizes.fontSizeWord}`,
    `--theme-font-size-hero:${fontSizes.fontSizeHero}`,
    `--theme-font-size-grammar-title:${fontSizes.fontSizeGrammarTitle}`,
    `--theme-font-size-grammar-desc:${fontSizes.fontSizeGrammarDesc}`
  ].join(';');
}

function buildThemePreview(theme) {
  const fontSizes = theme.fontSizes || buildFontSizeTokens(DEFAULT_CUSTOM_THEME.font_size_scale);

  return {
    id: theme.id,
    name: theme.name,
    source: theme.source,
    tone: theme.tone,
    description: theme.description,
    swatches: theme.swatches.slice(),
    fontLabel: theme.fontLabel,
    interactionLabel: theme.interactionLabel,
    accent: theme.accent,
    textPrimary: theme.textPrimary,
    textSecondary: theme.textSecondary,
    cardBg: theme.cardBg,
    cardBorder: theme.cardBorder,
    fontSizes,
    isCustom: theme.id === CUSTOM_THEME_ID,
    previewStyle: `background:linear-gradient(135deg, ${theme.heroStart} 0%, ${theme.heroEnd} 100%);color:#ffffff;`,
    buttonStyle: `background:${theme.secondaryBg};color:${theme.secondaryText};`,
    surfaceStyle: `background:${theme.cardBg};border:2rpx solid ${theme.cardBorder};color:${theme.textPrimary};`,
    metaStyle: `color:${theme.textSecondary};`,
    accentStyle: `color:${theme.accent};`
  };
}

function getThemeOptions() {
  return THEMES.map((theme) => buildThemePreview(getThemeById(theme.id)));
}

function getThemePreview(themeId, customTheme) {
  return buildThemePreview(resolveTheme(themeId || getCurrentThemeId(), customTheme));
}

function setCurrentTheme(themeId) {
  if (themeId === CUSTOM_THEME_ID) {
    const customSettings = Object.assign({}, store.getState().settings || {}, {
      theme_id: CUSTOM_THEME_ID
    });
    store.setSettings(customSettings);
    return CUSTOM_THEME_ID;
  }
  const resolvedTheme = getThemeById(themeId);
  const settings = Object.assign({}, store.getState().settings || {}, {
    theme_id: resolvedTheme.id
  });
  store.setSettings(settings);
  return resolvedTheme.id;
}

function setCustomTheme(customTheme) {
  const normalizedCustomTheme = normalizeCustomTheme(customTheme);
  const settings = Object.assign({}, store.getState().settings || {}, {
    theme_id: CUSTOM_THEME_ID,
    custom_theme: normalizedCustomTheme
  });
  store.setSettings(settings);
  return settings;
}

function getPageThemeData(themeId) {
  const resolvedTheme = resolveTheme(themeId || getCurrentThemeId());
  return {
    currentThemeId: resolvedTheme.id,
    pageThemeStyle: buildThemeStyleFromTheme(resolvedTheme),
    themePageClass: resolvedTheme.themePageClass || '',
    themeFontClass: resolvedTheme.themeFontClass,
    themeMotionClass: resolvedTheme.themeMotionClass,
    grammarThemeClass: resolvedTheme.grammarThemeClass,
    grammarCardHoverClass: resolvedTheme.grammarCardHoverClass,
    grammarActionHoverClass: resolvedTheme.grammarActionHoverClass
  };
}

function getTabBarThemeData(themeId) {
  const theme = resolveTheme(themeId || getCurrentThemeId());
  return {
    tabBarStyle: `background:${theme.tabBarBg};border:2rpx solid ${hexToRgba(theme.cardBorder, 0.82)};box-shadow:0 16rpx 44rpx ${theme.tabShadow};`,
    tabTextStyle: `color:${theme.tabText};`,
    tabActiveTextStyle: `color:${theme.tabActiveText};`,
    tabIconStyle: `background:${theme.tabIconBg};color:${theme.tabText};`,
    tabActiveIconStyle: `background:${theme.tabActiveBg};color:${theme.tabActiveText};`
    ,
    tabActiveSurfaceStyle: `background:linear-gradient(180deg, ${hexToRgba(theme.secondaryBg, 0.92)} 0%, ${hexToRgba(theme.cardBg, 0.82)} 100%);box-shadow:0 12rpx 28rpx ${theme.tabShadow}, inset 0 1rpx 0 rgba(255, 255, 255, 0.84);`
  };
}

function syncTabBar(page, themeId) {
  if (!page || typeof page.getTabBar !== 'function') {
    return;
  }
  const tabBar = page.getTabBar();
  if (!tabBar) {
    return;
  }
  const themeData = getTabBarThemeData(themeId);
  if (typeof tabBar.applyTheme === 'function') {
    tabBar.applyTheme(themeData);
    return;
  }
  if (typeof tabBar.setData === 'function') {
    tabBar.setData(themeData);
  }
}

function applyTheme(page, themeId) {
  if (!page || typeof page.setData !== 'function') {
    return;
  }
  const themeData = getPageThemeData(themeId);
  const currentData = page.data || {};
  const changedEntries = Object.keys(themeData).reduce((bucket, key) => {
    if (currentData[key] !== themeData[key]) {
      bucket[key] = themeData[key];
    }
    return bucket;
  }, {});
  if (Object.keys(changedEntries).length) {
    page.setData(changedEntries);
  }
  syncTabBar(page, themeData.currentThemeId);
}

function withThemePage(pageConfig) {
  const originalOnLoad = pageConfig.onLoad;
  const originalOnShow = pageConfig.onShow;
  const initialThemeData = getPageThemeData();

  return Object.assign({}, pageConfig, {
    data: Object.assign({}, pageConfig.data || {}, initialThemeData),
    onLoad(...args) {
      applyTheme(this);
      if (typeof originalOnLoad === 'function') {
        return originalOnLoad.apply(this, args);
      }
      return undefined;
    },
    onShow(...args) {
      applyTheme(this);
      if (typeof originalOnShow === 'function') {
        return originalOnShow.apply(this, args);
      }
      return undefined;
    }
  });
}

module.exports = {
  DEFAULT_THEME_ID,
  CUSTOM_THEME_ID,
  DEFAULT_CUSTOM_THEME,
  HUE_PRESETS,
  getCurrentThemeId,
  getPageThemeData,
  getTabBarThemeData,
  getThemeOptions,
  getThemePreview,
  normalizeCustomTheme,
  setCurrentTheme,
  setCustomTheme,
  applyTheme,
  syncTabBar,
  withThemePage
};
