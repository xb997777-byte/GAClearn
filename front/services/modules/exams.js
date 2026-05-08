const { request } = require('../request');

function generateTest(data = {}) {
  return request({
    url: '/tests/generate',
    method: 'POST',
    data
  });
}

function generatePlacementTest(data = {}) {
  return request({
    url: '/tests/placement/generate',
    method: 'POST',
    data
  });
}

function submitTest(data) {
  return request({
    url: '/tests/submit',
    method: 'POST',
    data
  });
}

function submitPlacementTest(data) {
  return request({
    url: '/tests/placement/submit',
    method: 'POST',
    data
  });
}

function getTestResult(testId) {
  return request({
    url: `/tests/result/${testId}`,
    method: 'GET'
  });
}

function getTestHistory() {
  return request({
    url: '/tests/history',
    method: 'GET'
  });
}

module.exports = {
  generateTest,
  generatePlacementTest,
  submitTest,
  submitPlacementTest,
  getTestResult,
  getTestHistory
};
