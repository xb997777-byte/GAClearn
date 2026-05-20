import { request } from '../lib/request';

export function getReviewTasks(params = {}) {
  return request({
    url: '/api/v1/review/tasks',
    method: 'GET',
    params,
  });
}

export function submitReview(data) {
  return request({
    url: '/api/v1/review/submit',
    method: 'POST',
    data,
  });
}

export function getReviewResult(sessionId) {
  return request({
    url: `/api/v1/review/result/${sessionId}`,
    method: 'GET',
  });
}

export function listWrongWords() {
  return request({
    url: '/api/v1/wrong-words',
    method: 'GET',
  });
}

export function deleteWrongWord(wordId) {
  return request({
    url: `/api/v1/wrong-words/${wordId}`,
    method: 'DELETE',
  });
}
