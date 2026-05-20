const { API_PREFIX, BASE_URL, REQUEST_TIMEOUT } = require('../config/env');
const store = require('../store/app-store');

let refreshPromise = null;

function isGetMethod(method) {
  return String(method || 'GET').toUpperCase() === 'GET';
}

function withQueryString(url, params = {}) {
  const source = params && typeof params === 'object' ? params : {};
  const entries = Object.keys(source)
    .filter((key) => source[key] !== undefined && source[key] !== null && source[key] !== '')
    .map((key) => `${encodeURIComponent(key)}=${encodeURIComponent(source[key])}`);
  if (!entries.length) {
    return url;
  }
  return `${url}${url.indexOf('?') >= 0 ? '&' : '?'}${entries.join('&')}`;
}

function requestByWx(options) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    wx.request({
      url: options.url,
      method: options.method || 'GET',
      data: options.data || {},
      timeout: options.timeout || REQUEST_TIMEOUT,
      header: options.header || {},
      success(response) {
        const duration = Date.now() - startedAt;
        console.info(`[request] ${options.method || 'GET'} ${options.url} -> ${response.statusCode} (${duration}ms)`);
        resolve(response);
      },
      fail(error) {
        const duration = Date.now() - startedAt;
        console.error(`[request] ${options.method || 'GET'} ${options.url} failed (${duration}ms)`, error);
        reject(error);
      }
    });
  });
}

function handleAuthExpired() {
  console.warn('[request] auth expired, clear local session and redirect to login');
  store.clearAuth();
  const pages = getCurrentPages();
  const currentRoute = pages.length ? `/${pages[pages.length - 1].route}` : '';
  if (currentRoute !== '/pages/login/index') {
    wx.reLaunch({ url: '/pages/login/index' });
  }
}

async function ensureRefreshedToken() {
  if (refreshPromise) {
    return refreshPromise;
  }
  const snapshot = store.getState();
  refreshPromise = requestByWx({
    url: `${BASE_URL}${API_PREFIX}/auth/refresh`,
    method: 'POST',
    data: {},
    header: snapshot.token ? { Authorization: `Token ${snapshot.token}` } : {},
    timeout: REQUEST_TIMEOUT
  })
    .then((response) => {
      if (!response || response.statusCode < 200 || response.statusCode >= 300 || !response.data || response.data.code !== 0) {
        const payload = (response && response.data) || {};
        throw buildRequestError(payload.detail || payload.message || 'token refresh failed', {
          code: (response && response.statusCode) || 'refresh_failed',
          response: payload
        });
      }
      const payload = response.data.data || {};
      store.setTokenMeta(payload.token, payload.expired_at || '');
      return payload.token || '';
    })
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

function buildRequestError(message, extras = {}) {
  const error = new Error(message);
  Object.keys(extras || {}).forEach((key) => {
    error[key] = extras[key];
  });
  return error;
}

async function request(config) {
  const snapshot = store.getState();
  const headers = Object.assign({}, config.header || {});
  const method = config.method || 'GET';

  if (snapshot.token && config.withAuth !== false) {
    headers.Authorization = `Token ${snapshot.token}`;
  }

  async function doRequest(useRefreshedToken = false) {
    const nextHeaders = Object.assign({}, headers);
    if (useRefreshedToken) {
      const refreshedToken = store.getState().token;
      if (refreshedToken && config.withAuth !== false) {
        nextHeaders.Authorization = `Token ${refreshedToken}`;
      }
    }
    try {
      return await requestByWx({
        url: `${BASE_URL}${API_PREFIX}${isGetMethod(method) ? withQueryString(config.url, config.params || config.data || {}) : config.url}`,
        method,
        data: isGetMethod(method) ? {} : (config.data || {}),
        header: nextHeaders,
        timeout: config.timeout
      });
    } catch (error) {
      const message = error && error.errMsg ? error.errMsg : 'network request failed';
      if (message.indexOf('timeout') > -1) {
        throw buildRequestError('请求超时，当前 AI 分析可能仍在生成中，请稍后重试', {
          code: 'timeout'
        });
      }
      throw buildRequestError(`网络请求失败：${message}`, {
        code: 'network'
      });
    }
  }

  let response = await doRequest(false);

  if ((response.statusCode === 401 || response.statusCode === 403) && config.withAuth !== false && config.retryOnAuthFailure !== false) {
    try {
      await ensureRefreshedToken();
      response = await doRequest(true);
    } catch (error) {
      console.warn('[request] token refresh failed', error);
      handleAuthExpired();
      throw buildRequestError((response.data && (response.data.detail || response.data.message)) || error.message || '登录已失效，请重新登录', {
        code: response.statusCode,
        response: response.data || null
      });
    }
  }

  if (response.statusCode === 401 || response.statusCode === 403) {
    console.warn('[request] auth error response', response.data);
    handleAuthExpired();
    throw buildRequestError((response.data && (response.data.detail || response.data.message)) || '登录已失效，请重新登录', {
      code: response.statusCode,
      response: response.data || null
    });
  }

  if (
    response.statusCode >= 200 &&
    response.statusCode < 300 &&
    response.data &&
    response.data.code === 0
  ) {
    return response.data.data;
  }

  if (response.statusCode === 404 && (config.url || '').indexOf('/ai/') === 0) {
    throw buildRequestError('当前后端还没有加载最新 AI 接口，请重启 Django 服务后再试', {
      code: 404,
      response: response.data || null
    });
  }

  if (response.statusCode === 404 && (config.url || '') === '/users/feedback') {
    throw buildRequestError('当前后端还没有加载反馈接口，请重启 Django 服务后再试', {
      code: 404,
      response: response.data || null
    });
  }

  console.error('[request] business error', {
    url: config.url,
    statusCode: response.statusCode,
    response: response.data
  });

  const responseData = response.data || {};
  const fallbackMessage =
    response.statusCode === 400 ? '请求参数错误'
      : response.statusCode >= 500 ? '服务暂时异常，请稍后重试'
        : '请求失败';
  throw buildRequestError(responseData.detail || responseData.message || fallbackMessage, {
    code: response.statusCode || responseData.code || 'business_error',
    response: responseData,
    data: responseData.data || null,
    fieldErrors: responseData.data && typeof responseData.data === 'object' && !Array.isArray(responseData.data)
      ? responseData.data
      : null
  });
}

module.exports = {
  request
};
