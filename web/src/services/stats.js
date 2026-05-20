import { request } from '../lib/request';

export function getOverview() {
  return request({
    url: '/api/v1/stats/overview',
    method: 'GET',
  });
}

export function getTrend(params = {}) {
  return request({
    url: '/api/v1/stats/trend',
    method: 'GET',
    params,
  });
}

export function checkin() {
  return request({
    url: '/api/v1/checkin',
    method: 'POST',
  });
}

export function getCheckinHistory() {
  return request({
    url: '/api/v1/checkin/history',
    method: 'GET',
  });
}
