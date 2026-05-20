import { request } from '../lib/request';

export function getBootstrap() {
  return request({
    url: '/api/v1/system/bootstrap',
    method: 'GET',
    withAuth: false,
  });
}

export function synthesizeSpeech(data) {
  return request({
    url: '/api/v1/system/speech',
    method: 'POST',
    data,
  });
}
