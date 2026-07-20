from datetime import datetime, timedelta, timezone

import pytest

from foundation.production import JobStatus, RetryPolicy, ScheduledJob, SQLiteJobRepository, run_next_job

NOW = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)


def repository(tmp_path):
    repo = SQLiteJobRepository(tmp_path / "jobs.sqlite3")
    repo.initialize()
    return repo


def job(job_id="job-1", key="key-1", scheduled_at=NOW, payload=None):
    return ScheduledJob(job_id, key, "DECISION_RUN", payload or {"run_id": job_id}, scheduled_at)


def test_enqueue_is_durable_idempotent_and_conflict_sensitive(tmp_path):
    repo = repository(tmp_path)
    assert repo.enqueue(job()) == repo.enqueue(job())
    assert SQLiteJobRepository(repo.database_path).get("job-1").idempotency_key == "key-1"
    with pytest.raises(ValueError, match="different job"):
        repo.enqueue(job("job-2", "key-1", payload={"changed": True}))


def test_due_jobs_are_claimed_in_deterministic_order_with_exclusive_lease(tmp_path):
    repo = repository(tmp_path)
    repo.enqueue(job("b", "b", NOW))
    repo.enqueue(job("a", "a", NOW))
    first = repo.claim_due(NOW, "worker-1", timedelta(minutes=5))
    second = repo.claim_due(NOW, "worker-2", timedelta(minutes=5))
    assert (first.job_id, second.job_id) == ("a", "b")
    assert first.status is JobStatus.RUNNING and first.attempts == 1


def test_successful_worker_execution_completes_once(tmp_path):
    repo = repository(tmp_path)
    repo.enqueue(job())
    completed = run_next_job(repo, NOW, "worker", lambda claimed: None)
    assert completed.status is JobStatus.COMPLETED
    assert run_next_job(repo, NOW, "worker", lambda claimed: None) is None


def test_failure_retries_with_backoff_then_dead_letters(tmp_path):
    repo = repository(tmp_path)
    repo.enqueue(job())
    policy = RetryPolicy(maximum_attempts=2, initial_backoff=timedelta(seconds=10))
    failed = run_next_job(repo, NOW, "worker", lambda claimed: (_ for _ in ()).throw(RuntimeError("boom")), retry_policy=policy)
    assert failed.status is JobStatus.RETRY_WAIT
    assert failed.available_at == NOW + timedelta(seconds=10)
    dead = run_next_job(repo, failed.available_at, "worker", lambda claimed: (_ for _ in ()).throw(RuntimeError("again")), retry_policy=policy)
    assert dead.status is JobStatus.DEAD_LETTER and "again" in dead.last_error


def test_expired_worker_lease_is_recovered_with_evidence(tmp_path):
    repo = repository(tmp_path)
    repo.enqueue(job())
    repo.claim_due(NOW, "lost-worker", timedelta(minutes=1))
    assert repo.recover_expired(NOW + timedelta(minutes=2)) == ("job-1",)
    recovered = repo.get("job-1")
    assert recovered.status is JobStatus.RETRY_WAIT
    assert recovered.last_error == "WORKER_LEASE_EXPIRED"


def test_only_lease_owner_can_complete_or_fail_job(tmp_path):
    repo = repository(tmp_path)
    repo.enqueue(job())
    repo.claim_due(NOW, "owner", timedelta(minutes=5))
    with pytest.raises(ValueError, match="does not hold"):
        repo.complete("job-1", "other-worker")
    assert repo.complete("job-1", "owner").status is JobStatus.COMPLETED
