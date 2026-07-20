from datetime import datetime, timedelta, timezone
import pytest
from foundation.production.free_staging import FreeStagingSettings, RetryingConnectionFactory, run_scheduled_cycle
from foundation.production.scheduling import SQLiteJobRepository
from foundation.production.worker import HandlerRegistry, HostedWorker, RecurringSchedule, WorkerSettings

def test_render_environment_is_explicit_and_postgresql_only():
    settings = FreeStagingSettings.from_environment({"PORT":"10000", "RENDER_EXTERNAL_HOSTNAME":"uiip.onrender.com", "UIIP_DATABASE_URL":"postgresql://u:p@h/db?sslmode=require"})
    environment = settings.application_environment()
    assert environment["UIIP_HTTP_HOST"] == "0.0.0.0"
    assert environment["UIIP_ALLOWED_HOSTS"] == "uiip.onrender.com"
    assert environment["UIIP_DATABASE_BACKEND"] == "postgresql"

def test_free_staging_rejects_sqlite_insecure_database_and_unbounded_work():
    with pytest.raises(ValueError, match="PostgreSQL"): FreeStagingSettings(10000, "host", "sqlite:///x")
    with pytest.raises(ValueError, match="TLS"): FreeStagingSettings(10000, "host", "postgresql://u:p@h/db")
    with pytest.raises(ValueError, match="maximum jobs"): FreeStagingSettings(10000, "host", "postgresql://u:p@h/db?sslmode=require", 101)

def test_retrying_factory_recovers_transient_cold_start():
    calls = []
    def connector(dsn):
        calls.append(dsn)
        if len(calls) < 3: raise ConnectionError("suspended")
        return "connected"
    factory = RetryingConnectionFactory("dsn", connector, 3, 0, lambda _: None)
    assert factory() == "connected" and len(calls) == 3

def test_retrying_factory_preserves_final_error():
    factory = RetryingConnectionFactory("dsn", lambda _: (_ for _ in ()).throw(ConnectionError("offline")), 2, 0, lambda _: None)
    with pytest.raises(ConnectionError, match="offline"): factory()

def test_one_shot_cycle_is_bucket_idempotent_and_bounded(tmp_path):
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3"); repository.initialize()
    handlers = HandlerRegistry(); handled = []; handlers.register("check", lambda job: handled.append(job.job_id))
    worker = HostedWorker(repository, handlers, WorkerSettings("one-shot", .01, timedelta(minutes=1)))
    schedule = RecurringSchedule("six-hour", "check", timedelta(hours=6), {})
    now = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)
    first = run_scheduled_cycle(repository, (schedule,), worker, now, 5)
    second = run_scheduled_cycle(repository, (schedule,), worker, now + timedelta(minutes=1), 5)
    assert first.processed == 1 and second.processed == 0
    assert first.enqueued_job_ids == second.enqueued_job_ids and len(handled) == 1

def test_one_shot_cycle_rejects_naive_time(tmp_path):
    repository = SQLiteJobRepository(tmp_path / "jobs.sqlite3"); repository.initialize()
    worker = HostedWorker(repository, HandlerRegistry(), WorkerSettings("one-shot"))
    with pytest.raises(ValueError, match="aware time"): run_scheduled_cycle(repository, (), worker, datetime(2026, 1, 1), 1)
