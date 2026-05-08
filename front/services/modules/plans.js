const { request } = require('../request');

function getCurrentPlan() {
  return request({
    url: '/plans/current',
    method: 'GET'
  });
}

function createPlan(data) {
  return request({
    url: '/plans',
    method: 'POST',
    data
  });
}

function updateCurrentPlan(data) {
  return request({
    url: '/plans/current',
    method: 'PUT',
    data
  });
}

function getPlanHistory(limit = 12) {
  return request({
    url: `/plans/current/history?limit=${encodeURIComponent(limit)}`,
    method: 'GET'
  });
}

function applyAiPlanPatch(data) {
  return request({
    url: '/plans/current/apply-ai-patch',
    method: 'POST',
    data
  });
}

function switchBook(data) {
  return request({
    url: '/plans/current/switch-book',
    method: 'POST',
    data
  });
}

function getTodayTask() {
  return request({
    url: '/tasks/today',
    method: 'GET'
  });
}

function startTodayTask() {
  return request({
    url: '/tasks/today/start',
    method: 'POST'
  });
}

function finishTodayTask() {
  return request({
    url: '/tasks/today/finish',
    method: 'POST'
  });
}

module.exports = {
  getCurrentPlan,
  createPlan,
  updateCurrentPlan,
  getPlanHistory,
  applyAiPlanPatch,
  switchBook,
  getTodayTask,
  startTodayTask,
  finishTodayTask
};
