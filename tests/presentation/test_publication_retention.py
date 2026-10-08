"""Publication retention: old presentation versions are pruned so the hosted database stays under its limit.

Runs against a real PostgreSQL when UIIP_TEST_POSTGRES_DSN is set (CI and local); skipped otherwise.
"""
from __future__ import annotations

import os
from contextlib import closing
from datetime import datetime, timedelta, timezone

import pytest

from foundation.presentation.postgres_read_model import PostgresPresentationRepository

DSN = os.environ.get("UIIP_TEST_POSTGRES_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="set UIIP_TEST_POSTGRES_DSN to run against PostgreSQL")


@pytest.fixture
def store():
    psycopg = pytest.importorskip("psycopg")
    with closing(psycopg.connect(DSN)) as db, db, db.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS presentation_active_publication, presentation_records, presentation_publications")
    repo = PostgresPresentationRepository.from_dsn(DSN)
    repo.initialize()
    return repo, psycopg


def _add(psycopg, pid, status, minutes):
    at = datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=minutes)
    with closing(psycopg.connect(DSN)) as db, db, db.cursor() as cur:
        cur.execute("""INSERT INTO presentation_publications (publication_id, publication_version, source_database_sha256,
                       source_database_classification, published_at_utc, publication_status, content_fingerprint, record_count)
                       VALUES (%s,'1','x','x',%s,%s,'f',2)""", (pid, at, status))
        for k in range(2):
            cur.execute("INSERT INTO presentation_records VALUES (%s,'asset','crypto',NULL,%s,'{\"a\":1}'::jsonb)", (pid, f"k{k}"))
        if status == "ACTIVE":
            cur.execute("INSERT INTO presentation_active_publication (singleton_id, publication_id) VALUES (1,%s)", (pid,))


def test_keeps_the_active_and_two_newest_superseded(store):
    repo, psycopg = store
    for i in range(6):
        _add(psycopg, f"old{i}", "SUPERSEDED", i)
    _add(psycopg, "bad", "REJECTED", 7)
    _add(psycopg, "stuck", "STAGED", 8)
    _add(psycopg, "live", "ACTIVE", 9)
    out = repo.prune(keep_superseded=2)
    assert out["publications_deleted"] == 6 and out["records_deleted"] == 12 and out["vacuumed"] is True
    with closing(psycopg.connect(DSN)) as db, db.cursor() as cur:
        cur.execute("SELECT publication_id FROM presentation_publications ORDER BY publication_id")
        assert [r[0] for r in cur.fetchall()] == ["live", "old4", "old5"]
        cur.execute("SELECT COUNT(*) FROM presentation_records")
        assert cur.fetchone()[0] == 6
    assert repo.active_metadata()["publication_id"] == "live"
    assert repo.prune(keep_superseded=2)["publications_deleted"] == 0


def test_refuses_to_keep_no_rollback(store):
    repo, _ = store
    with pytest.raises(ValueError):
        repo.prune(keep_superseded=0)
