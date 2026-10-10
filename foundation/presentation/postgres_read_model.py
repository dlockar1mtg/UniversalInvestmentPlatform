"""Atomic PostgreSQL store for versioned UIP dashboard presentation publications."""

from __future__ import annotations

from contextlib import closing
import json
from typing import Callable

from .publication_model import PresentationPublication


class PostgresPresentationRepository:
    """Store presentation projections without becoming analytical authority."""

    def __init__(self, connection_factory: Callable[[], object]):
        self._connection_factory = connection_factory

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresPresentationRepository":
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def initialize(self) -> None:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS presentation_publications (
                    publication_id TEXT PRIMARY KEY,
                    publication_version TEXT NOT NULL,
                    source_database_sha256 TEXT NOT NULL,
                    source_database_classification TEXT NOT NULL,
                    published_at_utc TIMESTAMPTZ NOT NULL,
                    publication_status TEXT NOT NULL,
                    content_fingerprint TEXT NOT NULL,
                    record_count BIGINT NOT NULL,
                    failure_reason TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS presentation_records (
                    publication_id TEXT NOT NULL REFERENCES presentation_publications(publication_id) ON DELETE CASCADE,
                    record_type TEXT NOT NULL,
                    domain_id TEXT NOT NULL,
                    asset_id TEXT,
                    record_key TEXT NOT NULL,
                    payload_json JSONB NOT NULL,
                    PRIMARY KEY (publication_id, record_type, domain_id, record_key)
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS presentation_active_publication (
                    singleton_id SMALLINT PRIMARY KEY CHECK (singleton_id = 1),
                    publication_id TEXT NOT NULL REFERENCES presentation_publications(publication_id),
                    activated_at_utc TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS presentation_records_lookup ON presentation_records (record_type, domain_id, asset_id)")

    def stage(self, publication: PresentationPublication) -> None:
        if publication.publication_status != "STAGED":
            raise ValueError("Only STAGED publications may be staged")
        fingerprint = publication.content_fingerprint
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute(
                "SELECT content_fingerprint, publication_status FROM presentation_publications WHERE publication_id=%s",
                (publication.publication_id,),
            )
            existing = cursor.fetchone()
            if existing:
                if existing[0] != fingerprint:
                    raise ValueError("publication_id already exists with different content")
                return
            cursor.execute(
                """INSERT INTO presentation_publications (
                    publication_id, publication_version, source_database_sha256,
                    source_database_classification, published_at_utc,
                    publication_status, content_fingerprint, record_count
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (
                    publication.publication_id,
                    publication.publication_version,
                    publication.source_database_sha256,
                    publication.source_database_classification,
                    publication.published_at_utc,
                    "STAGED",
                    fingerprint,
                    len(publication.records),
                ),
            )
            # One batched statement instead of one network round trip per record (about 99% of the
            # publication's time against the hosted database). Same rows, same transaction.
            cursor.executemany(
                """INSERT INTO presentation_records (
                    publication_id, record_type, domain_id, asset_id, record_key, payload_json
                ) VALUES (%s,%s,%s,%s,%s,%s::jsonb)""",
                [
                    (
                        publication.publication_id,
                        record.record_type,
                        record.domain_id,
                        record.asset_id,
                        record.record_key,
                        json.dumps(record.payload, sort_keys=True, default=str),
                    )
                    for record in publication.records
                ],
            )

    def validate_staged(self, publication_id: str) -> dict[str, int]:
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT publication_status, record_count FROM presentation_publications WHERE publication_id=%s",
                (publication_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(publication_id)
            if row[0] != "STAGED":
                raise ValueError("Publication is not STAGED")
            cursor.execute(
                "SELECT COUNT(*) FROM presentation_records WHERE publication_id=%s",
                (publication_id,),
            )
            actual = int(cursor.fetchone()[0])
            expected = int(row[1])
            if actual != expected:
                raise ValueError("Staged publication record count mismatch")
            cursor.execute(
                """SELECT domain_id, COUNT(*) FROM presentation_records
                   WHERE publication_id=%s AND record_type='domain_health'
                   GROUP BY domain_id ORDER BY domain_id""",
                (publication_id,),
            )
            health = {str(domain): int(count) for domain, count in cursor.fetchall()}
            if health != {"crypto": 1, "metals": 1, "mtg": 1}:
                raise ValueError("Staged publication must contain one health record per certified domain")
            cursor.execute(
                """SELECT domain_id, COUNT(*) FROM presentation_records
                   WHERE publication_id=%s AND record_type='asset'
                   GROUP BY domain_id ORDER BY domain_id""",
                (publication_id,),
            )
            asset_counts = {str(domain): int(count) for domain, count in cursor.fetchall()}
            if set(asset_counts) != {"crypto", "metals", "mtg"} or any(count <= 0 for count in asset_counts.values()):
                raise ValueError("Staged publication must contain a non-empty current asset surface for every certified domain")
            return {"record_count": actual, **{f"{domain}_asset_count": count for domain, count in asset_counts.items()}}

    def activate(self, publication_id: str) -> None:
        """Atomically switch the active pointer; rollback preserves the previous version."""
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute(
                "SELECT publication_status FROM presentation_publications WHERE publication_id=%s FOR UPDATE",
                (publication_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise KeyError(publication_id)
            if row[0] != "STAGED":
                raise ValueError("Only a STAGED publication may be activated")
            cursor.execute(
                """SELECT COUNT(*) FROM presentation_records
                   WHERE publication_id=%s AND record_type='domain_health'""",
                (publication_id,),
            )
            if int(cursor.fetchone()[0]) != 3:
                raise ValueError("Activation requires all three certified domain-health records")
            cursor.execute(
                """UPDATE presentation_publications
                   SET publication_status='SUPERSEDED'
                   WHERE publication_id=(SELECT publication_id FROM presentation_active_publication WHERE singleton_id=1)
                     AND publication_id<>%s""",
                (publication_id,),
            )
            cursor.execute(
                """INSERT INTO presentation_active_publication (singleton_id, publication_id)
                   VALUES (1,%s)
                   ON CONFLICT (singleton_id) DO UPDATE
                   SET publication_id=EXCLUDED.publication_id,
                       activated_at_utc=CURRENT_TIMESTAMP""",
                (publication_id,),
            )
            cursor.execute(
                "UPDATE presentation_publications SET publication_status='ACTIVE' WHERE publication_id=%s",
                (publication_id,),
            )

    def reject(self, publication_id: str, reason: str) -> None:
        if not reason.strip():
            raise ValueError("Rejection reason must not be blank")
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute(
                """UPDATE presentation_publications
                   SET publication_status='REJECTED', failure_reason=%s
                   WHERE publication_id=%s AND publication_status='STAGED'""",
                (reason, publication_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("Only a STAGED publication may be rejected")

    def prune(self, keep_superseded: int = 2) -> dict[str, int]:
        """Delete old presentation versions so the database stays under its size limit.

        Kept: the ACTIVE publication and the newest `keep_superseded` SUPERSEDED ones (for rollback).
        Deleted: older SUPERSEDED versions and every REJECTED or abandoned STAGED one. Publications are
        projections rebuilt from the domain packages, never the analytical record, so nothing unique is
        lost. VACUUM then makes the freed space reusable by the next publication (Neon counts the files,
        and a plain VACUUM does not shrink them, but new rows fill the freed pages instead of growing them).
        """
        if keep_superseded < 1:
            raise ValueError("keep at least one superseded publication for rollback")
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("""
                SELECT publication_id FROM presentation_publications
                WHERE publication_status <> 'ACTIVE'
                  AND publication_id NOT IN (SELECT publication_id FROM presentation_active_publication)
                  AND publication_id NOT IN (
                      SELECT publication_id FROM presentation_publications
                      WHERE publication_status = 'SUPERSEDED'
                      ORDER BY published_at_utc DESC, publication_id DESC LIMIT %s)
            """, (keep_superseded,))
            doomed = [row[0] for row in cursor.fetchall()]
            records = 0
            for publication_id in doomed:
                cursor.execute("DELETE FROM presentation_records WHERE publication_id=%s", (publication_id,))
                records += max(cursor.rowcount, 0)
                cursor.execute("DELETE FROM presentation_publications WHERE publication_id=%s", (publication_id,))
        vacuumed = False
        if doomed:
            db = self._connection_factory()
            try:
                db.autocommit = True                      # VACUUM cannot run inside a transaction
                with db.cursor() as cursor:
                    cursor.execute("VACUUM (ANALYZE) presentation_records")
                    cursor.execute("VACUUM (ANALYZE) presentation_publications")
                vacuumed = True
            except Exception:                             # space is still reclaimed later by autovacuum
                vacuumed = False
            finally:
                db.close()
        return {"publications_deleted": len(doomed), "records_deleted": records, "vacuumed": vacuumed}

    def active_metadata(self) -> dict[str, object] | None:
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute("""
                SELECT p.publication_id, p.publication_version,
                       p.source_database_sha256, p.source_database_classification,
                       p.published_at_utc, p.publication_status,
                       p.content_fingerprint, p.record_count, a.activated_at_utc
                FROM presentation_active_publication a
                JOIN presentation_publications p USING (publication_id)
                WHERE a.singleton_id=1
            """)
            row = cursor.fetchone()
        if row is None:
            return None
        keys = (
            "publication_id", "publication_version", "source_database_sha256",
            "source_database_classification", "published_at_utc", "publication_status",
            "content_fingerprint", "record_count", "activated_at_utc",
        )
        return dict(zip(keys, row))
