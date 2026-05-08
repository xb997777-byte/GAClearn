function splitSynonyms(text) {
  return (text || '')
    .split(/[;,/，；、]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function buildQuizOptions(currentWord, words) {
  const options = [];
  const seen = new Set();

  function pushOption(text) {
    const value = (text || '').trim();
    if (!value || seen.has(value)) {
      return;
    }
    seen.add(value);
    options.push(value);
  }

  pushOption(currentWord.meaning_cn);
  (words || []).forEach((item) => {
    if (item && item.id !== currentWord.id) {
      pushOption(item.meaning_cn);
    }
  });

  return options.slice(0, 4);
}

function buildLocalWordTutor(word, words = [], extra = {}) {
  if (!word) {
    return null;
  }

  const synonymList = splitSynonyms(word.synonyms);
  const whyRecommended = extra.whyRecommended || word.adaptive_reason || '这是你当前查看的词条，先把核心词义和例句理解透会更高效。';
  const confusingPoints = [];

  if (extra.confusingPoints && extra.confusingPoints.length) {
    extra.confusingPoints.forEach((item) => {
      if (item && confusingPoints.length < 3) {
        confusingPoints.push(item);
      }
    });
  }

  if (synonymList.length && confusingPoints.length < 3) {
    confusingPoints.push(`这个词常和 ${synonymList.slice(0, 2).join('、')} 一起记，但还是要回到例句里区分具体语气和搭配。`);
  }

  if (word.part_of_speech && confusingPoints.length < 3) {
    confusingPoints.push(`这里主要按 ${word.part_of_speech} 来理解和使用，不建议只背中文意思。`);
  }

  if (word.example_sentence && confusingPoints.length < 3) {
    confusingPoints.push('建议先读例句，再观察这个词在句子里的位置和作用。');
  }

  const quizOptions = buildQuizOptions(word, words);

  return {
    simple_explanation_cn: `${word.word} 常见意思是“${word.meaning_cn}”，这里先按 ${word.part_of_speech || '当前词性'} 来理解。`,
    memory_tip: word.example_sentence
      ? `先把它放进例句“${word.example_sentence}”里记，会比只背中文更稳。`
      : `先把“${word.word} = ${word.meaning_cn}”配对记住。`,
    usage_tip: word.example_translation
      ? `对照“${word.example_translation}”来看这个词在句子里的位置和作用。`
      : '建议先看词性，再模仿当前例句自己造一个短句。',
    why_recommended: whyRecommended,
    confusing_points: confusingPoints.slice(0, 3),
    synonym_compare: synonymList.slice(0, 3).map((item) => ({
      word: item,
      meaning_cn: '近义表达',
      difference: '它和当前词意思接近，但还是要结合例句区分具体场景。'
    })),
    mini_quiz: quizOptions.length >= 2 ? {
      prompt: `下面哪个中文释义最贴近 ${word.word}？`,
      options: quizOptions,
      answer: word.meaning_cn,
      explanation: '先把核心义项记准，再回到例句里理解它的真实用法。'
    } : null
  };
}

module.exports = {
  buildLocalWordTutor
};
