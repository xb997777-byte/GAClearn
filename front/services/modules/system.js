const { request } = require('../request');

function getBootstrap() {
  return request({
    url: '/system/bootstrap',
    method: 'GET',
    withAuth: false
  });
}

function synthesizeSpeech(data) {
  return request({
    url: '/system/speech',
    method: 'POST',
    data
  });
}

module.exports = {
  getBootstrap,
  synthesizeSpeech
};
