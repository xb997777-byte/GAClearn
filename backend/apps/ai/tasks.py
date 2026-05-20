from __future__ import annotations

from celery import shared_task
from django.db import close_old_connections

from .agent_runtime import fail_run, recover_stale_runs
from .runtime_registry import execute_registered_run


@shared_task(name="apps.ai.tasks.execute_agent_run_task")
def execute_agent_run_task(run_public_id: str) -> dict:
    close_old_connections()
    from .models import AIAsyncRun

    run = AIAsyncRun.objects.select_related("user").filter(public_id=run_public_id).first()
    if not run:
        return {"ok": False, "message": "run not found"}
    try:
        execute_registered_run(run)
    except Exception as exc:  # pragma: no cover
        fail_run(run, str(exc), request_payload=run.request_payload, retryable=True)
        raise
    finally:
        close_old_connections()
    return {"ok": True, "run_id": run_public_id}


@shared_task(name="apps.ai.tasks.recover_stale_agent_runs_task")
def recover_stale_agent_runs_task(limit: int = 20) -> dict:
    close_old_connections()
    try:
        recovered = recover_stale_runs(limit=max(int(limit or 20), 1), dispatch=True)
        return {
            "ok": True,
            "recovered_count": len(recovered),
            "runs": recovered,
        }
    finally:
        close_old_connections()
