"""Run one idempotent, bounded free-staging schedule and worker cycle."""
from datetime import timedelta
import json, os
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))

from foundation.production.free_staging import FreeStagingSettings, build_neon_repositories, run_scheduled_cycle
from foundation.production.portfolio import preview_portfolio_csv
from foundation.production.providers import AlphaVantageProvider, FREDProvider
from foundation.production.worker import HandlerRegistry, HostedWorker, RecurringSchedule, WorkerSettings, build_job_repository

if os.getenv("UIIP_DATABASE_URL") and os.getenv("UIIP_ALLOWED_HOSTS", "github-actions"):
    settings = FreeStagingSettings(int(os.getenv("PORT", "8000")), os.getenv("UIIP_ALLOWED_HOSTS", "github-actions"), os.environ["UIIP_DATABASE_URL"], int(os.getenv("UIIP_ONE_SHOT_MAX_JOBS", "20")))
    _, repository = build_neon_repositories(settings)
else:
    repository = build_job_repository()
definitions = json.loads(os.getenv("UIIP_SCHEDULES_JSON", '[{"schedule_id":"providers-6h","job_type":"provider_check","interval_seconds":21600,"payload":{}}]'))
schedules = tuple(RecurringSchedule(str(item["schedule_id"]), str(item["job_type"]), timedelta(seconds=float(item["interval_seconds"])), item.get("payload", {})) for item in definitions)
handlers = HandlerRegistry()

def provider_check(job):
    AlphaVantageProvider().quote(str(job.payload.get("symbol", "SPY")))
    FREDProvider().latest(str(job.payload.get("series_id", "MORTGAGE30US")))

def portfolio_validate(job):
    report = preview_portfolio_csv(Path(str(job.payload.get("path", os.getenv("UIIP_PORTFOLIO_CSV", "portfolio_holdings.csv")))))
    if not report.valid: raise ValueError(f"portfolio validation failed with {len(report.errors)} error(s)")

handlers.register("provider_check", provider_check)
handlers.register("portfolio_validate", portfolio_validate)
worker = HostedWorker(repository, handlers, WorkerSettings.from_environment())
result = run_scheduled_cycle(repository, schedules, worker, maximum_jobs=int(os.getenv("UIIP_ONE_SHOT_MAX_JOBS", "20")))
print(json.dumps(result.document(), sort_keys=True))
raise SystemExit(1 if result.failed else 0)
