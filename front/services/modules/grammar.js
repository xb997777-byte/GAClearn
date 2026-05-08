const { request } = require('../request');
const GRAMMAR_AI_TIMEOUT = 30000;

function listTopics() {
  return request({
    url: '/grammar/topics',
    method: 'GET'
  });
}

function listSentences(params = {}) {
  return request({
    url: '/grammar/sentences',
    method: 'GET',
    data: params
  });
}

function getSentenceDetail(sentenceId) {
  return request({
    url: `/grammar/sentences/${sentenceId}`,
    method: 'GET'
  });
}

function analyzeSentence(sentence) {
  return request({
    url: '/grammar/analyze',
    method: 'POST',
    data: { sentence },
    timeout: GRAMMAR_AI_TIMEOUT
  });
}

function askQuestion(data) {
  return request({
    url: '/grammar/ask',
    method: 'POST',
    data,
    timeout: GRAMMAR_AI_TIMEOUT
  });
}

function getRecommendations(params = {}) {
  return request({
    url: '/grammar/sentences/recommend',
    method: 'GET',
    data: params
  });
}

function createRecord(payload) {
  return request({
    url: '/grammar/records',
    method: 'POST',
    data: payload
  });
}

function getProgress() {
  return request({
    url: '/grammar/progress',
    method: 'GET'
  });
}

module.exports = {
  listTopics,
  listSentences,
  getSentenceDetail,
  analyzeSentence,
  askQuestion,
  getRecommendations,
  createRecord,
  getProgress
};
