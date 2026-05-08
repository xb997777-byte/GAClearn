import os

import requests


CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"
ACCESS_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"


def get_wechat_login_mode():
    mode = os.getenv("WECHAT_LOGIN_MODE", "auto").strip().lower()
    return mode if mode in {"auto", "mock", "real"} else "auto"


def has_wechat_credentials():
    return bool(os.getenv("WECHAT_APP_ID", "").strip()) and bool(os.getenv("WECHAT_APP_SECRET", "").strip())


def should_use_mock_login(code):
    code = (code or "").strip()
    if code.startswith("debug_"):
        return True

    mode = get_wechat_login_mode()
    if mode == "mock":
        return True
    if mode == "real":
        return False
    return not has_wechat_credentials()


def exchange_code_for_session(code):
    app_id = os.getenv("WECHAT_APP_ID", "").strip()
    app_secret = os.getenv("WECHAT_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise ValueError("wechat app credentials are not configured")

    response = requests.get(
        CODE2SESSION_URL,
        params={
            "appid": app_id,
            "secret": app_secret,
            "js_code": (code or "").strip(),
            "grant_type": "authorization_code",
        },
        timeout=8,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("errcode"):
        raise ValueError(data.get("errmsg") or "wechat code2session failed")
    if not data.get("openid"):
        raise ValueError("openid missing from wechat login response")
    return data


def list_subscribe_template_ids():
    raw_value = os.getenv("WECHAT_SUBSCRIBE_TEMPLATE_IDS", "").strip()
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def get_access_token():
    app_id = os.getenv("WECHAT_APP_ID", "").strip()
    app_secret = os.getenv("WECHAT_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        raise ValueError("wechat app credentials are not configured")

    response = requests.get(
        ACCESS_TOKEN_URL,
        params={
            "grant_type": "client_credential",
            "appid": app_id,
            "secret": app_secret,
        },
        timeout=8,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("errcode"):
        raise ValueError(data.get("errmsg") or "wechat access token request failed")
    token = data.get("access_token", "").strip()
    if not token:
        raise ValueError("wechat access token missing")
    return token
