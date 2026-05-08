const { request } = require('../request');

function wxLogin(data) {
  return request({
    url: '/auth/wx-login',
    method: 'POST',
    data,
    withAuth: false
  });
}

function getMe() {
  return request({
    url: '/users/me',
    method: 'GET'
  });
}

function syncProfile(data) {
  return request({
    url: '/auth/profile',
    method: 'POST',
    data
  });
}

function refreshToken() {
  return request({
    url: '/auth/refresh',
    method: 'POST'
  });
}

function getSettings() {
  return request({
    url: '/users/settings',
    method: 'GET'
  });
}

function updateSettings(data) {
  return request({
    url: '/users/settings',
    method: 'PUT',
    data
  });
}

function submitFeedback(data) {
  return request({
    url: '/users/feedback',
    method: 'POST',
    data
  });
}

function rebuildPersonalizedRag() {
  return request({
    url: '/users/settings/personalized-rag/rebuild',
    method: 'POST'
  });
}

module.exports = {
  wxLogin,
  getMe,
  syncProfile,
  refreshToken,
  getSettings,
  updateSettings,
  submitFeedback,
  rebuildPersonalizedRag
};
