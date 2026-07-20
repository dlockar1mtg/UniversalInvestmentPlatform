"""Free-staging runtime composition for Render, Neon, and bounded jobs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from time import sleep
from typing import Callable, Mapping, Sequence

from .worker import HostedWorker, RecurringSchedule, enqueue_schedule


@dataclass(frozen=True)
class FreeStagingSettings:
    port: int
    external_hostname: str
    database_url: str
    maximum_jobs: int = 20

    def __post_init__(self):
        if not 1 <= self.port <= 65535 or not self.external_hostname.strip():
            raise ValueError("valid port and Render external hostname are required")
        if not self.database_url.startswith(("postgresql://", "postgres://")):
            raise ValueError("free staging requires PostgreSQL")
        if "sslmode=require" not in self.database_url:
            raise ValueError("Neon connection must require TLS")
        if not 1 <= self.maximum_jobs <= 100:
            raise ValueError("maximum jobs must be between 1 and 100")

    @classmethod
    def from_environment(cls, values: Mapping[str, str] = os.environ):
        hostname = values.get("RENDER_EXTERNAL_HOSTNAME", values.get("UIIP_ALLOWED_HOSTS", "")).strip()
        return cls(int(values.get("PORT", values.get("UIIP_HTTP_PORT", "8000"))), hostname,
                   values.get("UIIP_DATABASE_URL", ""), int(values.get("UIIP_ONE_SHOT_MAX_JOBS", "20")))

    def application_environment(self) -> dict[str, str]:
        return {
            "UIIP_ENVIRONMENT": "staging", "UIIP_DATABASE_BACKEND": "postgresql",
            "UIIP_JOB_DATABASE_BACKEND": "postgresql", "UIIP_DATABASE_URL": self.database_url,
            "UIIP_REQUIRE_HTTPS": "true", "UIIP_ALLOWED_HOSTS": self.external_hostname,
            "UIIP_HTTP_HOST": "0.0.0.0", "UIIP_HTTP_PORT": str(self.port),
        }


class RetryingConnectionFactory:
    def __init__(self, dsn: str, connector: Callable[[str], object], attempts: int = 3,
                 delay_seconds: float = 0.25, pause: Callable[[float], None] = sleep):
        if attempts < 1 or delay_seconds < 0:
            raise ValueError("positive attempts and nonnegative delay are required")
        self.dsn, self.connector, self.attempts, self.delay_seconds, self.pause = dsn, connector, attempts, delay_seconds, pause

    def __call__(self):
        last_error = None
        for attempt in range(self.attempts):
            try:
                return self.connector(self.dsn)
            except Exception as exc:
                last_error = exc
                if attempt + 1 < self.attempts:
                    self.pause(self.delay_seconds * (attempt + 1))
        raise last_error


def build_neon_repositories(settings: FreeStagingSettings, connector=None):
    """Build both repository contracts on a cold-start-tolerant connection factory."""
    if connector is None:
        import psycopg
        connector = psycopg.connect
    from .postgres import PostgresProductionRepository
    from .postgres_jobs import PostgresJobRepository
    factory = RetryingConnectionFactory(settings.database_url, connector)
    production, jobs = PostgresProductionRepository(factory), PostgresJobRepository(factory)
    production.initialize()
    jobs.initialize()
    return production, jobs


@dataclass(frozen=True)
class ScheduledCycleResult:
    started_at: datetime
    enqueued_job_ids: tuple[str, ...]
    processed: int
    failed: int
    exhausted: bool

    def document(self):
        return {"enqueued_job_ids": list(self.enqueued_job_ids), "exhausted": self.exhausted,
                "failed": self.failed, "processed": self.processed, "started_at": self.started_at.isoformat()}


def run_scheduled_cycle(repository, schedules: Sequence[RecurringSchedule], worker: HostedWorker,
                        now: datetime | None = None, maximum_jobs: int = 20) -> ScheduledCycleResult:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or not 1 <= maximum_jobs <= 100:
        raise ValueError("aware time and bounded maximum jobs are required")
    enqueued = tuple(enqueue_schedule(repository, schedule, now).job_id for schedule in sorted(schedules, key=lambda item: item.schedule_id))
    before = worker.health
    exhausted = True
    for _ in range(maximum_jobs):
        if worker.run_once(now) is None:
            exhausted = False
            break
    after = worker.health
    return ScheduledCycleResult(now, enqueued, after.processed - before.processed, after.failed - before.failed, exhausted)
