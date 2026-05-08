const { API_PREFIX, BASE_URL, REQUEST_TIMEOUT } = require('../config/env');
const store = require('../store/app-store');

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

  if (snapshot.token && config.withAuth !== false) {
    headers.Authorization = `Token ${snapshot.token}`;
  }

  let response;
  try {
    response = await requestByWx({
      url: `${BASE_URL}${API_PREFIX}${config.url}`,
      method: config.method || 'GET',
      data: config.data || {},
      header: headers,
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

  if (response.statusCode === 401 || response.statusCode === 403) {
    console.warn('[request] auth error response', response.data);
    handleAuthExpired();
    throw buildRequestError((response.data && response.data.message) || '登录已失效，请重新登录', {
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
  throw buildRequestError(responseData.message || fallbackMessage, {
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
