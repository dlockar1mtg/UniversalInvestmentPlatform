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

def net_worth_snapshot(job):
    """Keep this month's net-worth row current, so the history has every month even when the dashboard is closed."""
    dsn = os.environ["UIIP_DATABASE_URL"]
    from foundation.presentation.read_api import PresentationReadRepository
    from foundation.production.external_account_performance import PostgresExternalAccountPerformanceRepository
    from foundation.production.household_plan import PostgresHouseholdPlanRepository
    from foundation.production.manual_holdings import PostgresManualHoldingRepository
    from foundation.production.net_worth import NetWorthHistory, capture
    from foundation.production.transaction_persistence import PostgresTransactionRepository
    history = NetWorthHistory.from_dsn(dsn); history.initialize()
    out = capture(history, transactions=PostgresTransactionRepository.from_dsn(dsn), presentation=PresentationReadRepository.from_dsn(dsn),
                  manual=PostgresManualHoldingRepository.from_dsn(dsn), external=PostgresExternalAccountPerformanceRepository.from_dsn(dsn),
                  plans=PostgresHouseholdPlanRepository.from_dsn(dsn))
    print(json.dumps({"net_worth_month": out["snapshot"]["month"], "status": out["status"], "seeded_months": out["seeded_months"],
                      "missing": out["snapshot"]["missing"]}))   # amounts stay out of the public log

handlers.register("provider_check", provider_check)
handlers.register("portfolio_validate", portfolio_validate)
handlers.register("net_worth_snapshot", net_worth_snapshot)
worker = HostedWorker(repository, handlers, WorkerSettings.from_environment())
result = run_scheduled_cycle(repository, schedules, worker, maximum_jobs=int(os.getenv("UIIP_ONE_SHOT_MAX_JOBS", "20")))
print(json.dumps(result.document(), sort_keys=True))
raise SystemExit(1 if result.failed else 0)
