"""Durable deterministic job scheduling, leasing, retry, and recovery."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Callable, Mapping


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    COMPLETED = "COMPLETED"
    DEAD_LETTER = "DEAD_LETTER"


@dataclass(frozen=True)
class RetryPolicy:
    maximum_attempts: int = 3
    initial_backoff: timedelta = timedelta(seconds=30)
    backoff_multiplier: int = 2

    def __post_init__(self) -> None:
        if self.maximum_attempts < 1 or self.initial_backoff < timedelta(0) or self.backoff_multiplier < 1:
            raise ValueError("retry policy values are outside permitted bounds")

    def delay_after(self, attempt: int) -> timedelta:
        return self.initial_backoff * (self.backoff_multiplier ** max(0, attempt - 1))


@dataclass(frozen=True)
class ScheduledJob:
    job_id: str
    idempotency_key: str
    job_type: str
    payload: Mapping[str, object]
    scheduled_at: datetime
    status: JobStatus = JobStatus.PENDING
    attempts: int = 0
    available_at: datetime | None = None
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    last_error: str | None = None

    def __post_init__(self) -> None:
        if not all((self.job_id.strip(), self.idempotency_key.strip(), self.job_type.strip())):
            raise ValueError("job identity, idempotency key, and type are required")
        if self.scheduled_at.tzinfo is None or (self.available_at and self.available_at.tzinfo is None):
            raise ValueError("job timestamps must be timezone-aware")
        if self.attempts < 0:
            raise ValueError("attempts must be non-negative")

    @property
    def payload_fingerprint(self) -> str:
        encoded = json.dumps(self.payload, sort_keys=True, separators=(",", ":"), default=str).encode()
        return sha256(encoded).hexdigest()


class SQLiteJobRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        with closing(self._connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS production_jobs (
                job_id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE,
                job_type TEXT NOT NULL, payload_json TEXT NOT NULL,
                payload_fingerprint TEXT NOT NULL, scheduled_at TEXT NOT NULL,
                status TEXT NOT NULL, attempts INTEGER NOT NULL, available_at TEXT NOT NULL,
                lease_owner TEXT, lease_expires_at TEXT, last_error TEXT
            )""")

    @staticmethod
    def _job(row: sqlite3.Row) -> ScheduledJob:
        return ScheduledJob(
            row["job_id"], row["idempotency_key"], row["job_type"], json.loads(row["payload_json"]),
            datetime.fromisoformat(row["scheduled_at"]), JobStatus(row["status"]), row["attempts"],
            datetime.fromisoformat(row["available_at"]), row["lease_owner"],
            datetime.fromisoformat(row["lease_expires_at"]) if row["lease_expires_at"] else None,
            row["last_error"],
        )

    def enqueue(self, job: ScheduledJob) -> ScheduledJob:
        available = job.available_at or job.scheduled_at
        encoded = json.dumps(job.payload, sort_keys=True, separators=(",", ":"), default=str)
        with closing(self._connect()) as db, db:
            existing = db.execute("SELECT * FROM production_jobs WHERE idempotency_key=?", (job.idempotency_key,)).fetchone()
            if existing:
                current = self._job(existing)
                if current.job_type != job.job_type or current.payload_fingerprint != job.payload_fingerprint:
                    raise ValueError("idempotency key already identifies a different job")
                return current
            db.execute("INSERT INTO production_jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                job.job_id, job.idempotency_key, job.job_type, encoded, job.payload_fingerprint,
                job.scheduled_at.isoformat(), job.status.value, job.attempts, available.isoformat(),
                job.lease_owner, job.lease_expires_at.isoformat() if job.lease_expires_at else None,
                job.last_error,
            ))
        return self.get(job.job_id)

    def get(self, job_id: str) -> ScheduledJob:
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT * FROM production_jobs WHERE job_id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._job(row)

    def claim_due(self, now: datetime, worker_id: str, lease_duration: timedelta) -> ScheduledJob | None:
        if now.tzinfo is None or not worker_id.strip() or lease_duration <= timedelta(0):
            raise ValueError("aware time, worker identity, and positive lease are required")
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM production_jobs WHERE status IN (?,?) AND available_at<=? ORDER BY available_at,job_id LIMIT 1",
                (JobStatus.PENDING.value, JobStatus.RETRY_WAIT.value, now.isoformat()),
            ).fetchone()
            if row is None:
                db.commit()
                return None
            db.execute("UPDATE production_jobs SET status=?, attempts=attempts+1, lease_owner=?, lease_expires_at=? WHERE job_id=?", (
                JobStatus.RUNNING.value, worker_id, (now + lease_duration).isoformat(), row["job_id"],
            ))
            db.commit()
            return self.get(row["job_id"])
        finally:
            db.close()

    def complete(self, job_id: str, worker_id: str) -> ScheduledJob:
        with closing(self._connect()) as db, db:
            changed = db.execute("UPDATE production_jobs SET status=?,lease_owner=NULL,lease_expires_at=NULL,last_error=NULL WHERE job_id=? AND status=? AND lease_owner=?", (
                JobStatus.COMPLETED.value, job_id, JobStatus.RUNNING.value, worker_id,
            )).rowcount
            if not changed:
                raise ValueError("worker does not hold the active job lease")
        return self.get(job_id)

    def fail(self, job_id: str, worker_id: str, now: datetime, error: str, policy: RetryPolicy) -> ScheduledJob:
        current = self.get(job_id)
        if current.status is not JobStatus.RUNNING or current.lease_owner != worker_id:
            raise ValueError("worker does not hold the active job lease")
        status = JobStatus.DEAD_LETTER if current.attempts >= policy.maximum_attempts else JobStatus.RETRY_WAIT
        available = now if status is JobStatus.DEAD_LETTER else now + policy.delay_after(current.attempts)
        with closing(self._connect()) as db, db:
            db.execute("UPDATE production_jobs SET status=?,available_at=?,lease_owner=NULL,lease_expires_at=NULL,last_error=? WHERE job_id=?", (
                status.value, available.isoformat(), error[:1000], job_id,
            ))
        return self.get(job_id)

    def recover_expired(self, now: datetime) -> tuple[str, ...]:
        with closing(self._connect()) as db, db:
            rows = db.execute("SELECT job_id FROM production_jobs WHERE status=? AND lease_expires_at<=? ORDER BY job_id", (JobStatus.RUNNING.value, now.isoformat())).fetchall()
            identifiers = tuple(row["job_id"] for row in rows)
            if identifiers:
                db.executemany("UPDATE production_jobs SET status=?,available_at=?,lease_owner=NULL,lease_expires_at=NULL,last_error=? WHERE job_id=?", [
                    (JobStatus.RETRY_WAIT.value, now.isoformat(), "WORKER_LEASE_EXPIRED", job_id) for job_id in identifiers
                ])
        return identifiers


def run_next_job(
    repository: SQLiteJobRepository, now: datetime, worker_id: str,
    handler: Callable[[ScheduledJob], None], *, lease_duration: timedelta = timedelta(minutes=5),
    retry_policy: RetryPolicy = RetryPolicy(),
) -> ScheduledJob | None:
    job = repository.claim_due(now, worker_id, lease_duration)
    if job is None:
        return None
    try:
        handler(job)
    except Exception as exc:
        return repository.fail(job.job_id, worker_id, now, f"{type(exc).__name__}: {exc}", retry_policy)
    return repository.complete(job.job_id, worker_id)
