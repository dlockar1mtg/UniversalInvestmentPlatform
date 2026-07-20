"""PostgreSQL implementation of the certified production repository contract."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime
import json
from typing import Callable

from .contracts import AuditEvent, PersistedArtifact, ProductionRun, ProductionRunStatus, canonical_json


class PostgresProductionRepository:
    def __init__(self, connection_factory: Callable[[], object]):
        self._connection_factory = connection_factory

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresProductionRepository":
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def initialize(self) -> None:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("""CREATE TABLE IF NOT EXISTS production_runs (
                run_id TEXT PRIMARY KEY, source_phase TEXT NOT NULL,
                request_fingerprint TEXT NOT NULL, policy_fingerprint TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL, status TEXT NOT NULL, metadata_json JSONB NOT NULL
            )""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS production_artifacts (
                artifact_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES production_runs(run_id),
                artifact_type TEXT NOT NULL, payload BYTEA NOT NULL,
                created_at TIMESTAMPTZ NOT NULL, content_fingerprint TEXT NOT NULL
            )""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS production_audit_events (
                event_id TEXT PRIMARY KEY, run_id TEXT NOT NULL REFERENCES production_runs(run_id),
                sequence INTEGER NOT NULL, event_type TEXT NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL, evidence_json JSONB NOT NULL,
                UNIQUE(run_id, sequence)
            )""")

    def register_run(self, run: ProductionRun) -> ProductionRun:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("SELECT request_fingerprint,policy_fingerprint FROM production_runs WHERE run_id=%s", (run.run_id,))
            existing = cursor.fetchone()
            if existing:
                if tuple(existing) != (run.request_fingerprint, run.policy_fingerprint):
                    raise ValueError("run_id is already registered with different fingerprints")
                return self.get_run(run.run_id)
            cursor.execute("INSERT INTO production_runs VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)", (
                run.run_id, run.source_phase, run.request_fingerprint, run.policy_fingerprint,
                run.created_at, run.status.value, canonical_json(dict(run.metadata)),
            ))
        return run

    def get_run(self, run_id: str) -> ProductionRun:
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute("SELECT run_id,source_phase,request_fingerprint,policy_fingerprint,created_at,status,metadata_json FROM production_runs WHERE run_id=%s", (run_id,))
            row = cursor.fetchone()
        if row is None:
            raise KeyError(run_id)
        metadata = row[6] if isinstance(row[6], dict) else json.loads(row[6])
        return ProductionRun(row[0], row[1], row[2], row[3], row[4], ProductionRunStatus(row[5]), metadata)

    def append_artifact(self, artifact: PersistedArtifact) -> None:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("SELECT content_fingerprint FROM production_artifacts WHERE artifact_id=%s", (artifact.artifact_id,))
            existing = cursor.fetchone()
            if existing:
                if existing[0] != artifact.content_fingerprint:
                    raise ValueError("artifact_id already contains different content")
                return
            cursor.execute("INSERT INTO production_artifacts VALUES (%s,%s,%s,%s,%s,%s)", (
                artifact.artifact_id, artifact.run_id, artifact.artifact_type, artifact.payload,
                artifact.created_at, artifact.content_fingerprint,
            ))

    def append_audit_event(self, event: AuditEvent) -> None:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(sequence),0) FROM production_audit_events WHERE run_id=%s", (event.run_id,))
            if event.sequence != cursor.fetchone()[0] + 1:
                raise ValueError("audit sequence must be contiguous")
            cursor.execute("INSERT INTO production_audit_events VALUES (%s,%s,%s,%s,%s,%s::jsonb)", (
                event.event_id, event.run_id, event.sequence, event.event_type,
                event.occurred_at, canonical_json(dict(event.evidence)),
            ))

    def audit_events(self, run_id: str) -> tuple[AuditEvent, ...]:
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute("SELECT event_id,run_id,sequence,event_type,occurred_at,evidence_json FROM production_audit_events WHERE run_id=%s ORDER BY sequence", (run_id,))
            rows = cursor.fetchall()
        return tuple(AuditEvent(row[0], row[1], row[2], row[3], row[4], row[5] if isinstance(row[5], dict) else json.loads(row[5])) for row in rows)

    def readiness(self) -> bool:
        try:
            with closing(self._connection_factory()) as db, db.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone()[0] == 1
        except Exception:
            return False
