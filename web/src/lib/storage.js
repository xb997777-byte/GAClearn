export function safeGet(key, fallback = null) {
  try {
    const raw = window.localStorage.getItem(key);
    if (!raw) {
      return fallback;
    }
    return JSON.parse(raw);
  } catch (error) {
    return fallback;
  }
}

export function safeSet(key, value) {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    // ignore
  }
}

export function safeRemove(key) {
  try {
    window.localStorage.removeItem(key);
  } catch (error) {
    // ignore
  }
}
