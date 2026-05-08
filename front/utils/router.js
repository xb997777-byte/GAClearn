const store = require('../store/app-store');

const AI_CENTER_PATH = '/pages/ai-center/index';

function isAiCenterUrl(url) {
  return typeof url === 'string' && url.indexOf(AI_CENTER_PATH) === 0;
}

function parseAiCenterIntent(url) {
  if (!isAiCenterUrl(url)) {
    return null;
  }
  const queryString = url.split('?')[1] || '';
  const params = {};
  queryString.split('&').forEach((pair) => {
    if (!pair) {
      return;
    }
    const [rawKey, rawValue = ''] = pair.split('=');
    const key = decodeURIComponent(rawKey || '').trim();
    if (!key) {
      return;
    }
    params[key] = decodeURIComponent(rawValue || '');
  });
  const intent = {
    tab: params.tab || '',
    workspace: params.workspace || '',
    query: params.query || '',
    sentence: params.sentence || '',
    question: params.question || ''
  };
  return Object.values(intent).some(Boolean) ? intent : {};
}

function go(url) {
  if (isAiCenterUrl(url)) {
    store.setAiCenterIntent(parseAiCenterIntent(url));
    wx.switchTab({ url: AI_CENTER_PATH });
    return;
  }
  wx.navigateTo({ url });
}

function back(delta = 1) {
  wx.navigateBack({ delta });
}

function tab(url) {
  wx.switchTab({ url });
}

function relaunch(url) {
  if (isAiCenterUrl(url)) {
    store.setAiCenterIntent(parseAiCenterIntent(url));
    wx.reLaunch({ url: AI_CENTER_PATH });
    return;
  }
  wx.reLaunch({ url });
}

module.exports = {
  go,
  back,
  tab,
  relaunch,
};
