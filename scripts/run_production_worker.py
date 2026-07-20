"""Run the hosted UIIP worker process."""

from pathlib import Path
import json
import os
import signal
import sys
from threading import Event

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.portfolio import preview_portfolio_csv
from foundation.production.providers import AlphaVantageProvider, FREDProvider
from foundation.production.worker import HandlerRegistry, HostedWorker, WorkerSettings, build_job_repository

stop = Event()
for signal_number in (signal.SIGINT, signal.SIGTERM):
    signal.signal(signal_number, lambda *_: stop.set())

handlers = HandlerRegistry()


def validate_portfolio(job):
    path = Path(str(job.payload.get("path", os.getenv("UIIP_PORTFOLIO_CSV", "portfolio_holdings.csv"))))
    report = preview_portfolio_csv(path)
    if not report.valid:
        raise ValueError(f"portfolio validation failed with {len(report.errors)} error(s)")
    print(json.dumps({"event": "portfolio_validated", "job_id": job.job_id, "positions": len(report.positions), "fingerprint": report.fingerprint}), flush=True)


def check_providers(job):
    symbol = str(job.payload.get("symbol", "SPY"))
    series = str(job.payload.get("series_id", "MORTGAGE30US"))
    quote, observation = AlphaVantageProvider().quote(symbol), FREDProvider().latest(series)
    print(json.dumps({"event": "providers_checked", "job_id": job.job_id, "symbol": quote.symbol, "series_id": observation.series_id}), flush=True)


handlers.register("portfolio_validate", validate_portfolio)
handlers.register("provider_check", check_providers)
worker = HostedWorker(build_job_repository(), handlers, WorkerSettings.from_environment())
worker.run(stop)
