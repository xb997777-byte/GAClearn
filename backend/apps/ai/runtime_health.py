from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from celery import current_app
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


HEALTH_CACHE_KEY = "ai:runtime_health_snapshot"
HEALTH_CACHE_TTL_SECONDS = max(int(getattr(settings, "AI_RUNTIME_HEALTH_CACHE_TTL_SECONDS", 6) or 6), 1)


def celery_worker_reachable(timeout: float = 0.8) -> bool:
    try:
        inspector = current_app.control.inspect(timeout=timeout)
        ping_result = inspector.ping() or {}
        return bool(ping_result)
    except Exception:
        return False


def inspect_celery_runtime(timeout: float = 0.8) -> Dict[str, Any]:
    try:
        inspector = current_app.control.inspect(timeout=timeout)
        ping_result = inspector.ping() or {}
        active_queues = inspector.active_queues() or {}
        workers = sorted(set(list(ping_result.keys()) + list(active_queues.keys())))
        observed_queues = set()
        for queue_defs in active_queues.values():
            for queue_info in queue_defs or []:
                queue_name = str((queue_info or {}).get("name") or "").strip()
                if queue_name:
                    observed_queues.add(queue_name)
        return {
            "worker_healthy": bool(ping_result),
            "workers": workers,
            "observed_queues": sorted(observed_queues),
        }
    except Exception:
        return {
            "worker_healthy": False,
            "workers": [],
            "observed_queues": [],
        }


def get_runtime_health() -> Dict[str, Any]:
    from .agent_runtime import QUEUED_RUNTIME_FEATURES, build_runtime_kind, redis_reachable, list_stale_runs

    runtime_kind = build_runtime_kind()
    strict_runtime = runtime_kind == "celery"
    redis_ok = redis_reachable()
    inspection = inspect_celery_runtime() if strict_runtime and redis_ok else {"worker_healthy": False, "workers": [], "observed_queues": []}
    schema_health = get_ai_schema_health()
    cache_allowed = strict_runtime and redis_ok and schema_health["healthy"]
    if cache_allowed:
        cached = cache.get(HEALTH_CACHE_KEY)
        if cached:
            payload = dict(cached)
            payload["health_snapshot_age_ms"] = max(
                int((datetime.now().timestamp() - payload.pop("_cached_at_ts", datetime.now().timestamp())) * 1000),
                0,
            )
            payload["deep_health_stale"] = False
            return payload

    worker_ok = bool(inspection["worker_healthy"]) if strict_runtime else True
    observed_queues = inspection.get("observed_queues") or []
    queue_health = {
        settings.AI_AGENT_QUEUE_SHORT: worker_ok and (not observed_queues or settings.AI_AGENT_QUEUE_SHORT in observed_queues),
        settings.AI_AGENT_QUEUE_LONG: worker_ok and (not observed_queues or settings.AI_AGENT_QUEUE_LONG in observed_queues),
        settings.AI_AGENT_QUEUE_TOOLS: worker_ok and (not observed_queues or settings.AI_AGENT_QUEUE_TOOLS in observed_queues),
    }
    healthy = True
    degraded_reason = ""
    if strict_runtime:
        healthy = redis_ok and worker_ok
        if not redis_ok:
            degraded_reason = "Redis 不可达，标准 Agent 运行时不可用。"
        elif not worker_ok:
            degraded_reason = "Celery Worker 不可达，标准 Agent 运行时不可用。"
    if not schema_health["healthy"]:
        healthy = False
        degraded_reason = schema_health["degraded_reason"]
    stale_runs = list_stale_runs(limit=10) if strict_runtime else []
    payload = {
        "agent_runtime": runtime_kind,
        "worker_backend": "celery" if runtime_kind == "celery" else "legacy_thread",
        "strict_runtime": strict_runtime,
        "worker_required": strict_runtime,
        "worker_healthy": worker_ok if strict_runtime else True,
        "redis_reachable": redis_ok,
        "workers": inspection.get("workers", []) if strict_runtime else [],
        "observed_queues": observed_queues if strict_runtime else [],
        "queue_health": queue_health,
        "queued_features": QUEUED_RUNTIME_FEATURES,
        "resume_available": True,
        "approval_available": True,
        "auto_recover_enabled": bool(getattr(settings, "AI_AGENT_AUTO_RECOVER_ENABLED", False)),
        "auto_recover_limit": int(getattr(settings, "AI_AGENT_AUTO_RECOVER_LIMIT", 0) or 0),
        "auto_recover_every_seconds": int(getattr(settings, "AI_AGENT_AUTO_RECOVER_EVERY_SECONDS", 0) or 0),
        "stale_run_count": len(stale_runs),
        "stale_runs_preview": [
            {
                "run_id": item.public_id,
                "feature_type": item.feature_type,
                "status": item.status,
                "queue_name": item.queue_name,
            }
            for item in stale_runs[:5]
        ],
        "schema_healthy": schema_health["healthy"],
        "pending_migrations": schema_health["pending_migrations"],
        "healthy": healthy,
        "degraded_reason": degraded_reason,
        "checked_at": datetime.now().isoformat(),
        "health_snapshot_age_ms": 0,
        "deep_health_stale": False,
    }
    if cache_allowed:
        cache.set(
            HEALTH_CACHE_KEY,
            {
                **payload,
                "_cached_at_ts": datetime.now().timestamp(),
            },
            HEALTH_CACHE_TTL_SECONDS,
        )
    return payload


def assert_runtime_available_for_feature(feature_type: str) -> None:
    from .agent_runtime import QUEUED_RUNTIME_FEATURES

    if feature_type not in QUEUED_RUNTIME_FEATURES:
        return
    health = get_runtime_health()
    if health["strict_runtime"] and not health["healthy"]:
        raise RuntimeError(health["degraded_reason"] or "标准 Agent 运行时不可用。")


def get_ai_schema_health() -> Dict[str, Any]:
    try:
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes("ai")
        plan = executor.migration_plan(targets)
        pending = [
            f"{migration.app_label}.{migration.name}"
            for migration, backwards in plan
            if not backwards and migration.app_label == "ai"
        ]
    except Exception as exc:
        return {
            "healthy": False,
            "pending_migrations": [],
            "degraded_reason": f"AI 数据库迁移状态检查失败：{exc}",
        }

    if pending:
        return {
            "healthy": False,
            "pending_migrations": pending,
            "degraded_reason": f"AI 数据库迁移未完成：{', '.join(pending)}",
        }

    return {
        "healthy": True,
        "pending_migrations": [],
        "degraded_reason": "",
    }
