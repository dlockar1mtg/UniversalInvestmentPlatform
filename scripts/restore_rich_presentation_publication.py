"""Restore the retained rich UIP presentation publication after a certified regression audit.

This command is intentionally hard-locked to the exact pre-regression publication
identified by the 2026-09-09 read-only inventory audit. It validates retained metadata,
record counts, and rich MTG/Metals sentinel surfaces inside one PostgreSQL transaction
before atomically switching the active presentation pointer.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import psycopg

TARGET_PUBLICATION_ID = "mtg-lane-native-detail-enrichment-a71e6025c44e"
TARGET_CONTENT_FINGERPRINT = "11e69cb36d83a4fa8562c0e7bab6c7c1ed685e9d78f1cc7058772823084f031e"
TARGET_SOURCE_DATABASE_SHA256 = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
TARGET_RECORD_COUNT = 13929
EXPECTED_CURRENT_ACTIVE_ID = "uip-production-20260909T114650Z-16445e77b711"

# These sentinels are taken directly from the 2026-09-09 read-only inventory
# for TARGET_PUBLICATION_ID. Do not substitute record types from earlier Metals
# publications (for example, metals_momentum_state), because the rich target
# publication uses the later tactical_state contract instead.
EXPECTED_SENTINELS = {
    ("mtg", "mtg_premium_research"): 787,
    ("mtg", "mtg_collector_research"): 50,
    ("mtg", "mtg_collector_forecast_horizon"): 294,
    ("mtg", "mtg_precollector_research"): 131,
    ("mtg", "mtg_precollector_scenario_horizon"): 190,
    ("mtg", "native_authority"): 968,
    ("metals", "tactical_state"): 10,
    ("metals", "risk"): 11,
    ("metals", "metals_price_history"): 8283,
    ("metals", "metals_current_price"): 11,
    ("metals", "metals_data_freshness"): 21,
    ("metals", "metals_model_component"): 64,
    ("metals", "metals_platform_health"): 1,
    ("metals", "metals_recommendation_change"): 10,
    ("metals", "metals_regime_probability"): 12,
    ("metals", "metals_uncertainty_adjusted"): 32,
    ("metals", "metals_commodity_decision_explanation"): 2,
    ("crypto", "asset"): 6,
    ("crypto", "risk"): 6,
}


def fetch_count(cur, domain_id: str, record_type: str) -> int:
    cur.execute(
        """
        SELECT COUNT(*)
        FROM presentation_records
        WHERE publication_id=%s AND domain_id=%s AND record_type=%s
        """,
        (TARGET_PUBLICATION_ID, domain_id, record_type),
    )
    return int(cur.fetchone()[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.confirm != "RESTORE_RICH_PRESENTATION":
        raise RuntimeError("Explicit confirmation token is incorrect")

    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    evidence: dict[str, object] = {
        "status": "STARTED",
        "target_publication_id": TARGET_PUBLICATION_ID,
        "expected_current_active_publication_id": EXPECTED_CURRENT_ACTIVE_ID,
    }

    with psycopg.connect(dsn) as db:
        with db.cursor() as cur:
            cur.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")

            cur.execute(
                """
                SELECT a.publication_id, p.publication_status
                FROM presentation_active_publication a
                JOIN presentation_publications p USING (publication_id)
                WHERE a.singleton_id=1
                FOR UPDATE
                """
            )
            current = cur.fetchone()
            if current is None:
                raise RuntimeError("No active presentation publication exists")
            current_id, current_status = str(current[0]), str(current[1])
            if current_id != EXPECTED_CURRENT_ACTIVE_ID or current_status != "ACTIVE":
                raise RuntimeError(
                    f"Active publication changed unexpectedly: {current_id} status={current_status}"
                )

            cur.execute(
                """
                SELECT publication_status, content_fingerprint, source_database_sha256, record_count
                FROM presentation_publications
                WHERE publication_id=%s
                FOR UPDATE
                """,
                (TARGET_PUBLICATION_ID,),
            )
            target = cur.fetchone()
            if target is None:
                raise RuntimeError("Target retained publication is missing")
            target_status, fingerprint, source_sha, declared_count = target
            if str(target_status) != "SUPERSEDED":
                raise RuntimeError(f"Target status is not SUPERSEDED: {target_status}")
            if str(fingerprint) != TARGET_CONTENT_FINGERPRINT:
                raise RuntimeError("Target content fingerprint changed")
            if str(source_sha) != TARGET_SOURCE_DATABASE_SHA256:
                raise RuntimeError("Target source database SHA changed")
            if int(declared_count) != TARGET_RECORD_COUNT:
                raise RuntimeError(f"Target declared record count changed: {declared_count}")

            cur.execute(
                "SELECT COUNT(*) FROM presentation_records WHERE publication_id=%s",
                (TARGET_PUBLICATION_ID,),
            )
            actual_count = int(cur.fetchone()[0])
            if actual_count != TARGET_RECORD_COUNT:
                raise RuntimeError(f"Target actual record count changed: {actual_count}")

            observed: dict[str, int] = {}
            for (domain_id, record_type), expected in EXPECTED_SENTINELS.items():
                actual = fetch_count(cur, domain_id, record_type)
                observed[f"{domain_id}/{record_type}"] = actual
                if actual != expected:
                    raise RuntimeError(
                        f"Sentinel mismatch {domain_id}/{record_type}: expected {expected}, observed {actual}"
                    )

            cur.execute(
                """
                UPDATE presentation_publications
                SET publication_status='SUPERSEDED'
                WHERE publication_id=%s AND publication_status='ACTIVE'
                """,
                (current_id,),
            )
            if cur.rowcount != 1:
                raise RuntimeError("Could not supersede current regressed publication")

            cur.execute(
                """
                UPDATE presentation_publications
                SET publication_status='ACTIVE', failure_reason=NULL
                WHERE publication_id=%s AND publication_status='SUPERSEDED'
                """,
                (TARGET_PUBLICATION_ID,),
            )
            if cur.rowcount != 1:
                raise RuntimeError("Could not mark retained rich publication ACTIVE")

            cur.execute(
                """
                UPDATE presentation_active_publication
                SET publication_id=%s, activated_at_utc=CURRENT_TIMESTAMP
                WHERE singleton_id=1
                """,
                (TARGET_PUBLICATION_ID,),
            )
            if cur.rowcount != 1:
                raise RuntimeError("Could not switch active publication pointer")

            cur.execute(
                """
                SELECT a.publication_id, p.publication_status, p.record_count
                FROM presentation_active_publication a
                JOIN presentation_publications p USING (publication_id)
                WHERE a.singleton_id=1
                """
            )
            verified = cur.fetchone()
            if verified is None:
                raise RuntimeError("Post-restore active publication verification returned no row")
            verified_id, verified_status, verified_count = verified
            if (
                str(verified_id) != TARGET_PUBLICATION_ID
                or str(verified_status) != "ACTIVE"
                or int(verified_count) != TARGET_RECORD_COUNT
            ):
                raise RuntimeError(f"Post-restore verification failed: {verified}")

            evidence.update(
                {
                    "status": "UIP_RICH_PRESENTATION_RESTORE_PASS",
                    "previous_active_publication_id": current_id,
                    "active_publication_id": str(verified_id),
                    "active_record_count": int(verified_count),
                    "target_content_fingerprint": TARGET_CONTENT_FINGERPRINT,
                    "target_source_database_sha256": TARGET_SOURCE_DATABASE_SHA256,
                    "sentinel_counts": observed,
                    "transaction_policy": "SERIALIZABLE_ATOMIC_POINTER_RESTORE_AFTER_EXACT_SENTINEL_VALIDATION",
                }
            )

    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    print("UIP_RICH_PRESENTATION_RESTORE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
