from datetime import datetime, timezone

import pytest

from foundation.production import (
    AuditEvent, PersistedArtifact, ProductionRun, ProductionRunStatus,
    ProductionRuntimeConfig, SQLiteProductionRepository,
)

NOW = datetime(2026, 7, 20, tzinfo=timezone.utc)


def run():
    return ProductionRun("run-1", "5.5", "a" * 64, "b" * 64, NOW, metadata={"asset": "etf"})


def repository(tmp_path):
    repo = SQLiteProductionRepository(tmp_path / "runtime.sqlite3")
    repo.initialize()
    return repo


def test_configuration_loads_from_explicit_mapping_and_fails_closed(tmp_path):
    config = ProductionRuntimeConfig.from_mapping({"UIIP_ENVIRONMENT": "test", "UIIP_DATABASE_PATH": str(tmp_path / "db"), "UIIP_ARTIFACT_DIRECTORY": str(tmp_path / "artifacts")})
    assert config.environment == "test" and config.strict_mode
    with pytest.raises(ValueError, match="missing runtime configuration"):
        ProductionRuntimeConfig.from_mapping({})


def test_run_registration_is_durable_and_idempotent(tmp_path):
    repo = repository(tmp_path)
    assert repo.register_run(run()) == run()
    assert repo.register_run(run()) == run()
    assert SQLiteProductionRepository(repo.database_path).get_run("run-1") == run()


def test_run_identity_conflict_fails_closed(tmp_path):
    repo = repository(tmp_path)
    repo.register_run(run())
    with pytest.raises(ValueError, match="different fingerprints"):
        repo.register_run(ProductionRun("run-1", "5.5", "c" * 64, "b" * 64, NOW))


def test_status_transition_is_persisted(tmp_path):
    repo = repository(tmp_path)
    repo.register_run(run())
    assert repo.update_status("run-1", ProductionRunStatus.RUNNING).status is ProductionRunStatus.RUNNING
    assert repo.update_status("run-1", ProductionRunStatus.COMPLETED).status is ProductionRunStatus.COMPLETED


def test_artifact_content_is_fingerprinted_and_duplicate_safe(tmp_path):
    repo = repository(tmp_path)
    repo.register_run(run())
    artifact = PersistedArtifact("artifact-1", "run-1", "MONITORING_OUTPUT", b"certified", NOW)
    repo.append_artifact(artifact)
    repo.append_artifact(artifact)
    with pytest.raises(ValueError, match="different content"):
        repo.append_artifact(PersistedArtifact("artifact-1", "run-1", "MONITORING_OUTPUT", b"changed", NOW))


def test_audit_events_preserve_contiguous_order_and_reject_duplicates(tmp_path):
    repo = repository(tmp_path)
    repo.register_run(run())
    repo.append_audit_event(AuditEvent("event-1", "run-1", 1, "REGISTERED", NOW, {"source": "certified"}))
    repo.append_audit_event(AuditEvent("event-2", "run-1", 2, "RUNNING", NOW))
    assert tuple(item.sequence for item in repo.audit_events("run-1")) == (1, 2)
    with pytest.raises(ValueError, match="already exists"):
        repo.append_audit_event(AuditEvent("event-3", "run-1", 2, "DUPLICATE", NOW))
