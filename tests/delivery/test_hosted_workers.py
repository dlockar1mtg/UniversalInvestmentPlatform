from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event

import pytest

from foundation.production.scheduling import JobStatus, ScheduledJob, SQLiteJobRepository
from foundation.production.worker import HandlerRegistry, HostedWorker, RecurringSchedule, WorkerSettings, build_job_repository, enqueue_schedule

NOW = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)


def repository(tmp_path):
    result = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    result.initialize()
    return result


def test_worker_settings_validate_and_load_environment():
    settings = WorkerSettings.from_environment({
        "UIIP_WORKER_ID": "worker-a", "UIIP_WORKER_POLL_SECONDS": "2",
        "UIIP_WORKER_LEASE_SECONDS": "60", "UIIP_WORKER_MAX_ATTEMPTS": "4",
    })
    assert settings.worker_id == "worker-a" and settings.poll_interval == 2
    assert settings.lease_duration == timedelta(seconds=60) and settings.retry_policy.maximum_attempts == 4
    with pytest.raises(ValueError):
        WorkerSettings("", 0, timedelta(0))


def test_handler_registry_enforces_unique_known_job_types():
    registry = HandlerRegistry()
    registry.register("sample", lambda job: None)
    with pytest.raises(ValueError):
        registry.register("sample", lambda job: None)
    with pytest.raises(ValueError, match="no handler"):
        registry.dispatch(ScheduledJob("j", "k", "unknown", {}, NOW))


def test_worker_claims_dispatches_and_completes_job(tmp_path):
    repo, handled = repository(tmp_path), []
    repo.enqueue(ScheduledJob("job-1", "once-1", "sample", {"value": 7}, NOW))
    handlers = HandlerRegistry()
    handlers.register("sample", lambda job: handled.append(job.payload["value"]))
    worker = HostedWorker(repo, handlers, WorkerSettings("worker-a", .01, timedelta(minutes=1)))
    result = worker.run_once(NOW)
    assert result.status is JobStatus.COMPLETED and handled == [7]
    assert worker.health.processed == 1 and worker.health.last_job_id == "job-1"


def test_worker_failure_is_retried_without_losing_evidence(tmp_path):
    repo = repository(tmp_path)
    repo.enqueue(ScheduledJob("job-1", "once-1", "sample", {}, NOW))
    handlers = HandlerRegistry()
    handlers.register("sample", lambda job: (_ for _ in ()).throw(RuntimeError("safe failure")))
    worker = HostedWorker(repo, handlers, WorkerSettings("worker-a", .01, timedelta(minutes=1)))
    result = worker.run_once(NOW)
    assert result.status is JobStatus.RETRY_WAIT and result.last_error == "RuntimeError: safe failure"
    assert worker.health.failed == 1


def test_recurring_schedule_is_bucket_idempotent_and_advances(tmp_path):
    repo = repository(tmp_path)
    schedule = RecurringSchedule("providers-hourly", "provider_check", timedelta(hours=1), {"symbol": "SPY"})
    first = enqueue_schedule(repo, schedule, NOW)
    repeated = enqueue_schedule(repo, schedule, NOW + timedelta(minutes=30))
    next_job = enqueue_schedule(repo, schedule, NOW + timedelta(hours=1))
    assert first.job_id == repeated.job_id and first.idempotency_key == repeated.idempotency_key
    assert next_job.job_id != first.job_id


def test_worker_loop_stops_deterministically_and_repository_builder_is_explicit(tmp_path):
    repo, handlers = repository(tmp_path), HandlerRegistry()
    worker = HostedWorker(repo, handlers, WorkerSettings("worker-a", .001, timedelta(minutes=1)))
    health = worker.run(Event(), max_iterations=2)
    assert health.status == "READY" and health.processed == 0
    built = build_job_repository({"UIIP_JOB_DATABASE_BACKEND": "sqlite", "UIIP_JOB_SQLITE_PATH": str(tmp_path / "built.sqlite3")})
    assert isinstance(built, SQLiteJobRepository)
    with pytest.raises(ValueError, match="backend"):
        build_job_repository({"UIIP_JOB_DATABASE_BACKEND": "unknown"})
