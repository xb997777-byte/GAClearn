from django.utils import timezone

from .models import LoginToken, UserSetting, WxUser
from .wechat import exchange_code_for_session, should_use_mock_login


def ensure_user_setting(user):
    setting, _ = UserSetting.objects.get_or_create(user=user)
    return setting


def serialize_setting(setting):
    return {
        "daily_target": setting.daily_target,
        "reminder_time": setting.reminder_time.strftime("%H:%M:%S"),
        "auto_play_audio": setting.auto_play_audio,
        "speech_speed": float(setting.speech_speed or 1.0),
        "review_enabled": setting.review_enabled,
        "theme_id": setting.theme_id,
        "custom_theme": setting.custom_theme or {},
        "cefr_level": setting.cefr_level,
        "placement_score": float(setting.placement_score or 0),
        "placement_completed_at": setting.placement_completed_at,
        "reminder_subscription_status": setting.reminder_subscription_status,
        "reminder_template_ids": setting.reminder_template_ids or [],
        "last_reminder_sent_at": setting.last_reminder_sent_at,
        "personalized_rag_enabled": setting.personalized_rag_enabled,
        "personalized_rag_status": setting.personalized_rag_status,
        "personalized_rag_chunk_count": int(setting.personalized_rag_chunk_count or 0),
        "personalized_rag_updated_at": setting.personalized_rag_updated_at,
        "personalized_rag_last_error": setting.personalized_rag_last_error,
    }


def serialize_user(user):
    return {
        "id": user.id,
        "openid": user.openid,
        "unionid": user.unionid,
        "nickname": user.nickname,
        "avatar_url": user.avatar_url,
        "gender": user.gender,
        "status": user.status,
        "last_login_at": user.last_login_at,
        "settings": serialize_setting(ensure_user_setting(user)),
    }


def _upsert_user(openid, unionid="", nickname="", avatar_url="", gender=""):
    defaults = {
        "unionid": unionid or "",
        "nickname": nickname or f"user_{openid[-6:]}",
        "avatar_url": avatar_url or "",
        "gender": gender or "",
    }
    user, created = WxUser.objects.get_or_create(openid=openid, defaults=defaults)
    if unionid:
        user.unionid = unionid
    if nickname:
        user.nickname = nickname
    if avatar_url:
        user.avatar_url = avatar_url
    if gender:
        user.gender = gender
    user.last_login_at = timezone.now()
    user.save()
    return user, created


def login_with_code(code, nickname="", avatar_url="", gender=""):
    code = (code or "").strip()
    if not code:
        raise ValueError("code is required")

    use_mock = should_use_mock_login(code)
    login_mode = "mock" if use_mock else "real"
    login_note = "dev mode mock login; replace with real wechat code2session in production"
    unionid = ""

    if use_mock:
        openid = f"mock_{code}"
    else:
        session_data = exchange_code_for_session(code)
        openid = session_data["openid"]
        unionid = session_data.get("unionid", "")
        login_note = "wechat code2session login success"

    user, created = _upsert_user(
        openid=openid,
        unionid=unionid,
        nickname=nickname,
        avatar_url=avatar_url,
        gender=gender,
    )

    token_obj = LoginToken.issue_for_user(user)
    return {
        "token": token_obj.token,
        "expired_at": token_obj.expired_at,
        "is_new_user": created,
        "user": serialize_user(user),
        "login_mode": login_mode,
        "login_note": login_note,
    }


def update_profile(user, data):
    for field in ("nickname", "avatar_url", "gender"):
        if field in data:
            setattr(user, field, data[field])
    user.save()
    return serialize_user(user)


def refresh_token(user, current_token=None):
    if current_token is not None:
        current_token.is_active = False
        current_token.save(update_fields=["is_active", "updated_at"])
    token_obj = LoginToken.issue_for_user(user)
    return {
        "token": token_obj.token,
        "expired_at": token_obj.expired_at,
    }
