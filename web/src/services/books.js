import { request } from '../lib/request';

export function listBooks(params = {}) {
  return request({
    url: '/api/v1/books',
    method: 'GET',
    params,
    withAuth: false,
  });
}

export function getBookDetail(bookId) {
  return request({
    url: `/api/v1/books/${bookId}`,
    method: 'GET',
    withAuth: false,
  });
}

export function getBookWords(bookId, params = {}) {
  return request({
    url: `/api/v1/books/${bookId}/words`,
    method: 'GET',
    params,
    withAuth: false,
  });
}
