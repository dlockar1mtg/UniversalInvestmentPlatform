"""Package status: the small ETF/housing/macro freshness summary served to Vitals and the Hall.

Runs against a real PostgreSQL when UIIP_TEST_POSTGRES_DSN is set (CI and local); skipped otherwise.
"""
from __future__ import annotations

import json
import os
from contextlib import closing

import pytest

from foundation.presentation.postgres_read_model import PostgresPresentationRepository
from foundation.presentation.read_api import PresentationReadRepository

DSN = os.environ.get("UIIP_TEST_POSTGRES_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="set UIIP_TEST_POSTGRES_DSN to run against PostgreSQL")


def test_package_status_summarises_each_package_and_current_funds():
    psycopg = pytest.importorskip("psycopg")
    with closing(psycopg.connect(DSN)) as db, db, db.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS presentation_active_publication, presentation_records, presentation_publications")
    PostgresPresentationRepository.from_dsn(DSN).initialize()
    rows = [
        ("etf_package", "etf", "etf-universe", {"generated_at_utc": "2026-10-09T23:00:00Z", "package_id": "etf-1", "fund_count": 3}),
        ("etf_fund", "etf", "VOO", {"freshness_state": "CURRENT", "history_daily": [1, 2]}),
        ("etf_fund", "etf", "QQQM", {"freshness_state": "CURRENT"}),
        ("etf_fund", "etf", "OLD", {"freshness_state": "STALE"}),
        ("housing_package", "housing", "housing-markets", {"generated_at_utc": "2026-10-09T23:52:00Z", "latest_input_observation": "2026-10-08", "market_count": 2}),
        ("macro_package", "macro", "macro-rsi", {"generated_at_utc": "2026-10-09T23:49:00Z", "data_quality": {"status": "OK"}, "history": [1] * 50}),
    ]
    with closing(psycopg.connect(DSN)) as db, db, db.cursor() as cur:
        cur.execute("""INSERT INTO presentation_publications (publication_id, publication_version, source_database_sha256,
                       source_database_classification, published_at_utc, publication_status, content_fingerprint, record_count)
                       VALUES ('p1','1','x','x',now(),'ACTIVE','f',6)""")
        for kind, domain, key, payload in rows:
            cur.execute("INSERT INTO presentation_records VALUES ('p1',%s,%s,NULL,%s,%s::jsonb)", (kind, domain, key, json.dumps(payload)))
        cur.execute("INSERT INTO presentation_active_publication (singleton_id, publication_id) VALUES (1,'p1')")
    status = PresentationReadRepository.from_dsn(DSN).package_status()
    assert status["etf"]["funds"] == 3 and status["etf"]["current_funds"] == 2 and status["etf"]["package_id"] == "etf-1"
    assert status["housing"]["latest_input_observation"] == "2026-10-08" and status["housing"]["market_count"] == 2
    assert status["macro"]["data_quality"] == "OK" and status["macro"]["generated_at_utc"].startswith("2026-10-09")
