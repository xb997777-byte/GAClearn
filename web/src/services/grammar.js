import { request } from '../lib/request';

export function listTopics() {
  return request({
    url: '/api/v1/grammar/topics',
    method: 'GET',
  });
}

export function listSentences(params = {}) {
  return request({
    url: '/api/v1/grammar/sentences',
    method: 'GET',
    params,
  });
}

export function getSentenceDetail(sentenceId) {
  return request({
    url: `/api/v1/grammar/sentences/${sentenceId}`,
    method: 'GET',
  });
}

export function analyzeSentence(sentence) {
  return request({
    url: '/api/v1/grammar/analyze',
    method: 'POST',
    data: { sentence },
  });
}

export function askQuestion(data) {
  return request({
    url: '/api/v1/grammar/ask',
    method: 'POST',
    data,
  });
}

export function getRecommendations(params = {}) {
  return request({
    url: '/api/v1/grammar/sentences/recommend',
    method: 'GET',
    params,
  });
}

export function createRecord(payload) {
  return request({
    url: '/api/v1/grammar/records',
    method: 'POST',
    data: payload,
  });
}

export function getProgress() {
  return request({
    url: '/api/v1/grammar/progress',
    method: 'GET',
  });
}
