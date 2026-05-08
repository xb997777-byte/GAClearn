const { request } = require('../request');

function getOverview() {
  return request({
    url: '/stats/overview',
    method: 'GET'
  });
}

function getTrend(params = {}) {
  return request({
    url: '/stats/trend',
    method: 'GET',
    data: params
  });
}

function checkin() {
  return request({
    url: '/checkin',
    method: 'POST'
  });
}

function getCheckinHistory() {
  return request({
    url: '/checkin/history',
    method: 'GET'
  });
}

module.exports = {
  getOverview,
  getTrend,
  checkin,
  getCheckinHistory
};
