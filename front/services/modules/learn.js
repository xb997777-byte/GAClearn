const { request } = require('../request');

function getLearnWords(params = {}) {
  return request({
    url: '/learn/words',
    method: 'GET',
    data: params
  });
}

function getLearnWordDetail(wordId) {
  return request({
    url: `/learn/words/${wordId}`,
    method: 'GET'
  });
}

function createLearningRecord(data) {
  return request({
    url: '/learn/records',
    method: 'POST',
    data
  });
}

function createLearningRecordBatch(data) {
  return request({
    url: '/learn/records/batch',
    method: 'POST',
    data
  });
}

function listFavorites() {
  return request({
    url: '/favorites',
    method: 'GET'
  });
}

function addFavorite(data) {
  return request({
    url: '/favorites',
    method: 'POST',
    data
  });
}

function removeFavorite(wordId) {
  return request({
    url: `/favorites/${wordId}`,
    method: 'DELETE'
  });
}

module.exports = {
  getLearnWords,
  getLearnWordDetail,
  createLearningRecord,
  createLearningRecordBatch,
  listFavorites,
  addFavorite,
  removeFavorite
};
