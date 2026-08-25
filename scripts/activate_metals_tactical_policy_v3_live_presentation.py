from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.presentation.postgres_read_model import PostgresPresentationRepository
from foundation.presentation.publication_model import build_presentation_publication, sha256_file
from foundation.presentation.publication_service import publish_presentation_bundle, validate_publication_bundle

AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_fresh_live_presentation_activation_authorization.json"
EXPECTED_AUTHORIZATION_ID = "METALS-TACTICAL-POLICY-V3-FRESH-LIVE-PRESENTATION-ACTIVATION-AUTHORIZATION-1"
EXPECTED_AUTHORIZATION_DECISION = "AUTHORIZE_ONE_FRESH_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION"
EXPECTED_PUBLICATION_ID = "metals-v3-live-tactical-r2-20260825"
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_FINGERPRINT = "21a3e3c8a1e73b7370d23f0704081f7ac01f28609bed22f94d00d4f4c2e7c126"
EXPECTED_RECORD_COUNT = 4181
EXPECTED_TACTICAL_COUNT = 10


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--database", required=True)
    p.add_argument("--publication-id", default=EXPECTED_PUBLICATION_ID)
    p.add_argument("--authorization", default=str(AUTH_PATH))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    database = Path(args.database).resolve()
    authorization_path = Path(args.authorization).resolve()
    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is not available in this process.")
    if args.publication_id != EXPECTED_PUBLICATION_ID:
        raise RuntimeError("Unexpected fresh target publication ID.")
    auth = json.loads(authorization_path.read_text(encoding="utf-8"))
    if auth.get("authorization_id") != EXPECTED_AUTHORIZATION_ID:
        raise RuntimeError("Unexpected fresh live activation authorization ID.")
    if auth.get("authorization_decision") != EXPECTED_AUTHORIZATION_DECISION:
        raise RuntimeError("Fresh live activation is not authorized.")
    if auth.get("fresh_target_publication_id") != EXPECTED_PUBLICATION_ID:
        raise RuntimeError("Fresh authorization target publication ID changed.")
    if auth.get("consumed_prior_authorization_may_be_reused") is not False:
        raise RuntimeError("Consumed prior authorization became reusable.")
    if auth.get("failed_prior_publication_id_may_be_reused") is not False:
        raise RuntimeError("Failed prior publication ID became reusable.")
    if int(auth.get("execution_limit", 0)) != 1 or auth.get("execution_is_one_time") is not True:
        raise RuntimeError("Fresh live activation authorization is not one bounded execution.")
    actual_sha = sha256_file(database)
    if actual_sha != EXPECTED_DB_SHA or auth.get("source_database_sha256") != EXPECTED_DB_SHA:
        raise RuntimeError("Authoritative DuckDB SHA does not match certified fresh activation authority.")
    if auth.get("certified_content_fingerprint") != EXPECTED_FINGERPRINT:
        raise RuntimeError("Fresh authorization fingerprint changed.")
    if int(auth.get("certified_record_count", -1)) != EXPECTED_RECORD_COUNT:
        raise RuntimeError("Fresh authorization record count changed.")
    if int(auth.get("certified_metals_tactical_state_count", -1)) != EXPECTED_TACTICAL_COUNT:
        raise RuntimeError("Fresh authorization tactical-state count changed.")
    with duckdb.connect(str(database), read_only=True) as connection:
        publication = build_presentation_publication(
            ROOT,
            database,
            connection,
            publication_id=args.publication_id,
        )
    validate_publication_bundle(publication)
    tactical = [r for r in publication.records if r.record_type == "tactical_state" and r.domain_id == "metals"]
    if publication.content_fingerprint != EXPECTED_FINGERPRINT:
        raise RuntimeError("Built publication fingerprint does not match certified non-active publication.")
    if len(publication.records) != EXPECTED_RECORD_COUNT:
        raise RuntimeError("Built publication record count changed.")
    if len(tactical) != EXPECTED_TACTICAL_COUNT:
        raise RuntimeError("Built tactical-state count changed.")
    if any(dict(r.payload).get("is_reference_control") is True for r in tactical):
        raise RuntimeError("Reference/control row entered tactical opportunity projection.")
    store = PostgresPresentationRepository.from_dsn(dsn)
    store.initialize()
    previous = store.active_metadata()
    result = publish_presentation_bundle(store, publication)
    active = store.active_metadata()
    if not active or active.get("publication_id") != publication.publication_id:
        raise RuntimeError("New presentation publication did not become active.")
    if active.get("source_database_sha256") != EXPECTED_DB_SHA:
        raise RuntimeError("Active publication source SHA changed.")
    if active.get("content_fingerprint") != EXPECTED_FINGERPRINT:
        raise RuntimeError("Active publication fingerprint changed.")
    if int(active.get("record_count", -1)) != EXPECTED_RECORD_COUNT:
        raise RuntimeError("Active publication record count changed.")
    print(json.dumps({
        "status": "PASS",
        "publication_id": publication.publication_id,
        "previous_active_publication_id": None if previous is None else previous.get("publication_id"),
        "active_publication_id": active.get("publication_id"),
        "source_database_sha256": active.get("source_database_sha256"),
        "content_fingerprint": active.get("content_fingerprint"),
        "record_count": int(active.get("record_count")),
        "metals_tactical_state_count": len(tactical),
        "activation_status": result.status,
        "analytical_database_write": False,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
