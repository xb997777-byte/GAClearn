import axios from 'axios';
import { REQUEST_TIMEOUT } from '../config/env';
import router from '../router';
import { useSessionStore } from '../stores/session';

const client = axios.create({
  timeout: REQUEST_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use((config) => {
  const sessionStore = useSessionStore();
  if (!sessionStore.hydrated) {
    sessionStore.hydrate();
  }
  if (sessionStore.token && config.withAuth !== false) {
    config.headers.Authorization = `Token ${sessionStore.token}`;
  }
  return config;
});

let refreshPromise = null;

async function ensureRefreshedToken() {
  if (!refreshPromise) {
    refreshPromise = client({
      url: '/api/v1/auth/refresh',
      method: 'POST',
      withAuth: true,
      _retried: true,
    })
      .then((response) => {
        const payload = (response && response.data && response.data.data) || {};
        const sessionStore = useSessionStore();
        sessionStore.setTokenMeta(payload.token, payload.expired_at || '');
        return payload.token || '';
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config || {};
    if (error.response && [401, 403].includes(error.response.status) && originalRequest.withAuth !== false && !originalRequest._retried) {
      try {
        originalRequest._retried = true;
        const token = await ensureRefreshedToken();
        if (token) {
          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Token ${token}`;
        }
        return client(originalRequest);
      } catch (_refreshError) {
        const sessionStore = useSessionStore();
        sessionStore.clearAuth();
        if (router.currentRoute.value.name !== 'login') {
          router.replace({
            name: 'login',
            query: {
              redirect: router.currentRoute.value.fullPath,
            },
          });
        }
        throw new Error((error.response.data && (error.response.data.detail || error.response.data.message)) || '登录已失效，请重新登录');
      }
    }
    if (error.response && [401, 403].includes(error.response.status)) {
      const sessionStore = useSessionStore();
      sessionStore.clearAuth();
      if (router.currentRoute.value.name !== 'login') {
        router.replace({
          name: 'login',
          query: {
            redirect: router.currentRoute.value.fullPath,
          },
        });
      }
      throw new Error((error.response.data && (error.response.data.detail || error.response.data.message)) || '登录已失效，请重新登录');
    }
    if (error.code === 'ECONNABORTED') {
      throw new Error('请求超时，当前 AI 分析可能仍在生成中，请稍后重试');
    }
    if (!error.response) {
      throw new Error(`网络请求失败：${error.message || 'unknown error'}`);
    }
    throw error;
  },
);

export async function request(config) {
  const method = String(config.method || 'GET').toUpperCase();
  const response = await client({
    url: config.url,
    method,
    data: method === 'GET' ? undefined : (config.data || undefined),
    params: config.params || (method === 'GET' ? config.data || undefined : undefined),
    withAuth: config.withAuth,
    timeout: config.timeout || REQUEST_TIMEOUT,
  });

  const payload = response.data || {};
  if (response.status >= 200 && response.status < 300 && payload.code === 0) {
    return payload.data;
  }

  throw new Error(payload.message || '请求失败');
}
