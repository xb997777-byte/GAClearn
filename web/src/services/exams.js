import { request } from '../lib/request';

export function generateTest(data = {}) {
  return request({
    url: '/api/v1/tests/generate',
    method: 'POST',
    data,
  });
}

export function generatePlacementTest(data = {}) {
  return request({
    url: '/api/v1/tests/placement/generate',
    method: 'POST',
    data,
  });
}

export function submitTest(data) {
  return request({
    url: '/api/v1/tests/submit',
    method: 'POST',
    data,
  });
}

export function submitPlacementTest(data) {
  return request({
    url: '/api/v1/tests/placement/submit',
    method: 'POST',
    data,
  });
}

export function getTestResult(testId) {
  return request({
    url: `/api/v1/tests/result/${testId}`,
    method: 'GET',
  });
}

export function getTestHistory() {
  return request({
    url: '/api/v1/tests/history',
    method: 'GET',
  });
}
