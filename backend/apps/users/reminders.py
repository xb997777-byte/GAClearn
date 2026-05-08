import os

import requests
from django.utils import timezone

from apps.plans.services import get_current_plan, get_or_create_today_task
from .models import UserSetting
from .wechat import get_access_token


SUBSCRIBE_SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/subscribe/send"


def _minute_delta(now, reminder_time):
    target_minutes = reminder_time.hour * 60 + reminder_time.minute
    current_minutes = now.hour * 60 + now.minute
    return abs(current_minutes - target_minutes)


def _should_send_now(setting, now, tolerance_minutes):
    if setting.reminder_subscription_status != "accepted":
        return False
    if not (setting.reminder_template_ids or []):
        return False
    if _minute_delta(now, setting.reminder_time) > tolerance_minutes:
        return False
    if setting.last_reminder_sent_at and timezone.localtime(setting.last_reminder_sent_at).date() == now.date():
        return False
    return True


def _build_message_data(setting):
    user = setting.user
    plan = get_current_plan(user)
    if plan:
      task = get_or_create_today_task(user, plan)
      focus_text = f"{plan.book.name} {max(task.new_word_target - task.learned_count, 0)}个新词"
    else:
      focus_text = "先创建今日学习计划"

    thing_key = os.getenv("WECHAT_REMINDER_THING_KEY", "thing1")
    time_key = os.getenv("WECHAT_REMINDER_TIME_KEY", "time2")
    phrase_key = os.getenv("WECHAT_REMINDER_PHRASE_KEY", "phrase3")
    return {
        thing_key: {"value": focus_text[:20]},
        time_key: {"value": setting.reminder_time.strftime("%H:%M")},
        phrase_key: {"value": "记得开始今天的英语学习"},
    }


def _send_subscribe_message(openid, template_id, page, data, miniprogram_state="formal"):
    access_token = get_access_token()
    response = requests.post(
        f"{SUBSCRIBE_SEND_URL}?access_token={access_token}",
        json={
            "touser": openid,
            "template_id": template_id,
            "page": page,
            "miniprogram_state": miniprogram_state,
            "lang": "zh_CN",
            "data": data,
        },
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errcode"):
        raise ValueError(payload.get("errmsg") or "wechat subscribe send failed")
    return payload


def dispatch_due_reminders(dry_run=True, tolerance_minutes=20):
    now = timezone.localtime()
    page = os.getenv("WECHAT_REMINDER_PAGE", "pages/home/index")
    miniprogram_state = os.getenv("WECHAT_MINIPROGRAM_STATE", "formal")
    queryset = UserSetting.objects.select_related("user").all()
    results = []
    for setting in queryset:
        if not _should_send_now(setting, now, tolerance_minutes):
            continue
        template_id = (setting.reminder_template_ids or [None])[0]
        if not template_id:
            continue
        data = _build_message_data(setting)
        item = {
            "user_id": setting.user_id,
            "openid": setting.user.openid,
            "template_id": template_id,
            "data": data,
            "page": page,
            "status": "preview" if dry_run else "sent",
        }
        if not dry_run:
            _send_subscribe_message(setting.user.openid, template_id, page, data, miniprogram_state=miniprogram_state)
            setting.last_reminder_sent_at = timezone.now()
            setting.save(update_fields=["last_reminder_sent_at", "updated_at"])
        results.append(item)
    return results
