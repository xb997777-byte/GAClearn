import hashlib
import json
import os
from datetime import timedelta
from time import monotonic

from django.db.models import Count, Q
from django.utils import timezone

from .models import AIRequestLog, AIResponseCache


DEFAULT_RATE_LIMIT = int(os.getenv("AI_RATE_LIMIT_PER_HOUR", "80") or 80)
DEFAULT_CACHE_TTL_SECONDS = int(os.getenv("AI_CACHE_TTL_SECONDS", "1800") or 1800)


def normalize_payload(payload):
    return json.loads(json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, default=str))


def make_cache_key(feature_type, payload, user_id=None):
    normalized = normalize_payload(payload)
    raw = json.dumps(
        {"feature_type": feature_type, "user_id": user_id or 0, "payload": normalized},
        ensure_ascii=False,
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached_response(feature_type, payload, user_id=None):
    cache_key = make_cache_key(feature_type, payload, user_id=user_id)
    cached = (
        AIResponseCache.objects.filter(
            feature_type=feature_type,
            cache_key=cache_key,
            expires_at__gt=timezone.now(),
        )
        .only("id", "response_payload", "hit_count")
        .first()
    )
    if not cached:
        return None, cache_key
    cached.hit_count += 1
    cached.last_hit_at = timezone.now()
    cached.save(update_fields=["hit_count", "last_hit_at", "updated_at"])
    data = dict(cached.response_payload or {})
    data.setdefault("ai_observability", {})
    data["ai_observability"].update(
        {
            "cache_key": cache_key,
            "cache_hit": True,
            "cached_at": cached.updated_at,
        }
    )
    return data, cache_key


def set_cached_response(feature_type, payload, response_payload, ttl_seconds=None, user_id=None):
    cache_key = make_cache_key(feature_type, payload, user_id=user_id)
    normalized_payload = normalize_payload(payload)
    expires_at = timezone.now() + timedelta(seconds=ttl_seconds or DEFAULT_CACHE_TTL_SECONDS)
    cache, _ = AIResponseCache.objects.update_or_create(
        cache_key=cache_key,
        defaults={
            "feature_type": feature_type,
            "request_hash": cache_key,
            "response_payload": normalize_payload(response_payload),
            "expires_at": expires_at,
        },
    )
    return cache


def check_rate_limit(user, feature_type, limit=None, window_minutes=60):
    if not user:
        return {"allowed": True, "limit": limit or DEFAULT_RATE_LIMIT, "used": 0}
    limit = int(limit or DEFAULT_RATE_LIMIT)
    since = timezone.now() - timedelta(minutes=window_minutes)
    used = AIRequestLog.objects.filter(
        user=user,
        feature_type=feature_type,
        created_at__gte=since,
    ).exclude(status="rate_limited").count()
    return {
        "allowed": used < limit,
        "limit": limit,
        "used": used,
        "remaining": max(limit - used, 0),
        "window_minutes": window_minutes,
    }


def log_ai_request(
    *,
    user,
    feature_type,
    endpoint="",
    request_payload=None,
    response_payload=None,
    status="success",
    cache_key="",
    cache_hit=False,
    latency_ms=0,
    prompt_version="",
    model_name="",
    error_message="",
):
    return AIRequestLog.objects.create(
        user=user,
        feature_type=feature_type,
        endpoint=endpoint,
        request_payload=normalize_payload(request_payload),
        response_payload=normalize_payload(response_payload),
        status=status,
        cache_key=cache_key,
        cache_hit=cache_hit,
        latency_ms=max(int(latency_ms or 0), 0),
        prompt_version=prompt_version,
        model_name=model_name,
        error_message=str(error_message or "")[:2000],
    )


def run_observed_feature(
    *,
    user,
    feature_type,
    endpoint,
    request_payload,
    producer,
    use_cache=True,
    cache_ttl_seconds=None,
    rate_limit=None,
):
    started_at = monotonic()
    current_user_id = getattr(user, "id", None)
    cached, cache_key = (None, make_cache_key(feature_type, request_payload, user_id=current_user_id))
    rate_status = check_rate_limit(user, feature_type, limit=rate_limit)
    if not rate_status["allowed"]:
        response = {
            "rate_limit": rate_status,
            "message": "AI 请求过于频繁，请稍后再试。",
        }
        log_ai_request(
            user=user,
            feature_type=feature_type,
            endpoint=endpoint,
            request_payload=request_payload,
            response_payload=response,
            status="rate_limited",
            cache_key=cache_key,
            latency_ms=int((monotonic() - started_at) * 1000),
        )
        raise ValueError("AI 请求过于频繁，请稍后再试")

    if use_cache:
        cached, cache_key = get_cached_response(feature_type, request_payload, user_id=current_user_id)
        if cached:
            latency_ms = int((monotonic() - started_at) * 1000)
            cached.setdefault("ai_observability", {})
            cached["ai_observability"].update(
                {
                    "latency_ms": latency_ms,
                    "endpoint": endpoint,
                    "status": "success",
                }
            )
            log_ai_request(
                user=user,
                feature_type=feature_type,
                endpoint=endpoint,
                request_payload=request_payload,
                response_payload=cached,
                cache_key=cache_key,
                cache_hit=True,
                latency_ms=latency_ms,
                prompt_version=(cached.get("ai_strategy") or {}).get("prompt_version", ""),
                model_name=(cached.get("ai_strategy") or {}).get("model_name", ""),
            )
            return cached

    try:
        response = producer()
        latency_ms = int((monotonic() - started_at) * 1000)
        response.setdefault("ai_observability", {})
        response["ai_observability"].update(
            {
                "cache_key": cache_key,
                "cache_hit": False,
                "rate_limit": rate_status,
                "latency_ms": latency_ms,
                "endpoint": endpoint,
                "status": "success",
                "prompt_version": (response.get("ai_strategy") or {}).get("prompt_version", ""),
                "model_name": (response.get("ai_strategy") or {}).get("model_name", ""),
            }
        )
        if use_cache:
            set_cached_response(
                feature_type,
                request_payload,
                response,
                ttl_seconds=cache_ttl_seconds,
                user_id=current_user_id,
            )
        log_ai_request(
            user=user,
            feature_type=feature_type,
            endpoint=endpoint,
            request_payload=request_payload,
            response_payload=response,
            status="success",
            cache_key=cache_key,
            latency_ms=latency_ms,
            prompt_version=(response.get("ai_strategy") or {}).get("prompt_version", ""),
            model_name=(response.get("ai_strategy") or {}).get("model_name", ""),
        )
        return response
    except Exception as exc:
        log_ai_request(
            user=user,
            feature_type=feature_type,
            endpoint=endpoint,
            request_payload=request_payload,
            response_payload={},
            status="failed",
            cache_key=cache_key,
            latency_ms=int((monotonic() - started_at) * 1000),
            error_message=str(exc),
        )
        raise


def build_observability_summary(user):
    now = timezone.now()
    day_start = now - timedelta(days=1)
    week_start = now - timedelta(days=7)
    logs = AIRequestLog.objects.filter(user=user)
    recent_logs = logs.order_by("-id")[:20]
    by_feature = (
        logs.filter(created_at__gte=week_start)
        .values("feature_type")
        .annotate(total=Count("id"), cache_hits=Count("id", filter=Q(cache_hit=True)))
        .order_by("-total")[:12]
    )
    runtime_path_counter = {
        "langgraph": 0,
        "langchain_explicit": 0,
        "mcp_tool": 0,
        "chroma": 0,
        "personalized_rag": 0,
        "fallback": 0,
    }
    recent_payload_logs = logs.filter(created_at__gte=week_start).only("response_payload").order_by("-id")[:120]
    for item in recent_payload_logs:
        response_payload = item.response_payload or {}
        feature_runtime = response_payload.get("feature_runtime") or {}
        tags = feature_runtime.get("tags") or []
        for key in runtime_path_counter.keys():
            if key in tags:
                runtime_path_counter[key] += 1
    status_counter = CounterLike(logs.filter(created_at__gte=week_start).values_list("status", flat=True))
    cache_count = AIResponseCache.objects.filter(expires_at__gt=now).count()
    return {
        "window": {"daily_since": day_start, "weekly_since": week_start},
        "totals": {
            "today_requests": logs.filter(created_at__gte=day_start).count(),
            "week_requests": logs.filter(created_at__gte=week_start).count(),
            "active_cache_items": cache_count,
        },
        "status_summary": dict(status_counter),
        "prompt_versions": list(
            logs.filter(created_at__gte=week_start)
            .exclude(prompt_version="")
            .values("prompt_version")
            .annotate(total=Count("id"))
            .order_by("-total", "prompt_version")[:12]
        ),
        "model_summary": list(
            logs.filter(created_at__gte=week_start)
            .exclude(model_name="")
            .values("model_name")
            .annotate(total=Count("id"))
            .order_by("-total", "model_name")[:12]
        ),
        "feature_summary": [
            {
                "feature_type": item["feature_type"],
                "total": item["total"],
                "cache_hits": item["cache_hits"],
            }
            for item in by_feature
        ],
        "runtime_path_summary": [
            {
                "path": key,
                "total": runtime_path_counter[key],
            }
            for key in ["langgraph", "langchain_explicit", "mcp_tool", "chroma", "personalized_rag", "fallback"]
        ],
        "recent_logs": [
            {
                "id": item.id,
                "feature_type": item.feature_type,
                "status": item.status,
                "cache_hit": item.cache_hit,
                "latency_ms": item.latency_ms,
                "endpoint": item.endpoint,
                "prompt_version": item.prompt_version,
                "model_name": item.model_name,
                "created_at": item.created_at,
                "error_message": item.error_message,
            }
            for item in recent_logs
        ],
    }


def CounterLike(values):
    counter = {}
    for value in values:
        counter[value] = counter.get(value, 0) + 1
    return counter
