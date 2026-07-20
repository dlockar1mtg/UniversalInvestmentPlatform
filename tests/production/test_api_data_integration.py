from datetime import datetime, timedelta, timezone
import json

from foundation.production import (
    ExternalDataRecord, IngestionPolicy, ProductionAPI, SQLiteProductionRepository,
    ingest_provider,
)

NOW = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)


class Provider:
    provider_id = "market-data"

    def __init__(self, records):
        self.records = records

    def fetch(self):
        return self.records


def record(record_id="r1", asset="etf", price="100", observed_at=NOW):
    return ExternalDataRecord(record_id, "market-data", observed_at, asset, {"price": price}, f"source:{record_id}")


def api(tmp_path):
    repo = SQLiteProductionRepository(tmp_path / "production.sqlite3")
    repo.initialize()
    return ProductionAPI(repo), repo


def request(run_id="run-1", payload=None):
    return json.dumps({
        "run_id": run_id, "source_phase": "5.5", "policy_fingerprint": "a" * 64,
        "requested_at": NOW.isoformat(), "payload": payload or {"portfolio": "universal"},
    })


def test_ingestion_is_deterministic_and_input_order_invariant():
    records = (record("b", "metals", "200"), record("a", "etf", "100"))
    policy = IngestionPolicy(NOW + timedelta(minutes=1), required_metrics=("price",))
    first = ingest_provider(Provider(records), policy)
    second = ingest_provider(Provider(tuple(reversed(records))), policy)
    assert first == second
    assert tuple(item.asset_id for item in first.records) == ("etf", "metals")


def test_ingestion_rejects_stale_missing_and_duplicate_records():
    import pytest
    policy = IngestionPolicy(NOW, maximum_age=timedelta(hours=1), required_metrics=("price",))
    with pytest.raises(ValueError, match="maximum data age"):
        ingest_provider(Provider((record(observed_at=NOW - timedelta(hours=2)),)), policy)
    with pytest.raises(ValueError, match="duplicate"):
        ingest_provider(Provider((record(), record())), policy)


def test_api_registers_run_and_preserves_request_fingerprint(tmp_path):
    service, repo = api(tmp_path)
    response = service.handle("POST", "/v1/runs", request())
    assert response.status_code == 202
    assert response.body["run_id"] == "run-1"
    assert repo.get_run("run-1").request_fingerprint == response.body["request_fingerprint"]


def test_api_submission_is_idempotent_and_audited_once(tmp_path):
    service, repo = api(tmp_path)
    assert service.handle("POST", "/v1/runs", request()).status_code == 202
    assert service.handle("POST", "/v1/runs", request()).status_code == 202
    assert len(repo.audit_events("run-1")) == 1


def test_api_rejects_conflicting_identity_and_invalid_json_safely(tmp_path):
    service, _ = api(tmp_path)
    service.handle("POST", "/v1/runs", request())
    conflict = service.handle("POST", "/v1/runs", request(payload={"changed": True}))
    invalid = service.handle("POST", "/v1/runs", "not-json")
    assert conflict.status_code == invalid.status_code == 400
    assert conflict.body["error"]["code"] == "INVALID_REQUEST"


def test_api_retrieves_status_and_returns_stable_not_found_errors(tmp_path):
    service, _ = api(tmp_path)
    service.handle("POST", "/v1/runs", request())
    found = service.handle("GET", "/v1/runs/run-1")
    missing = service.handle("GET", "/v1/runs/missing")
    assert found.status_code == 200 and found.body["status"] == "REGISTERED"
    assert missing == service.handle("GET", "/v1/runs/missing")
    assert missing.body["error"]["code"] == "RUN_NOT_FOUND"
