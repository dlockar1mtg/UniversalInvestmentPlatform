from datetime import datetime, timezone
from pathlib import Path

import pytest

import foundation.production.hosted_refresh_status as refresh_status
from foundation.production.publication_outcomes import (
    latest_outcome,
    normalize_outcome,
    record_outcome,
    summarize_reason,
)

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "production-publication-cycle.yml"
NOW = datetime(2026, 10, 1, 20, 0, tzinfo=timezone.utc)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, sql, params=None):
        self.connection.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.connection.rows.pop(0)


class FakeConnection:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.executed = []
        self.committed = False
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def _healthy(domain_id):
    return {
        "domain_id": domain_id,
        "certification_state": "CERTIFIED",
        "import_registry_status": "ACTIVE",
        "last_import_status": "IMPORTED",
        "last_imported_at_utc": "2026-10-01T19:00:00+00:00",
        "last_data_as_of_date": "2026-10-01",
        "warning_count": 0,
        "error_count": 0,
    }


class RepositoryWithoutOutcomeStore:
    def domain_health(self):
        return tuple(_healthy(domain) for domain in ("crypto", "metals", "mtg"))


class RepositoryWithOutcomeStore(RepositoryWithoutOutcomeStore):
    connection_factory = object


def _status_with_outcome(monkeypatch, outcome):
    monkeypatch.setattr(refresh_status, "latest_outcome", lambda factory: outcome)
    return refresh_status.build_refresh_status(RepositoryWithOutcomeStore(), now=NOW)


def test_normalize_outcome_maps_job_status():
    assert normalize_outcome("success") == "SUCCESS"
    assert normalize_outcome(" Failure ") == "FAILURE"
    assert normalize_outcome("cancelled") == "CANCELLED"
    with pytest.raises(ValueError):
        normalize_outcome("skipped")


def test_summarize_reason_keeps_last_lines_and_redacts_secrets():
    log = "warning one\n\nUsing postgresql://user:pw@host/db\nGoverned source run x is too old: 241.1 hours\n"
    reason = summarize_reason(log, redact=("postgresql://user:pw@host/db",), max_lines=2)
    assert reason == "Using [redacted] | Governed source run x is too old: 241.1 hours"
    assert summarize_reason("\n  \n") is None


def test_record_outcome_creates_table_upserts_and_commits():
    connection = FakeConnection()
    record_outcome(
        lambda: connection,
        run_id="36913106164-1",
        workflow="UIP Production Publication Cycle",
        outcome="FAILURE",
        reason="too old",
        run_url="https://github.com/example/runs/36913106164",
        now=NOW,
    )
    assert connection.executed[0][0].startswith("CREATE TABLE IF NOT EXISTS publication_run_outcomes")
    sql, params = connection.executed[1]
    assert sql.startswith("INSERT INTO publication_run_outcomes")
    assert "ON CONFLICT (run_id) DO UPDATE" in sql
    assert params == (
        "36913106164-1",
        "UIP Production Publication Cycle",
        "FAILURE",
        "too old",
        "https://github.com/example/runs/36913106164",
        NOW,
    )
    assert connection.committed and connection.closed


def test_record_outcome_rejects_unknown_outcome():
    with pytest.raises(ValueError):
        record_outcome(
            lambda: FakeConnection(), run_id="1", workflow="w", outcome="BROKEN", reason=None, run_url=None
        )


def test_latest_outcome_is_none_before_the_table_exists():
    connection = FakeConnection(rows=[(None,)])
    assert latest_outcome(lambda: connection) is None
    assert len(connection.executed) == 1


def test_latest_outcome_returns_most_recent_row_with_utc_time():
    connection = FakeConnection(
        rows=[("publication_run_outcomes",), ("1-1", "wf", "FAILURE", "too old", "url", NOW)]
    )
    assert latest_outcome(lambda: connection) == {
        "run_id": "1-1",
        "workflow": "wf",
        "outcome": "FAILURE",
        "reason": "too old",
        "run_url": "url",
        "recorded_at_utc": "2026-10-01T20:00:00+00:00",
    }
    assert "ORDER BY recorded_at_utc DESC" in connection.executed[1][0]


def test_refresh_status_surfaces_a_failed_publication(monkeypatch):
    failure = {
        "run_id": "36913106164-1",
        "workflow": "UIP Production Publication Cycle",
        "outcome": "FAILURE",
        "reason": "Governed source run x is too old: 241.1 hours",
        "run_url": "url",
        "recorded_at_utc": "2026-10-01T19:16:00+00:00",
    }
    document = _status_with_outcome(monkeypatch, failure)
    assert document["status"] == "REVIEW"
    assert document["last_publication_outcome"] == failure
    for item in document["items"]:
        assert item["health_state"] == "REVIEW"
        assert item["last_good_state_status"] == "LAST_GOOD_STATE_REMAINS_ACTIVE"
        assert item["recommendations_usable"] is True
        assert "too old: 241.1 hours" in item["failure_summary"]


def test_refresh_status_is_unchanged_after_a_successful_publication(monkeypatch):
    success = {
        "run_id": "36923558824-1",
        "workflow": "UIP Production Publication Cycle",
        "outcome": "SUCCESS",
        "reason": None,
        "run_url": "url",
        "recorded_at_utc": "2026-10-01T20:55:00+00:00",
    }
    document = _status_with_outcome(monkeypatch, success)
    assert document["status"] == "HEALTHY"
    assert document["last_publication_outcome"] == success
    assert all(item["failure_summary"] is None for item in document["items"])


def test_refresh_status_without_an_outcome_store_reports_none():
    document = refresh_status.build_refresh_status(RepositoryWithoutOutcomeStore(), now=NOW)
    assert document["last_publication_outcome"] is None
    assert document["status"] == "HEALTHY"


def test_publication_workflow_records_every_outcome():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "- name: Record publication outcome" in text
    assert "scripts/record_publication_outcome.py" in text
    assert '--job-status "${{ job.status }}"' in text
    assert "publication_errors.log" in text
    record_step = text[text.index("- name: Record publication outcome"):]
    header = record_step.split("run:")[0]
    assert "if: always()" in header
    assert "continue-on-error: true" in header
