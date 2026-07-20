"""PostgreSQL durable job repository for horizontally scaled workers."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime, timedelta
import json
from typing import Callable

from .scheduling import JobStatus, RetryPolicy, ScheduledJob


class PostgresJobRepository:
    def __init__(self, connection_factory: Callable[[], object]):
        self._connection_factory = connection_factory

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresJobRepository":
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def initialize(self) -> None:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("""CREATE TABLE IF NOT EXISTS production_jobs (
                job_id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE,
                job_type TEXT NOT NULL, payload_json JSONB NOT NULL,
                payload_fingerprint TEXT NOT NULL, scheduled_at TIMESTAMPTZ NOT NULL,
                status TEXT NOT NULL, attempts INTEGER NOT NULL, available_at TIMESTAMPTZ NOT NULL,
                lease_owner TEXT, lease_expires_at TIMESTAMPTZ, last_error TEXT
            )""")

    @staticmethod
    def _job(row) -> ScheduledJob:
        payload = row[3] if isinstance(row[3], dict) else json.loads(row[3])
        return ScheduledJob(row[0], row[1], row[2], payload, row[5], JobStatus(row[6]), row[7], row[8], row[9], row[10], row[11])

    def get(self, job_id: str) -> ScheduledJob:
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute("SELECT job_id,idempotency_key,job_type,payload_json,payload_fingerprint,scheduled_at,status,attempts,available_at,lease_owner,lease_expires_at,last_error FROM production_jobs WHERE job_id=%s", (job_id,))
            row = cursor.fetchone()
        if row is None:
            raise KeyError(job_id)
        return self._job(row)

    def enqueue(self, job: ScheduledJob) -> ScheduledJob:
        available = job.available_at or job.scheduled_at
        encoded = json.dumps(job.payload, sort_keys=True, separators=(",", ":"), default=str)
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("SELECT job_id,job_type,payload_fingerprint FROM production_jobs WHERE idempotency_key=%s", (job.idempotency_key,))
            existing = cursor.fetchone()
            if existing:
                if existing[1:] != (job.job_type, job.payload_fingerprint):
                    raise ValueError("idempotency key already identifies a different job")
                return self.get(existing[0])
            cursor.execute("INSERT INTO production_jobs VALUES (%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s)", (
                job.job_id, job.idempotency_key, job.job_type, encoded, job.payload_fingerprint,
                job.scheduled_at, job.status.value, job.attempts, available, job.lease_owner, job.lease_expires_at, job.last_error,
            ))
        return self.get(job.job_id)

    def claim_due(self, now: datetime, worker_id: str, lease_duration: timedelta) -> ScheduledJob | None:
        if now.tzinfo is None or not worker_id.strip() or lease_duration <= timedelta(0):
            raise ValueError("aware time, worker identity, and positive lease are required")
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("""SELECT job_id FROM production_jobs
                WHERE status IN (%s,%s) AND available_at<=%s
                ORDER BY available_at,job_id FOR UPDATE SKIP LOCKED LIMIT 1""",
                (JobStatus.PENDING.value, JobStatus.RETRY_WAIT.value, now))
            row = cursor.fetchone()
            if row is None:
                return None
            cursor.execute("UPDATE production_jobs SET status=%s,attempts=attempts+1,lease_owner=%s,lease_expires_at=%s WHERE job_id=%s",
                           (JobStatus.RUNNING.value, worker_id, now + lease_duration, row[0]))
            job_id = row[0]
        return self.get(job_id)

    def complete(self, job_id: str, worker_id: str) -> ScheduledJob:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("UPDATE production_jobs SET status=%s,lease_owner=NULL,lease_expires_at=NULL,last_error=NULL WHERE job_id=%s AND status=%s AND lease_owner=%s",
                           (JobStatus.COMPLETED.value, job_id, JobStatus.RUNNING.value, worker_id))
            if cursor.rowcount != 1:
                raise ValueError("worker does not hold the active job lease")
        return self.get(job_id)

    def fail(self, job_id: str, worker_id: str, now: datetime, error: str, policy: RetryPolicy) -> ScheduledJob:
        current = self.get(job_id)
        if current.status is not JobStatus.RUNNING or current.lease_owner != worker_id:
            raise ValueError("worker does not hold the active job lease")
        status = JobStatus.DEAD_LETTER if current.attempts >= policy.maximum_attempts else JobStatus.RETRY_WAIT
        available = now if status is JobStatus.DEAD_LETTER else now + policy.delay_after(current.attempts)
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("UPDATE production_jobs SET status=%s,available_at=%s,lease_owner=NULL,lease_expires_at=NULL,last_error=%s WHERE job_id=%s",
                           (status.value, available, error[:1000], job_id))
        return self.get(job_id)

    def recover_expired(self, now: datetime) -> tuple[str, ...]:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("SELECT job_id FROM production_jobs WHERE status=%s AND lease_expires_at<=%s ORDER BY job_id FOR UPDATE",
                           (JobStatus.RUNNING.value, now))
            identifiers = tuple(row[0] for row in cursor.fetchall())
            if identifiers:
                cursor.execute("UPDATE production_jobs SET status=%s,available_at=%s,lease_owner=NULL,lease_expires_at=NULL,last_error=%s WHERE job_id=ANY(%s)",
                               (JobStatus.RETRY_WAIT.value, now, "WORKER_LEASE_EXPIRED", list(identifiers)))
        return identifiers
