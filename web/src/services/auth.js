import { request } from '../lib/request';

export function wxLogin(data) {
  return request({
    url: '/api/v1/auth/wx-login',
    method: 'POST',
    data,
    withAuth: false,
  });
}

export function getMe() {
  return request({
    url: '/api/v1/users/me',
    method: 'GET',
  });
}

export function syncProfile(data) {
  return request({
    url: '/api/v1/auth/profile',
    method: 'POST',
    data,
  });
}

export function refreshToken() {
  return request({
    url: '/api/v1/auth/refresh',
    method: 'POST',
  });
}

export function getSettings() {
  return request({
    url: '/api/v1/users/settings',
    method: 'GET',
  });
}

export function updateSettings(data) {
  return request({
    url: '/api/v1/users/settings',
    method: 'PUT',
    data,
  });
}

export function submitFeedback(data) {
  return request({
    url: '/api/v1/users/feedback',
    method: 'POST',
    data,
  });
}

export function rebuildPersonalizedRag() {
  return request({
    url: '/api/v1/users/settings/personalized-rag/rebuild',
    method: 'POST',
  });
}
