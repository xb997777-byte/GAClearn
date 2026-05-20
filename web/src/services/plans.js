import { request } from '../lib/request';

export function getCurrentPlan() {
  return request({
    url: '/api/v1/plans/current',
    method: 'GET',
  });
}

export function createPlan(data) {
  return request({
    url: '/api/v1/plans',
    method: 'POST',
    data,
  });
}

export function updateCurrentPlan(data) {
  return request({
    url: '/api/v1/plans/current',
    method: 'PUT',
    data,
  });
}

export function getPlanHistory(limit = 12) {
  return request({
    url: '/api/v1/plans/current/history',
    method: 'GET',
    params: { limit },
  });
}

export function applyAiPlanPatch(data) {
  return request({
    url: '/api/v1/plans/current/apply-ai-patch',
    method: 'POST',
    data,
  });
}

export function switchBook(data) {
  return request({
    url: '/api/v1/plans/current/switch-book',
    method: 'POST',
    data,
  });
}

export function getTodayTask() {
  return request({
    url: '/api/v1/tasks/today',
    method: 'GET',
  });
}

export function startTodayTask() {
  return request({
    url: '/api/v1/tasks/today/start',
    method: 'POST',
  });
}

export function finishTodayTask() {
  return request({
    url: '/api/v1/tasks/today/finish',
    method: 'POST',
  });
}
