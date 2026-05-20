export const CUSTOM_THEME_ID = 'custom_dynamic';
export const DEFAULT_THEME_ID = 'busuu_ocean';

export const DEFAULT_CUSTOM_THEME = {
  base_hue: 132,
  base_lightness: 50,
  gradient_enabled: true,
  gradient_shift: 18,
  gradient_depth: 12,
  font_hue: 224,
  font_lightness: 18,
  font_size_scale: 100,
};

export const HUE_PRESETS = [
  { id: 'forest', label: '森林绿', hue: 132, color: '#58cc02' },
  { id: 'sunrise', label: '晨光橙', hue: 28, color: '#ff7a00' },
  { id: 'ocean', label: '深海蓝', hue: 210, color: '#0d6efd' },
  { id: 'neon', label: '夜光青', hue: 188, color: '#00d1ff' },
  { id: 'berry', label: '莓果紫', hue: 282, color: '#7c3aed' },
  { id: 'coral', label: '珊瑚红', hue: 8, color: '#ff6f61' },
  { id: 'blush', label: '柔桃粉', hue: 340, color: '#ff8fab' },
  { id: 'mint', label: '薄荷青', hue: 168, color: '#00bfa6' },
];

const THEMES = [
  {
    id: 'duo_forest',
    name: '绿林闯关',
    source: 'Game Learn',
    tone: '活力打卡',
    description: '高饱和绿配亮黄，把学习做成一场持续通关。',
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
    cardShadow: 'rgba(88, 204, 2, 0.14)',
    tabShadow: 'rgba(58, 131, 30, 0.18)',
  },
  {
    id: 'babbel_sunrise',
    name: '晨光暖橙',
    source: 'Coach Learn',
    tone: '陪练推进',
    description: '暖橙与奶油白更像一个耐心但有节奏的学习教练。',
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
    cardShadow: 'rgba(255, 122, 0, 0.13)',
    tabShadow: 'rgba(193, 93, 0, 0.16)',
  },
  {
    id: 'busuu_ocean',
    name: '深海进阶',
    source: 'Structured Learn',
    tone: '系统推进',
    description: '深蓝到天青的层次，适合系统化学习与长期进度追踪。',
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
    cardShadow: 'rgba(13, 110, 253, 0.14)',
    tabShadow: 'rgba(13, 110, 253, 0.18)',
  },
  {
    id: 'memrise_neon',
    name: '夜光记忆',
    source: 'Immersive Learn',
    tone: '霓虹记忆',
    description: '深靛与电光蓝更适合强化记忆感和沉浸式学习氛围。',
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
    cardShadow: 'rgba(45, 27, 105, 0.16)',
    tabShadow: 'rgba(45, 27, 105, 0.18)',
  },
  {
    id: 'drops_berry',
    name: '紫莓词块',
    source: 'Chunk Learn',
    tone: '方块高能',
    description: '紫粉撞色适合词块、标签与轻量密集的练习体验。',
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
    cardShadow: 'rgba(111, 44, 255, 0.15)',
    tabShadow: 'rgba(124, 58, 237, 0.18)',
  },
  {
    id: 'mondly_coral',
    name: '珊瑚轨道',
    source: 'Travel Learn',
    tone: '轻旅行口语',
    description: '珊瑚红和天蓝的对比让口语、场景和任务推进更有画面感。',
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
    cardShadow: 'rgba(255, 111, 97, 0.14)',
    tabShadow: 'rgba(220, 95, 83, 0.18)',
  },
  {
    id: 'promova_blush',
    name: '柔桃会话',
    source: 'Conversation Learn',
    tone: '轻柔陪伴',
    description: '柔和桃粉更适合陪伴式口语、自我表达和轻压力学习。',
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
    cardShadow: 'rgba(255, 107, 147, 0.14)',
    tabShadow: 'rgba(219, 95, 129, 0.18)',
  },
  {
    id: 'aurora_lab',
    name: '极光智学',
    source: 'AI Lab',
    tone: '未来感',
    description: '蓝青与淡紫的极光层次，更适合 AI 分析、技能中心与复杂结果。',
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
    cardShadow: 'rgba(92, 108, 255, 0.14)',
    tabShadow: 'rgba(92, 108, 255, 0.18)',
  },
  {
    id: 'forest_review',
    name: '青苔复习',
    source: 'Review Flow',
    tone: '平静巩固',
    description: '低饱和森林系更适合复习、错词回看和长期坚持。',
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
    cardShadow: 'rgba(91, 140, 90, 0.14)',
    tabShadow: 'rgba(74, 122, 73, 0.18)',
  },
  {
    id: 'paper_dawn',
    name: '晨纸轻读',
    source: 'Light Study',
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
    cardShadow: 'rgba(132, 165, 157, 0.13)',
    tabShadow: 'rgba(132, 165, 157, 0.16)',
  },
];

const EXPERIENCE_PROFILES = {
  playful: {
    themeFontClass: 'font-playful',
    themeMotionClass: 'motion-pop',
    fontBody: '"Trebuchet MS","Avenir Next","PingFang SC","Microsoft YaHei",sans-serif',
    fontDisplay: '"Trebuchet MS","Avenir Next","PingFang SC","Microsoft YaHei",sans-serif',
    fontLabel: '活力圆角体',
    interactionLabel: '弹跳推进',
  },
  coach: {
    themeFontClass: 'font-coach',
    themeMotionClass: 'motion-glide',
    fontBody: '"Avenir Next","Segoe UI","PingFang SC","Microsoft YaHei",sans-serif',
    fontDisplay: '"Avenir Next","Trebuchet MS","PingFang SC","Microsoft YaHei",sans-serif',
    fontLabel: '教练无衬线',
    interactionLabel: '推进反馈',
  },
  editorial: {
    themeFontClass: 'font-editorial',
    themeMotionClass: 'motion-focus',
    fontBody: '"Helvetica Neue","Gill Sans","PingFang SC","Microsoft YaHei",sans-serif',
    fontDisplay: '"Gill Sans","Avenir Next","PingFang SC","Microsoft YaHei",sans-serif',
    fontLabel: '杂志标题体',
    interactionLabel: '聚焦展开',
  },
};

const EXPERIENCE_MAP = {
  duo_forest: 'playful',
  drops_berry: 'playful',
  mondly_coral: 'playful',
  babbel_sunrise: 'coach',
  busuu_ocean: 'coach',
  promova_blush: 'coach',
  forest_review: 'coach',
  paper_dawn: 'coach',
  memrise_neon: 'editorial',
  aurora_lab: 'editorial',
};

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, Number(value)));
}

function normalizeHue(value) {
  const result = Number(value) % 360;
  return result < 0 ? result + 360 : result;
}

function componentToHex(value) {
  const hex = clamp(value, 0, 255).toString(16);
  return hex.length === 1 ? `0${hex}` : hex;
}

function hslToRgb(h, s, l) {
  const hue = normalizeHue(h) / 360;
  const sat = clamp(s, 0, 100) / 100;
  const lig = clamp(l, 0, 100) / 100;

  if (sat === 0) {
    const gray = Math.round(lig * 255);
    return { r: gray, g: gray, b: gray };
  }

  const q = lig < 0.5 ? lig * (1 + sat) : lig + sat - lig * sat;
  const p = 2 * lig - q;

  function hueToRgb(t) {
    let temp = t;
    if (temp < 0) {
      temp += 1;
    }
    if (temp > 1) {
      temp -= 1;
    }
    if (temp < 1 / 6) {
      return p + (q - p) * 6 * temp;
    }
    if (temp < 1 / 2) {
      return q;
    }
    if (temp < 2 / 3) {
      return p + (q - p) * (2 / 3 - temp) * 6;
    }
    return p;
  }

  return {
    r: Math.round(hueToRgb(hue + 1 / 3) * 255),
    g: Math.round(hueToRgb(hue) * 255),
    b: Math.round(hueToRgb(hue - 1 / 3) * 255),
  };
}

function hslToHex(h, s, l) {
  const rgb = hslToRgb(h, s, l);
  return `#${componentToHex(rgb.r)}${componentToHex(rgb.g)}${componentToHex(rgb.b)}`;
}

function hexToRgb(hex) {
  const source = String(hex || '').replace('#', '').trim();
  if (!/^[0-9a-fA-F]{6}$/.test(source)) {
    return { r: 44, g: 93, b: 255 };
  }
  return {
    r: parseInt(source.slice(0, 2), 16),
    g: parseInt(source.slice(2, 4), 16),
    b: parseInt(source.slice(4, 6), 16),
  };
}

function hexToRgba(hex, alpha) {
  const rgb = hexToRgb(hex);
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
}

export function buildFontSizeTokens(scalePercent) {
  const scale = clamp(scalePercent, 85, 130) / 100;
  const size = (base) => `${Math.round(base * scale)}px`;
  return {
    fontScale: scale,
    fontSizeBase: size(16),
    fontSizeTitle: size(28),
    fontSizeSubtitle: size(14),
    fontSizeListTitle: size(18),
    fontSizeListDesc: size(14),
    fontSizeButton: size(15),
    fontSizeMetric: size(32),
    fontSizeWord: size(52),
    fontSizeHero: size(42),
    fontSizeGrammarTitle: size(24),
    fontSizeGrammarDesc: size(14),
  };
}

export function normalizeCustomTheme(customTheme) {
  const theme = Object.assign({}, DEFAULT_CUSTOM_THEME, customTheme || {});
  return {
    base_hue: Math.round(normalizeHue(theme.base_hue)),
    base_lightness: Math.round(clamp(theme.base_lightness, 22, 72)),
    gradient_enabled: !!theme.gradient_enabled,
    gradient_shift: Math.round(clamp(theme.gradient_shift, 0, 90)),
    gradient_depth: Math.round(clamp(theme.gradient_depth, 0, 24)),
    font_hue: Math.round(normalizeHue(theme.font_hue)),
    font_lightness: Math.round(clamp(theme.font_lightness, 6, 92)),
    font_size_scale: Math.round(clamp(theme.font_size_scale, 85, 130)),
  };
}

function decorateTheme(theme) {
  const profileKey = EXPERIENCE_MAP[theme.id] || 'coach';
  return Object.assign({}, theme, EXPERIENCE_PROFILES[profileKey]);
}

const THEME_MAP = THEMES.reduce((map, theme) => {
  map[theme.id] = decorateTheme(theme);
  return map;
}, {});

export function buildCustomTheme(customTheme) {
  const normalized = normalizeCustomTheme(customTheme);
  const baseHue = normalized.base_hue;
  const baseLightness = normalized.base_lightness;
  const gradientHue = normalized.gradient_enabled ? normalizeHue(baseHue + normalized.gradient_shift) : baseHue;
  const gradientLightness = normalized.gradient_enabled
    ? clamp(baseLightness - normalized.gradient_depth, 18, 64)
    : baseLightness;
  const fontHue = normalized.font_hue;
  const fontLightness = normalized.font_lightness;

  const primaryStart = hslToHex(baseHue, 76, baseLightness);
  const primaryEnd = hslToHex(gradientHue, 78, gradientLightness);
  const heroStart = hslToHex(baseHue, 80, clamp(baseLightness - 6, 18, 56));
  const heroEnd = hslToHex(gradientHue, 82, clamp(gradientLightness - 8, 14, 52));
  const accent = hslToHex(baseHue, 72, clamp(baseLightness - 4, 20, 58));
  const pageStart = hslToHex(baseHue, 64, clamp(baseLightness + 46, 90, 98));
  const pageMid = hslToHex(baseHue, 48, clamp(baseLightness + 50, 94, 99));
  const pageEnd = hslToHex(baseHue, 36, clamp(baseLightness + 52, 96, 99));
  const cardBorder = hslToHex(baseHue, 34, clamp(baseLightness + 30, 78, 92));
  const secondaryBg = hslToHex(baseHue, 72, clamp(baseLightness + 34, 84, 95));
  const secondaryText = hslToHex(baseHue, 58, clamp(baseLightness - 18, 18, 52));
  const chipBg = hslToHex(baseHue, 70, clamp(baseLightness + 38, 88, 96));
  const chipText = hslToHex(baseHue, 60, clamp(baseLightness - 20, 16, 50));
  const segmentedBg = hslToHex(baseHue, 52, clamp(baseLightness + 38, 88, 96));
  const segmentedText = hslToHex(fontHue, 14, clamp(fontLightness + 26, 36, 72));
  const textPrimary = hslToHex(fontHue, 16, fontLightness);
  const textSecondary = hslToHex(fontHue, 12, clamp(fontLightness + 26, 38, 78));
  const tabText = hslToHex(fontHue, 12, clamp(fontLightness + 24, 40, 74));
  const fontSizes = buildFontSizeTokens(normalized.font_size_scale);

  return Object.assign(
    {
      id: CUSTOM_THEME_ID,
      name: '自定义主题',
      source: '用户调色',
      tone: normalized.gradient_enabled ? '渐变主题' : '纯色主题',
      description: '你自己调出来的主题，可继续微调并长期保存。',
      swatches: [primaryStart, primaryEnd, secondaryBg, pageStart],
      pageStart,
      pageMid,
      pageEnd,
      heroStart,
      heroEnd,
      cardBg: '#ffffff',
      cardBorder,
      textPrimary,
      textSecondary,
      accent,
      primaryStart,
      primaryEnd,
      secondaryBg,
      secondaryText,
      ghostBg: '#ffffff',
      ghostText: textPrimary,
      chipBg,
      chipText,
      segmentedBg,
      segmentedText,
      segmentedActiveBg: '#ffffff',
      segmentedActiveText: accent,
      navBg: `${hexToRgba(pageStart, 0.94)}`,
      navText: textPrimary,
      tabBarBg: 'rgba(255, 255, 255, 0.98)',
      tabText,
      tabActiveText: accent,
      tabIconBg: chipBg,
      tabActiveBg: secondaryBg,
      cardShadow: hexToRgba(primaryStart, 0.16),
      tabShadow: hexToRgba(primaryStart, 0.18),
      fontSizes,
      customConfig: normalized,
    },
    EXPERIENCE_PROFILES.playful,
  );
}

function getThemeById(themeId) {
  return THEME_MAP[themeId] || THEME_MAP[DEFAULT_THEME_ID];
}

export function resolveTheme(themeId, customTheme) {
  if (themeId === CUSTOM_THEME_ID) {
    return buildCustomTheme(customTheme);
  }
  return getThemeById(themeId);
}

export function buildThemePreview(themeId, customTheme) {
  const theme = resolveTheme(themeId, customTheme);
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
    heroStart: theme.heroStart,
    heroEnd: theme.heroEnd,
    secondaryBg: theme.secondaryBg,
    secondaryText: theme.secondaryText,
    themeFontClass: theme.themeFontClass,
    themeMotionClass: theme.themeMotionClass,
    fontSizes,
    isCustom: theme.id === CUSTOM_THEME_ID,
    previewStyle: `background:linear-gradient(135deg, ${theme.heroStart} 0%, ${theme.heroEnd} 100%);color:#ffffff;`,
    buttonStyle: `background:${theme.secondaryBg};color:${theme.secondaryText};`,
    surfaceStyle: `background:${theme.cardBg};border:1px solid ${theme.cardBorder};color:${theme.textPrimary};`,
  };
}

export function getThemeOptions() {
  return THEMES.map((theme) => buildThemePreview(theme.id));
}

export function buildThemeCssVars(themeId, customTheme) {
  const theme = resolveTheme(themeId, customTheme);
  const fontSizes = theme.fontSizes || buildFontSizeTokens(DEFAULT_CUSTOM_THEME.font_size_scale);

  return {
    '--bg': theme.pageEnd,
    '--bg-start': theme.pageStart,
    '--bg-mid': theme.pageMid,
    '--bg-end': theme.pageEnd,
    '--bg-panel': hexToRgba(theme.cardBg, 0.88),
    '--bg-panel-soft': hexToRgba(theme.secondaryBg, 0.58),
    '--bg-panel-strong': hexToRgba(theme.cardBg, 0.96),
    '--bg-hero': `linear-gradient(135deg, ${theme.heroStart} 0%, ${theme.heroEnd} 100%)`,
    '--bg-hero-soft': `linear-gradient(135deg, ${hexToRgba(theme.heroStart, 0.92)} 0%, ${hexToRgba(theme.heroEnd, 0.9)} 100%)`,
    '--bg-orb-a': hexToRgba(theme.primaryStart, 0.24),
    '--bg-orb-b': hexToRgba(theme.primaryEnd, 0.18),
    '--bg-orb-c': hexToRgba(theme.accent, 0.14),
    '--bg-orb-warm': hexToRgba(theme.primaryEnd, 0.16),
    '--border': hexToRgba(theme.cardBorder, 0.92),
    '--border-strong': hexToRgba(theme.cardBorder, 1),
    '--text': theme.textPrimary,
    '--text-soft': theme.textSecondary,
    '--text-light': 'rgba(255,255,255,0.92)',
    '--accent': theme.accent,
    '--accent-deep': theme.secondaryText,
    '--accent-soft': hexToRgba(theme.accent, 0.14),
    '--accent-warm': theme.primaryEnd,
    '--success': '#1f9d72',
    '--danger': '#cf4d4d',
    '--hero-start': theme.heroStart,
    '--hero-end': theme.heroEnd,
    '--chip-bg': theme.chipBg,
    '--chip-text': theme.chipText,
    '--segmented-bg': theme.segmentedBg,
    '--segmented-text': theme.segmentedText,
    '--segmented-active-bg': theme.segmentedActiveBg,
    '--segmented-active-text': theme.segmentedActiveText,
    '--shadow': `0 24px 80px ${hexToRgba(theme.primaryStart, 0.18)}`,
    '--shadow-soft': `0 14px 36px ${hexToRgba(theme.primaryStart, 0.12)}`,
    '--shadow-card': `0 18px 40px ${hexToRgba(theme.primaryStart, 0.11)}`,
    '--shadow-button': `0 12px 28px ${hexToRgba(theme.primaryStart, 0.24)}`,
    '--sidebar-hero-start': theme.heroStart,
    '--sidebar-hero-end': theme.heroEnd,
    '--sidebar-shadow': `0 28px 70px ${hexToRgba(theme.primaryStart, 0.28)}`,
    '--sidebar-mark-text': theme.secondaryText,
    '--sidebar-mark-bg': `linear-gradient(135deg, ${theme.primaryEnd} 0%, rgba(255, 255, 255, 0.98) 100%)`,
    '--sidebar-mark-shadow': `0 14px 24px ${hexToRgba(theme.primaryEnd, 0.24)}`,
    '--sidebar-active-bg': `linear-gradient(135deg, rgba(255, 255, 255, 0.18) 0%, ${hexToRgba(theme.primaryEnd, 0.16)} 100%)`,
    '--font-sans': theme.fontBody,
    '--font-display': theme.fontDisplay,
    '--font-size-base': fontSizes.fontSizeBase,
    '--font-size-title': fontSizes.fontSizeTitle,
    '--font-size-subtitle': fontSizes.fontSizeSubtitle,
    '--font-size-list-title': fontSizes.fontSizeListTitle,
    '--font-size-list-desc': fontSizes.fontSizeListDesc,
    '--font-size-button': fontSizes.fontSizeButton,
    '--font-size-metric': fontSizes.fontSizeMetric,
    '--font-size-word': fontSizes.fontSizeWord,
    '--font-size-hero': fontSizes.fontSizeHero,
  };
}

export function applyDocumentTheme(settings = {}) {
  const themeId = settings.theme_id || DEFAULT_THEME_ID;
  const customTheme = settings.custom_theme || DEFAULT_CUSTOM_THEME;
  const theme = resolveTheme(themeId, customTheme);
  const vars = buildThemeCssVars(themeId, customTheme);

  Object.entries(vars).forEach(([key, value]) => {
    document.documentElement.style.setProperty(key, value);
  });

  document.documentElement.dataset.themeId = theme.id;
  document.documentElement.dataset.themeMotion = theme.themeMotionClass || '';
  document.documentElement.dataset.themeFont = theme.themeFontClass || '';

  return theme;
}
