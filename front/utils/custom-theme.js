const CUSTOM_THEME_ID = 'custom_dynamic';

const DEFAULT_CUSTOM_THEME = {
  base_hue: 218,
  base_lightness: 48,
  gradient_enabled: true,
  gradient_shift: 18,
  gradient_depth: 12,
  font_hue: 220,
  font_lightness: 18,
  font_size_scale: 100
};

const HUE_PRESETS = [
  { id: 'sky', label: '天空蓝', hue: 210, color: '#3b82f6' },
  { id: 'forest', label: '森林绿', hue: 132, color: '#22c55e' },
  { id: 'sunset', label: '日落橙', hue: 28, color: '#f97316' },
  { id: 'berry', label: '莓果紫', hue: 282, color: '#a855f7' },
  { id: 'rose', label: '玫瑰粉', hue: 340, color: '#f43f5e' },
  { id: 'ocean', label: '海风青', hue: 188, color: '#06b6d4' },
  { id: 'amber', label: '琥珀黄', hue: 44, color: '#f59e0b' },
  { id: 'ink', label: '墨蓝灰', hue: 224, color: '#334155' }
];

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, Number(value)));
}

function normalizeHue(value) {
  const result = Number(value) % 360;
  return result < 0 ? result + 360 : result;
}

function normalizeCustomTheme(customTheme) {
  const theme = Object.assign({}, DEFAULT_CUSTOM_THEME, customTheme || {});
  return {
    base_hue: Math.round(normalizeHue(theme.base_hue)),
    base_lightness: Math.round(clamp(theme.base_lightness, 22, 72)),
    gradient_enabled: !!theme.gradient_enabled,
    gradient_shift: Math.round(clamp(theme.gradient_shift, 0, 90)),
    gradient_depth: Math.round(clamp(theme.gradient_depth, 0, 24)),
    font_hue: Math.round(normalizeHue(theme.font_hue)),
    font_lightness: Math.round(clamp(theme.font_lightness, 6, 92)),
    font_size_scale: Math.round(clamp(theme.font_size_scale, 85, 130))
  };
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
    b: Math.round(hueToRgb(hue - 1 / 3) * 255)
  };
}

function componentToHex(value) {
  const hex = clamp(value, 0, 255).toString(16);
  return hex.length === 1 ? `0${hex}` : hex;
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
    b: parseInt(source.slice(4, 6), 16)
  };
}

function hexToRgba(hex, alpha) {
  const rgb = hexToRgb(hex);
  return `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${alpha})`;
}

function buildFontSizeTokens(scalePercent) {
  const scale = clamp(scalePercent, 85, 130) / 100;
  const size = (base) => `${Math.round(base * scale)}rpx`;
  return {
    fontScale: scale,
    fontSizeBase: size(28),
    fontSizeTitle: size(34),
    fontSizeSubtitle: size(24),
    fontSizeListTitle: size(30),
    fontSizeListDesc: size(24),
    fontSizeButton: size(28),
    fontSizeMetric: size(40),
    fontSizeWord: size(58),
    fontSizeHero: size(46),
    fontSizeGrammarTitle: size(32),
    fontSizeGrammarDesc: size(24)
  };
}

function buildCustomTheme(customTheme) {
  const normalized = normalizeCustomTheme(customTheme);
  const baseHue = normalized.base_hue;
  const baseLightness = normalized.base_lightness;
  const gradientHue = normalized.gradient_enabled
    ? normalizeHue(baseHue + normalized.gradient_shift)
    : baseHue;
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

  return {
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
    cardShadow: hexToRgba(primaryStart, 0.14),
    tabShadow: hexToRgba(primaryStart, 0.16),
    themeFontClass: 'font-coach',
    themeMotionClass: normalized.gradient_enabled ? 'motion-glide' : 'motion-focus',
    grammarThemeClass: normalized.gradient_enabled ? 'grammar-theme-coach' : 'grammar-theme-editorial',
    grammarCardHoverClass: normalized.gradient_enabled ? 'hover-card-slide' : 'hover-card-focus',
    grammarActionHoverClass: normalized.gradient_enabled ? 'hover-action-sweep' : 'hover-action-nudge',
    fontBody: "'Avenir Next','Segoe UI','PingFang SC','Microsoft YaHei',sans-serif",
    fontDisplay: "'Avenir Next','Segoe UI','PingFang SC','Microsoft YaHei',sans-serif",
    fontLabel: `字色 ${textPrimary.toUpperCase()}`,
    interactionLabel: normalized.gradient_enabled ? '渐变推进' : '纯色聚焦',
    customConfig: normalized,
    fontSizes
  };
}

module.exports = {
  CUSTOM_THEME_ID,
  DEFAULT_CUSTOM_THEME,
  HUE_PRESETS,
  normalizeCustomTheme,
  hexToRgba,
  buildCustomTheme,
  buildFontSizeTokens
};
