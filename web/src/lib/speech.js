import { synthesizeSpeech } from '../services/system';

let activeAudio = null;
const speechUrlCache = new Map();

export function normalizeSpeechSpeed(speed) {
  const value = Number(speed || 1);
  if (!Number.isFinite(value)) {
    return 1;
  }
  return Math.min(Math.max(Math.round(value * 100) / 100, 0.5), 1.2);
}

function buildSpeechKey(text, options = {}) {
  return `${options.lang || 'en-US'}::${normalizeSpeechSpeed(options.speed)}::${String(text || '').trim()}`;
}

export async function playAudioUrl(url, options = {}) {
  if (!url) {
    throw new Error('音频地址为空');
  }
  if (activeAudio) {
    activeAudio.pause();
  }
  const audio = new Audio(url);
  audio.playbackRate = normalizeSpeechSpeed(options.playbackRate || 1);
  activeAudio = audio;
  await audio.play();
  return new Promise((resolve, reject) => {
    audio.addEventListener('ended', () => resolve({ source: 'url', url }), { once: true });
    audio.addEventListener('error', () => reject(new Error('音频播放失败')), { once: true });
  });
}

export async function getSpeechAudioUrl(text, options = {}) {
  const content = String(text || '').trim();
  if (!content) {
    throw new Error('朗读内容为空');
  }
  if (options.audioUrl) {
    return options.audioUrl;
  }
  const key = buildSpeechKey(content, options);
  if (speechUrlCache.has(key)) {
    return speechUrlCache.get(key);
  }
  const response = await synthesizeSpeech({
    text: content,
    lang: options.lang || 'en-US',
    speed: normalizeSpeechSpeed(options.speed || 1),
  });
  if (!response || !response.audio_url) {
    throw new Error('语音生成失败');
  }
  speechUrlCache.set(key, response.audio_url);
  return response.audio_url;
}

export async function speakText(text, options = {}) {
  const url = await getSpeechAudioUrl(text, options);
  return playAudioUrl(url, { playbackRate: 1 });
}
