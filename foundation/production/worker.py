"""Hosted worker and recurring scheduling runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import socket
from threading import Event
from time import sleep
from typing import Callable, Mapping, Protocol

from .scheduling import RetryPolicy, ScheduledJob, SQLiteJobRepository


class JobRepository(Protocol):
    def initialize(self) -> None: ...
    def enqueue(self, job: ScheduledJob) -> ScheduledJob: ...
    def claim_due(self, now: datetime, worker_id: str, lease_duration: timedelta) -> ScheduledJob | None: ...
    def complete(self, job_id: str, worker_id: str) -> ScheduledJob: ...
    def fail(self, job_id: str, worker_id: str, now: datetime, error: str, policy: RetryPolicy) -> ScheduledJob: ...
    def recover_expired(self, now: datetime) -> tuple[str, ...]: ...


@dataclass(frozen=True)
class WorkerSettings:
    worker_id: str = field(default_factory=lambda: f"{socket.gethostname()}-{os.getpid()}")
    poll_interval: float = 5.0
    lease_duration: timedelta = timedelta(minutes=5)
    retry_policy: RetryPolicy = RetryPolicy()

    def __post_init__(self) -> None:
        if not self.worker_id.strip() or self.poll_interval <= 0 or self.lease_duration <= timedelta(0):
            raise ValueError("worker identity, positive poll interval, and lease duration are required")

    @classmethod
    def from_environment(cls, values: Mapping[str, str] = os.environ) -> "WorkerSettings":
        return cls(
            values.get("UIIP_WORKER_ID", f"{socket.gethostname()}-{os.getpid()}"),
            float(values.get("UIIP_WORKER_POLL_SECONDS", "5")),
            timedelta(seconds=float(values.get("UIIP_WORKER_LEASE_SECONDS", "300"))),
            RetryPolicy(int(values.get("UIIP_WORKER_MAX_ATTEMPTS", "3"))),
        )


class HandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[ScheduledJob], None]] = {}

    def register(self, job_type: str, handler: Callable[[ScheduledJob], None]) -> None:
        normalized = job_type.strip()
        if not normalized or normalized in self._handlers:
            raise ValueError("job type must be nonblank and registered once")
        self._handlers[normalized] = handler

    def dispatch(self, job: ScheduledJob) -> None:
        try:
            handler = self._handlers[job.job_type]
        except KeyError as exc:
            raise ValueError(f"no handler registered for job type {job.job_type}") from exc
        handler(job)


@dataclass(frozen=True)
class WorkerHealth:
    worker_id: str
    status: str
    processed: int
    failed: int
    last_job_id: str | None
    last_heartbeat: datetime


class HostedWorker:
    def __init__(self, repository: JobRepository, handlers: HandlerRegistry, settings: WorkerSettings):
        self.repository, self.handlers, self.settings = repository, handlers, settings
        self._processed = self._failed = 0
        self._last_job_id: str | None = None
        self._last_heartbeat = datetime.now(timezone.utc)

    @property
    def health(self) -> WorkerHealth:
        return WorkerHealth(self.settings.worker_id, "READY", self._processed, self._failed, self._last_job_id, self._last_heartbeat)

    def run_once(self, now: datetime | None = None) -> ScheduledJob | None:
        now = now or datetime.now(timezone.utc)
        self.repository.recover_expired(now)
        job = self.repository.claim_due(now, self.settings.worker_id, self.settings.lease_duration)
        self._last_heartbeat = now
        if job is None:
            return None
        self._last_job_id = job.job_id
        try:
            self.handlers.dispatch(job)
        except Exception as exc:
            self._failed += 1
            message = f"{type(exc).__name__}: {exc}"[:1000]
            return self.repository.fail(job.job_id, self.settings.worker_id, now, message, self.settings.retry_policy)
        self._processed += 1
        return self.repository.complete(job.job_id, self.settings.worker_id)

    def run(self, stop: Event, *, max_iterations: int | None = None) -> WorkerHealth:
        iterations = 0
        while not stop.is_set() and (max_iterations is None or iterations < max_iterations):
            job = self.run_once()
            iterations += 1
            if job is None:
                stop.wait(self.settings.poll_interval)
        return self.health


def build_job_repository(values: Mapping[str, str] = os.environ) -> JobRepository:
    backend = values.get("UIIP_JOB_DATABASE_BACKEND", values.get("UIIP_DATABASE_BACKEND", "sqlite")).lower()
    if backend == "postgresql":
        from .postgres_jobs import PostgresJobRepository
        repository = PostgresJobRepository.from_dsn(values.get("UIIP_DATABASE_URL", ""))
    elif backend == "sqlite":
        path = Path(values.get("UIIP_JOB_SQLITE_PATH", "var/uiip/jobs.sqlite3"))
        path.parent.mkdir(parents=True, exist_ok=True)
        repository = SQLiteJobRepository(path)
    else:
        raise ValueError("job database backend must be sqlite or postgresql")
    repository.initialize()
    return repository


@dataclass(frozen=True)
class RecurringSchedule:
    schedule_id: str
    job_type: str
    interval: timedelta
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.schedule_id.strip() or not self.job_type.strip() or self.interval <= timedelta(0):
            raise ValueError("schedule identity, job type, and positive interval are required")


def enqueue_schedule(repository: JobRepository, schedule: RecurringSchedule, due_at: datetime) -> ScheduledJob:
    if due_at.tzinfo is None:
        raise ValueError("schedule time must be timezone-aware")
    bucket = int(due_at.timestamp() // schedule.interval.total_seconds())
    identity = f"{schedule.schedule_id}:{bucket}"
    digest = hashlib.sha256(identity.encode()).hexdigest()[:24]
    job = ScheduledJob(f"job-{digest}", identity, schedule.job_type, schedule.payload, due_at)
    return repository.enqueue(job)
