from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from apps.ai.agent_runtime import list_stale_runs, recover_stale_runs


class Command(BaseCommand):
    help = "Recover stale queued/running AI agent runs back into the standard runtime."

    def add_arguments(self, parser):
        parser.add_argument("--feature", type=str, default="", help="Optional feature_type filter.")
        parser.add_argument("--limit", type=int, default=100, help="Maximum stale runs to inspect.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            dest="dry_run",
            help="Only list stale runs without requeueing them.",
        )
        parser.add_argument(
            "--no-dispatch",
            action="store_true",
            dest="no_dispatch",
            help="Mark stale runs back to queued but do not dispatch them to worker.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="as_json",
            help="Print result as JSON.",
        )

    def handle(self, *args, **options):
        feature_type = (options.get("feature") or "").strip() or None
        limit = max(int(options.get("limit") or 100), 1)
        if options.get("dry_run"):
            stale_runs = list_stale_runs(feature_type=feature_type, limit=limit)
            payload = {
                "dry_run": True,
                "count": len(stale_runs),
                "runs": [
                    {
                        "run_id": item.public_id,
                        "feature_type": item.feature_type,
                        "status": item.status,
                        "queue_name": item.queue_name,
                    }
                    for item in stale_runs
                ],
            }
        else:
            recovered = recover_stale_runs(
                feature_type=feature_type,
                limit=limit,
                dispatch=not bool(options.get("no_dispatch")),
            )
            payload = {
                "dry_run": False,
                "count": len(recovered),
                "runs": recovered,
            }

        if options.get("as_json"):
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
            return

        if payload["count"] <= 0:
            self.stdout.write(self.style.SUCCESS("No stale AI runs found."))
            return

        summary = "Found" if payload["dry_run"] else "Recovered"
        self.stdout.write(self.style.WARNING(f"{summary} {payload['count']} stale AI runs."))
        for item in payload["runs"]:
            self.stdout.write(
                f"- {item['run_id']} [{item['feature_type']}] {item['status']} queue={item.get('queue_name') or ''}"
            )
