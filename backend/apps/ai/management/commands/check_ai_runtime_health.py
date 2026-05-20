from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.ai.runtime_health import get_runtime_health


class Command(BaseCommand):
    help = "Check strict AI agent runtime health for Redis, Celery workers, and queues."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Print full health payload as JSON.",
        )

    def handle(self, *args, **options):
        payload = get_runtime_health()
        if options.get("as_json"):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        healthy = bool(payload.get("healthy"))
        style = self.style.SUCCESS if healthy else self.style.WARNING
        self.stdout.write(style(f"AI runtime healthy: {healthy}"))
        self.stdout.write(f"runtime: {payload.get('agent_runtime')}")
        self.stdout.write(f"strict_runtime: {payload.get('strict_runtime')}")
        self.stdout.write(f"redis_reachable: {payload.get('redis_reachable')}")
        self.stdout.write(f"worker_healthy: {payload.get('worker_healthy')}")
        self.stdout.write(f"workers: {', '.join(payload.get('workers') or []) or '(none)'}")
        self.stdout.write(f"observed_queues: {', '.join(payload.get('observed_queues') or []) or '(none)'}")
        self.stdout.write(f"queue_health: {json.dumps(payload.get('queue_health') or {}, ensure_ascii=False)}")
        self.stdout.write(f"schema_healthy: {payload.get('schema_healthy')}")
        self.stdout.write(f"pending_migrations: {', '.join(payload.get('pending_migrations') or []) or '(none)'}")
        if payload.get("degraded_reason"):
            self.stdout.write(self.style.WARNING(f"degraded_reason: {payload['degraded_reason']}"))
