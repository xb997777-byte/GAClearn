const { request } = require('../request');

function listBooks(params = {}) {
  return request({
    url: '/books',
    method: 'GET',
    data: params,
    withAuth: false
  });
}

function getBookDetail(bookId) {
  return request({
    url: `/books/${bookId}`,
    method: 'GET',
    withAuth: false
  });
}

function getBookWords(bookId, params = {}) {
  return request({
    url: `/books/${bookId}/words`,
    method: 'GET',
    data: params,
    withAuth: false
  });
}

module.exports = {
  listBooks,
  getBookDetail,
  getBookWords
};
