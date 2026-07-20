"""Enqueue configured recurring jobs without duplicate schedule buckets."""

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
from time import sleep

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.worker import RecurringSchedule, build_job_repository, enqueue_schedule

repository = build_job_repository()
definitions = json.loads(os.getenv("UIIP_SCHEDULES_JSON", "[]"))
schedules = tuple(RecurringSchedule(
    str(item["schedule_id"]), str(item["job_type"]), timedelta(seconds=float(item["interval_seconds"])), item.get("payload", {}),
) for item in definitions)
poll = float(os.getenv("UIIP_SCHEDULER_POLL_SECONDS", "30"))

while True:
    now = datetime.now(timezone.utc)
    for schedule in schedules:
        job = enqueue_schedule(repository, schedule, now)
        print(json.dumps({"event": "schedule_enqueued", "schedule_id": schedule.schedule_id, "job_id": job.job_id}), flush=True)
    sleep(poll)
