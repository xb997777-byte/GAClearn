const { request } = require('../request');

function getReviewTasks(params = {}) {
  return request({
    url: '/review/tasks',
    method: 'GET',
    params
  });
}

function submitReview(data) {
  return request({
    url: '/review/submit',
    method: 'POST',
    data
  });
}

function getReviewResult(sessionId) {
  return request({
    url: `/review/result/${sessionId}`,
    method: 'GET'
  });
}

function listWrongWords() {
  return request({
    url: '/wrong-words',
    method: 'GET'
  });
}

function deleteWrongWord(wordId) {
  return request({
    url: `/wrong-words/${wordId}`,
    method: 'DELETE'
  });
}

module.exports = {
  getReviewTasks,
  submitReview,
  getReviewResult,
  listWrongWords,
  deleteWrongWord
};
