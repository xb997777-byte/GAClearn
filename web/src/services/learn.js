import { request } from '../lib/request';

export function getLearnWords(params = {}) {
  return request({
    url: '/api/v1/learn/words',
    method: 'GET',
    params,
  });
}

export function getLearnWordDetail(wordId) {
  return request({
    url: `/api/v1/learn/words/${wordId}`,
    method: 'GET',
  });
}

export function createLearningRecord(data) {
  return request({
    url: '/api/v1/learn/records',
    method: 'POST',
    data,
  });
}

export function createLearningRecordBatch(data) {
  return request({
    url: '/api/v1/learn/records/batch',
    method: 'POST',
    data,
  });
}

export function listFavorites() {
  return request({
    url: '/api/v1/favorites',
    method: 'GET',
  });
}

export function addFavorite(data) {
  return request({
    url: '/api/v1/favorites',
    method: 'POST',
    data,
  });
}

export function removeFavorite(wordId) {
  return request({
    url: `/api/v1/favorites/${wordId}`,
    method: 'DELETE',
  });
}
