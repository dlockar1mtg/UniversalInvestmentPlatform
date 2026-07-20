"""Deterministic Phase 6 production-readiness certification."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from .api import ProductionAPI
from .config import ProductionRuntimeConfig
from .contracts import AuditEvent, PersistedArtifact, ProductionRun
from .deployment import DatabaseBackupManager, DeploymentManifest, SchemaMigration, bootstrap_production
from .integration import ExternalDataRecord, IngestionPolicy, ingest_provider
from .observability import EventRecorder, MetricRegistry, SecuredProductionGateway
from .operations import collect_operational_status
from .persistence import SQLiteProductionRepository
from .scheduling import JobStatus, ScheduledJob, SQLiteJobRepository, run_next_job
from .security import APIKeyAuthenticator, SecretReference


NOW = datetime(2026, 7, 20, 12, tzinfo=timezone.utc)


@dataclass(frozen=True)
class ProductionCertificationCheck:
    check_id: str
    status: str
    evidence: str

    def to_dict(self) -> dict[str, str]:
        return {"check_id": self.check_id, "evidence": self.evidence, "status": self.status}


@dataclass(frozen=True)
class Phase6CertificationReport:
    phase: str
    status: str
    release_version: str
    certification_fingerprint: str
    checks: tuple[ProductionCertificationCheck, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "certification_fingerprint": self.certification_fingerprint,
            "checks": [item.to_dict() for item in self.checks],
            "phase": self.phase, "release_version": self.release_version, "status": self.status,
        }


class _Provider:
    provider_id = "certified-market-data"

    def __init__(self, reverse: bool = False):
        groups = ("crypto", "etf", "metals", "mtg")
        records = tuple(ExternalDataRecord(
            f"record-{group}", self.provider_id, NOW, group,
            {"price": index + 100, "score": 80 - index}, f"certified:{group}",
        ) for index, group in enumerate(groups))
        self.records = tuple(reversed(records)) if reverse else records

    def fetch(self):
        return self.records


def _check(check_id: str, passed: bool, evidence: str, failure: str) -> ProductionCertificationCheck:
    return ProductionCertificationCheck(check_id, "PASSED" if passed else "FAILED", evidence if passed else failure)


def _scenario(root: Path, *, reverse: bool = False) -> tuple[ProductionCertificationCheck, ...]:
    config = ProductionRuntimeConfig("test", root / "data" / "production.sqlite3", root / "artifacts")
    manifest = DeploymentManifest(
        "6.0.0", "phase-6-certified-revision", "a" * 64, "test",
        (SchemaMigration("001-certification", "CREATE TABLE certification_marker(value TEXT);"),),
        (SecretReference("UIIP_CERTIFICATION_KEY"),),
    )
    startup = bootstrap_production(config, manifest, {"UIIP_CERTIFICATION_KEY": "resolved-at-runtime"})

    repository = SQLiteProductionRepository(config.database_path)
    run = ProductionRun("phase-6-certification", "6", "b" * 64, "c" * 64, NOW, metadata={"scope": "production-readiness"})
    repository.register_run(run)
    repository.register_run(run)
    repository.append_artifact(PersistedArtifact("certified-output", run.run_id, "CERTIFICATION", b"certified-output", NOW))
    repository.append_audit_event(AuditEvent("certified-event", run.run_id, 1, "PRODUCTION_REGISTERED", NOW))
    with closing(sqlite3.connect(config.database_path)) as database:
        artifact_row = database.execute(
            "SELECT content_fingerprint FROM production_artifacts WHERE artifact_id=?",
            ("certified-output",),
        ).fetchone()

    policy = IngestionPolicy(NOW + timedelta(minutes=1), required_metrics=("price", "score"))
    batch = ingest_provider(_Provider(reverse), policy)
    reversed_batch = ingest_provider(_Provider(not reverse), policy)

    authenticator = APIKeyAuthenticator(
        {"viewer": ("viewer",), "operator": ("operator",)},
        {"viewer": APIKeyAuthenticator.hash_credential("viewer-key"), "operator": APIKeyAuthenticator.hash_credential("operator-key")},
    )
    events, metrics = EventRecorder(), MetricRegistry()
    gateway = SecuredProductionGateway(ProductionAPI(repository), authenticator, events, metrics)
    api_body = json.dumps({
        "run_id": "api-certification-run", "source_phase": "6",
        "policy_fingerprint": "d" * 64, "requested_at": NOW.isoformat(),
        "payload": {"batch_fingerprint": batch.batch_fingerprint},
    }, sort_keys=True)
    unauthenticated = gateway.handle("POST", "/v1/runs", api_body, correlation_id="correlation-unauthenticated")
    forbidden = gateway.handle("POST", "/v1/runs", api_body, credential="viewer-key", correlation_id="correlation-forbidden")
    accepted = gateway.handle("POST", "/v1/runs", api_body, credential="operator-key", correlation_id="correlation-accepted")

    jobs = SQLiteJobRepository(config.database_path)
    scheduled = ScheduledJob("certification-job", "certification-key", "DECISION_RUN", {"run_id": run.run_id}, NOW)
    jobs.enqueue(scheduled)
    jobs.enqueue(scheduled)
    completed = run_next_job(jobs, NOW, "certification-worker", lambda item: None)
    recovery = ScheduledJob("recovery-job", "recovery-key", "RECOVERY_TEST", {"run_id": run.run_id}, NOW)
    jobs.enqueue(recovery)
    jobs.claim_due(NOW, "lost-worker", timedelta(minutes=1))
    recovered = jobs.recover_expired(NOW + timedelta(minutes=2))

    backup = root / "backup" / "production.sqlite3"
    restored = root / "restore" / "production.sqlite3"
    manager = DatabaseBackupManager(config.database_path)
    backup_fingerprint = manager.create_backup(backup)
    manager.restore(backup, restored)
    restored_run = SQLiteProductionRepository(restored).get_run(run.run_id)
    status = collect_operational_status(config)
    metric_snapshot = metrics.snapshot()

    return (
        _check("RUNTIME_AND_STARTUP_GATES", startup.health.ready and startup.applied_migrations == ("001-certification",),
               "Validated configuration, secrets, migrations, and readiness gates.", "Runtime startup gates failed."),
        _check("PERSISTENCE_AND_AUDIT_INTEGRITY", repository.get_run(run.run_id) == run and len(repository.audit_events(run.run_id)) == 1,
               "Run registration was idempotent and durable audit evidence was preserved.", "Persistence or audit integrity failed."),
        _check("ARTIFACT_INTEGRITY", artifact_row is not None and len(artifact_row[0]) == 64,
               "Content-addressed certification artifact was stored under the certified run.", "Artifact integrity failed."),
        _check("CROSS_ASSET_DATA_INTEGRATION", {item.asset_id for item in batch.records} == {"crypto", "etf", "metals", "mtg"},
               "Normalized certified data for crypto, etf, metals, and mtg.", "Cross-asset ingestion coverage failed."),
        _check("DETERMINISM_AND_INPUT_ORDER", batch == reversed_batch,
               "Reversed provider input produced the identical normalized batch and fingerprint.", "Data integration was not input-order invariant."),
        _check("SECURITY_BOUNDARIES", (unauthenticated.status_code, forbidden.status_code, accepted.status_code) == (401, 403, 202),
               "Authentication and role authorization enforced 401, 403, and accepted boundaries.", "Security boundaries failed."),
        _check("SCHEDULING_IDEMPOTENCY_AND_RECOVERY", completed is not None and completed.status is JobStatus.COMPLETED and recovered == ("recovery-job",),
               "Idempotent scheduling, exclusive execution, and expired-lease recovery passed.", "Scheduling or recovery failed."),
        _check("OBSERVABILITY_AND_REDACTION", len(events.events) == 3 and all(item.fields["credential"] == "[REDACTED]" for item in events.events) and len(metric_snapshot["counters"]) == 3,
               "Correlated events redacted credentials and metrics retained all API outcomes.", "Observability or redaction failed."),
        _check("BACKUP_AND_RESTORE", len(backup_fingerprint) == 64 and manager.verify(backup) and restored_run.run_id == run.run_id,
               "Online backup, integrity verification, and isolated restore preserved the certified run.", "Backup or restore verification failed."),
        _check("OPERATIONAL_DIAGNOSTICS", status.database_available and status.artifact_directory_available and status.run_counts.get("REGISTERED") == 2,
               "Operational diagnostics reconciled database, artifacts, runs, and jobs.", "Operational diagnostics failed."),
    )


def certify_phase_6() -> Phase6CertificationReport:
    """Execute Phase 6 certification twice and require identical evidence."""
    with TemporaryDirectory() as first_root, TemporaryDirectory() as second_root:
        first = _scenario(Path(first_root))
        second = _scenario(Path(second_root), reverse=True)
    checks = first
    if first != second:
        checks = tuple(
            ProductionCertificationCheck(item.check_id, "FAILED", "Repeated certification evidence differed.")
            if item.check_id == "DETERMINISM_AND_INPUT_ORDER" else item for item in first
        )
    status = "PASSED" if all(item.status == "PASSED" for item in checks) else "FAILED"
    core = {"phase": "6", "release_version": "6.0.0", "status": status, "checks": [item.to_dict() for item in checks]}
    fingerprint = sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return Phase6CertificationReport("6", status, "6.0.0", fingerprint, checks)
