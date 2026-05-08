const systemApi = require('../services/modules/system');
const store = require('../store/app-store');

let audioContext = null;
const speechUrlCache = {};
const DEFAULT_SPEECH_SPEED = 1;

function ensureAudioContext() {
  if (!audioContext) {
    audioContext = wx.createInnerAudioContext();
    audioContext.obeyMuteSwitch = false;
  }
  return audioContext;
}

function isSpeechPlaybackReady() {
  return true;
}

function normalizeSpeechSpeed(speed) {
  const value = Number(speed || DEFAULT_SPEECH_SPEED);
  if (!Number.isFinite(value)) {
    return DEFAULT_SPEECH_SPEED;
  }
  return Math.min(Math.max(Math.round(value * 100) / 100, 0.5), 1.2);
}

function getGlobalSpeechSpeed() {
  const settings = store.getState().settings || {};
  return normalizeSpeechSpeed(settings.speech_speed || DEFAULT_SPEECH_SPEED);
}

function resolveSpeechSpeed(options = {}) {
  if (options.speed !== undefined && options.speed !== null && options.speed !== '') {
    return normalizeSpeechSpeed(options.speed);
  }
  return getGlobalSpeechSpeed();
}

function playAudioUrl(url, options = {}) {
  return new Promise((resolve, reject) => {
    if (!url) {
      reject(new Error('音频地址为空'));
      return;
    }
    const ctx = ensureAudioContext();
    ctx.stop();
    ctx.src = url;
    if ('playbackRate' in ctx) {
      ctx.playbackRate = resolveSpeechSpeed({ speed: options.playbackRate });
    }
    ctx.onEnded(() => resolve({ source: 'url', url }));
    ctx.onError((error) => reject(new Error((error && error.errMsg) || '音频播放失败')));
    ctx.play();
  });
}

function buildSpeechCacheKey(text, options = {}) {
  return `${options.lang || 'en-US'}::${resolveSpeechSpeed(options)}::${String(text || '').trim()}`;
}

async function getSpeechAudioUrl(text, options = {}) {
  const content = String(text || '').trim();
  if (!content) {
    throw new Error('朗读内容为空');
  }
  if (options.audioUrl) {
    return options.audioUrl;
  }

  const cacheKey = buildSpeechCacheKey(content, options);
  if (speechUrlCache[cacheKey]) {
    return speechUrlCache[cacheKey];
  }

  const response = await systemApi.synthesizeSpeech({
    text: content,
    lang: options.lang || 'en-US',
    speed: resolveSpeechSpeed(options)
  });
  if (!response || !response.audio_url) {
    throw new Error('语音生成失败');
  }
  speechUrlCache[cacheKey] = response.audio_url;
  return response.audio_url;
}

async function speakText(text, options = {}) {
  const url = await getSpeechAudioUrl(text, options);
  await playAudioUrl(url, options.audioUrl ? { playbackRate: resolveSpeechSpeed(options) } : { playbackRate: 1 });
  return { source: options.audioUrl ? 'url' : 'backend_tts', url };
}

module.exports = {
  isSpeechPlaybackReady,
  normalizeSpeechSpeed,
  getGlobalSpeechSpeed,
  playAudioUrl,
  getSpeechAudioUrl,
  speakText
};
