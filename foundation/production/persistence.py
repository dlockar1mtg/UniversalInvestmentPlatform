"""Transactional SQLite persistence for production runs and audit evidence."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import sqlite3

from .contracts import AuditEvent, PersistedArtifact, ProductionRun, ProductionRunStatus, canonical_json


class SQLiteProductionRepository:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def _connect(self):
        connection = sqlite3.connect(self.database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with closing(self._connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS production_runs (
                    run_id TEXT PRIMARY KEY, source_phase TEXT NOT NULL,
                    request_fingerprint TEXT NOT NULL, policy_fingerprint TEXT NOT NULL,
                    created_at TEXT NOT NULL, status TEXT NOT NULL, metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS production_artifacts (
                    artifact_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES production_runs(run_id),
                    artifact_type TEXT NOT NULL, payload BLOB NOT NULL,
                    created_at TEXT NOT NULL, content_fingerprint TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS production_audit_events (
                    event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES production_runs(run_id),
                    sequence INTEGER NOT NULL, event_type TEXT NOT NULL,
                    occurred_at TEXT NOT NULL, evidence_json TEXT NOT NULL,
                    UNIQUE(run_id, sequence)
                );
            """)

    def register_run(self, run: ProductionRun) -> ProductionRun:
        with closing(self._connect()) as db, db:
            existing = db.execute("SELECT request_fingerprint, policy_fingerprint FROM production_runs WHERE run_id=?", (run.run_id,)).fetchone()
            if existing:
                if existing != (run.request_fingerprint, run.policy_fingerprint):
                    raise ValueError("run_id is already registered with different fingerprints")
                return self.get_run(run.run_id)
            db.execute("INSERT INTO production_runs VALUES (?,?,?,?,?,?,?)", (
                run.run_id, run.source_phase, run.request_fingerprint, run.policy_fingerprint,
                run.created_at.isoformat(), run.status.value, canonical_json(dict(run.metadata)),
            ))
        return run

    def get_run(self, run_id: str) -> ProductionRun:
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT * FROM production_runs WHERE run_id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return ProductionRun(row[0], row[1], row[2], row[3], datetime.fromisoformat(row[4]), ProductionRunStatus(row[5]), json.loads(row[6]))

    def update_status(self, run_id: str, status: ProductionRunStatus) -> ProductionRun:
        with closing(self._connect()) as db, db:
            changed = db.execute("UPDATE production_runs SET status=? WHERE run_id=?", (status.value, run_id)).rowcount
            if not changed:
                raise KeyError(run_id)
        return self.get_run(run_id)

    def append_artifact(self, artifact: PersistedArtifact) -> None:
        with closing(self._connect()) as db, db:
            existing = db.execute("SELECT content_fingerprint FROM production_artifacts WHERE artifact_id=?", (artifact.artifact_id,)).fetchone()
            if existing:
                if existing[0] != artifact.content_fingerprint:
                    raise ValueError("artifact_id already contains different content")
                return
            db.execute("INSERT INTO production_artifacts VALUES (?,?,?,?,?,?)", (
                artifact.artifact_id, artifact.run_id, artifact.artifact_type, artifact.payload,
                artifact.created_at.isoformat(), artifact.content_fingerprint,
            ))

    def append_audit_event(self, event: AuditEvent) -> None:
        with closing(self._connect()) as db, db:
            duplicate = db.execute(
                "SELECT 1 FROM production_audit_events WHERE event_id=? OR (run_id=? AND sequence=?)",
                (event.event_id, event.run_id, event.sequence),
            ).fetchone()
            if duplicate:
                raise ValueError("audit event identity or sequence already exists")
            last = db.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM production_audit_events WHERE run_id=?",
                (event.run_id,),
            ).fetchone()[0]
            if event.sequence != last + 1:
                raise ValueError("audit sequence must be contiguous")
            try:
                db.execute("INSERT INTO production_audit_events VALUES (?,?,?,?,?,?)", (
                    event.event_id, event.run_id, event.sequence, event.event_type,
                    event.occurred_at.isoformat(), canonical_json(dict(event.evidence)),
                ))
            except sqlite3.IntegrityError as exc:
                raise ValueError("audit event identity or sequence already exists") from exc

    def audit_events(self, run_id: str) -> tuple[AuditEvent, ...]:
        with closing(self._connect()) as db, db:
            rows = db.execute("SELECT event_id,run_id,sequence,event_type,occurred_at,evidence_json FROM production_audit_events WHERE run_id=? ORDER BY sequence", (run_id,)).fetchall()
        return tuple(AuditEvent(row[0], row[1], row[2], row[3], datetime.fromisoformat(row[4]), json.loads(row[5])) for row in rows)
