const DEFAULT_DIFFICULTIES = [
  { id: 0, label: '全部难度' },
  { id: 1, label: '基础' },
  { id: 2, label: '进阶' },
  { id: 3, label: '考试' }
];

const VIEW_MODE_META = {
  complete: {
    title: '完整视图',
    description: '按原句顺序阅读，适合先看整句，再逐块理解。'
  },
  core: {
    title: '主干视图',
    description: '先抓主语、谓语、宾语，再把修饰层补回去。'
  }
};

function buildLegendMap(legend) {
  const result = {};
  (legend || []).forEach((item) => {
    result[item.token] = item;
  });
  return result;
}

function isPunctuationToken(token) {
  return /^[,.;:!?)\]%]+$/.test(token);
}

function tokenizeSegmentText(text) {
  if (!text) {
    return [];
  }
  const matches = text.match(/[A-Za-z0-9]+(?:['’][A-Za-z0-9]+)*|[^\s]/g);
  return matches || [];
}

function buildSentenceTokens(segments, selectedAnnotationId) {
  const tokens = [];
  let tokenIndex = 0;

  (segments || []).forEach((segment) => {
    const parts = tokenizeSegmentText(segment.text);
    if (!parts.length) {
      return;
    }

    parts.forEach((part) => {
      if (isPunctuationToken(part) && tokens.length) {
        tokens[tokens.length - 1].text += part;
        return;
      }

      const annotationId = segment.annotation_id || null;
      tokens.push({
        id: `token-${tokenIndex}`,
        text: part,
        annotationId,
        roleLabel: segment.role_label || '',
        grammarLabel: segment.grammar_label || '',
        background: annotationId ? segment.background : '#ffffff',
        color: annotationId ? segment.color : '#344054',
        style: annotationId
          ? `background:${segment.background};color:${segment.color};`
          : '',
        isPlain: !annotationId,
        isFocused: !!annotationId && annotationId === selectedAnnotationId,
        isDimmed: !!selectedAnnotationId && !!annotationId && annotationId !== selectedAnnotationId,
        isMutedPlain: !annotationId && !!selectedAnnotationId
      });
      tokenIndex += 1;
    });
  });

  return tokens;
}

function buildGuideCards(detail) {
  const annotations = detail && detail.annotations ? detail.annotations : [];
  const chunks = detail && detail.chunk_breakdown ? detail.chunk_breakdown : [];

  return chunks.map((chunk, index) => {
    const annotation = annotations[index] || null;
    const annotationId = annotation ? annotation.id : null;
    const background = annotation ? annotation.background : '#f8fafc';
    const color = annotation ? annotation.color : '#344054';
    const roleLabel = chunk.role_label || (annotation ? annotation.role_label : '') || '语法成分';
    const grammarLabel = annotation ? (annotation.grammar_label || annotation.role_label) : roleLabel;
    const isCore = chunk.is_core !== undefined ? !!chunk.is_core : !!(annotation && annotation.is_core);

    return {
      id: annotationId || `guide-${index}`,
      annotationId,
      order: index + 1,
      orderLabel: index + 1 < 10 ? `0${index + 1}` : `${index + 1}`,
      english: chunk.en || (annotation ? annotation.text_span : ''),
      chinese: chunk.cn || '',
      note: chunk.note || (annotation ? annotation.explanation : '') || '',
      roleLabel,
      grammarLabel,
      roleType: annotation ? annotation.role_type : '',
      token: annotation ? annotation.color_token : 'plain',
      background,
      color,
      accentStyle: `background:${background};color:${color};`,
      outlineStyle: `border-color:${color};`,
      isCore,
      relationText: isCore ? '主干' : '补充'
    };
  });
}

function buildAnnotationMap(detail) {
  const map = {};
  const annotations = detail && detail.annotations ? detail.annotations : [];
  annotations.forEach((item) => {
    map[item.id] = item;
  });
  return map;
}

function buildDisplaySegments(detail, viewMode, selectedAnnotation) {
  if (!detail) {
    return [];
  }

  if (viewMode !== 'core') {
    return detail.complete_segments || [];
  }

  const selectedAnnotationId = selectedAnnotation ? selectedAnnotation.id : 0;
  const annotationMap = buildAnnotationMap(detail);

  return (detail.complete_segments || []).map((segment) => {
    const annotationId = segment.annotation_id || 0;
    if (!annotationId) {
      return segment;
    }

    const annotation = annotationMap[annotationId];
    if ((annotation && annotation.is_core) || annotationId === selectedAnnotationId) {
      return segment;
    }

    return Object.assign({}, segment, {
      annotation_id: null,
      background: '#ffffff',
      color: '#344054',
      role_label: '',
      grammar_label: ''
    });
  });
}

function decorateGuideCards(cards, selectedAnnotationId) {
  return (cards || []).map((card, index, list) => Object.assign({}, card, {
    isSelected: !!selectedAnnotationId && card.annotationId === selectedAnnotationId,
    isDimmed: !!selectedAnnotationId && !!card.annotationId && card.annotationId !== selectedAnnotationId,
    isEven: index % 2 === 1,
    isLast: index === list.length - 1
  }));
}

function pickDefaultAnnotation(detail) {
  const annotations = detail && detail.annotations ? detail.annotations : [];
  return annotations.find((item) => item.is_core) || annotations[0] || null;
}

function findAnnotationById(detail, annotationId) {
  const annotations = detail && detail.annotations ? detail.annotations : [];
  if (!annotationId) {
    return null;
  }
  return annotations.find((item) => item.id === annotationId) || null;
}

function findGuideCardByAnnotationId(cards, annotationId) {
  if (!annotationId) {
    return null;
  }
  return (cards || []).find((item) => item.annotationId === annotationId) || null;
}

function buildVisualState(detail, viewMode, selectedAnnotationId, sourceGuideCards) {
  const selectedAnnotation = findAnnotationById(detail, selectedAnnotationId) || pickDefaultAnnotation(detail);
  const resolvedGuideCards = sourceGuideCards || buildGuideCards(detail);
  const displaySegments = buildDisplaySegments(detail, viewMode, selectedAnnotation);
  const sentenceTokens = buildSentenceTokens(displaySegments, selectedAnnotation ? selectedAnnotation.id : 0);
  const guideCards = decorateGuideCards(resolvedGuideCards, selectedAnnotation ? selectedAnnotation.id : 0);
  const coreGuideCards = guideCards.filter((item) => item.isCore);
  const supportGuideCards = guideCards.filter((item) => !item.isCore);
  const selectedGuideCard =
    findGuideCardByAnnotationId(guideCards, selectedAnnotation ? selectedAnnotation.id : 0) ||
    coreGuideCards[0] ||
    guideCards[0] ||
    null;
  const viewMeta = VIEW_MODE_META[viewMode] || VIEW_MODE_META.complete;

  return {
    selectedAnnotation,
    sentenceTokens,
    guideCards,
    coreGuideCards,
    supportGuideCards,
    selectedGuideCard,
    viewModeTitle: viewMeta.title,
    viewModeDescription: viewMeta.description
  };
}

module.exports = {
  DEFAULT_DIFFICULTIES,
  VIEW_MODE_META,
  buildLegendMap,
  buildGuideCards,
  buildVisualState,
  findAnnotationById,
  pickDefaultAnnotation
};
