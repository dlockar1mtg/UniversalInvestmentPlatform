"""Publish a governed rich UIP candidate from explicitly resolved source artifacts.

The caller supplies exact source artifacts and run identifiers. All rich sources are
validated and the complete presentation candidate is built and certified in a temporary
DuckDB before any PostgreSQL connection is opened. Scheduled automation therefore stays
fail-closed: a source-resolution or validation failure cannot replace the active state.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import duckdb

from foundation.import_engine.audit import apply_audit_registry_migration
from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.presentation.metals_rich_projection import build_metals_rich_records
from foundation.presentation.postgres_read_model import PostgresPresentationRepository
from foundation.presentation.publication_model import PresentationPublication, build_presentation_publication
from foundation.presentation.publication_service import publish_presentation_bundle, validate_publication_bundle
from foundation.presentation.rich_candidate_composition import compose_rich_candidate
from scripts.publish_latest_domain_artifacts import (
    assert_required_presentation_surfaces,
    find_package,
    import_mtg,
    import_universal_package,
    sha256,
)
from scripts.rehearse_rich_publication_candidate import (
    MTG_RICH_EXPECTED_COUNTS,
    assert_unique_records,
    configure_mtg_sidecars,
    expected_metals_counts,
)

CONFIRMATION = "PUBLISH_REHEARSED_RICH_CANDIDATE"
EXPECTED_GENERIC_COUNTS = {
    "crypto": {
        "asset": 6,
        "domain_health": 1,
        "forecast": 129,
        "recommendation": 6,
        "risk": 6,
    },
    "metals": {
        "asset": 9,
        "domain_health": 1,
        "forecast": 27,
        "recommendation": 9,
    },
    "mtg": {
        "asset": 968,
        "domain_health": 1,
        "native_authority": 968,
        "recommendation": 968,
    },
}


def git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--crypto-artifact", type=Path, required=True)
    parser.add_argument("--metals-artifact", type=Path, required=True)
    parser.add_argument("--mtg-artifact", type=Path, required=True)
    parser.add_argument("--mtg-repo", type=Path, required=True)
    parser.add_argument("--expected-mtg-head", required=True)
    parser.add_argument("--crypto-source-run-id", required=True)
    parser.add_argument("--metals-source-run-id", required=True)
    parser.add_argument("--mtg-source-run-id", required=True)
    parser.add_argument("--expected-record-count", type=int, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args()

    if args.confirm != CONFIRMATION:
        raise RuntimeError("Exact rich-publication confirmation token was not provided")

    dsn = os.getenv("UIIP_DATABASE_URL", "").strip()
    if not dsn:
        raise RuntimeError("UIIP_DATABASE_URL is required")

    artifact_roots = {
        "crypto": args.crypto_artifact.resolve(),
        "metals": args.metals_artifact.resolve(),
        "mtg": args.mtg_artifact.resolve(),
    }
    for domain, root in artifact_roots.items():
        if not root.is_dir():
            raise RuntimeError(f"{domain} artifact root is missing: {root}")

    mtg_repo = args.mtg_repo.resolve()
    if not mtg_repo.is_dir():
        raise RuntimeError(f"MTG repository checkout is missing: {mtg_repo}")
    observed_mtg_head = git_head(mtg_repo)
    if observed_mtg_head != args.expected_mtg_head:
        raise RuntimeError(
            f"MTG authority head drifted: expected={args.expected_mtg_head} observed={observed_mtg_head}"
        )

    mtg_sidecars = configure_mtg_sidecars(mtg_repo)

    # Everything through this block is local-only. No PostgreSQL connection is opened.
    with tempfile.TemporaryDirectory(prefix="uip-rich-production-candidate-") as temp_name:
        temp_root = Path(temp_name)
        config = ImportEngineConfig(
            repository_root=ROOT,
            database_path=temp_root / "universal_investment.duckdb",
            schema_root=ROOT / "schemas" / "v1" / "csv",
            integration_root=temp_root / "integration",
            validation_root=temp_root / "validation",
        )
        initialize_database(config)
        apply_audit_registry_migration(config)

        crypto_package = find_package(artifact_roots["crypto"], "crypto")
        metals_package = find_package(artifact_roots["metals"], "metals")
        mtg_package = find_package(artifact_roots["mtg"], "mtg")

        imports = [
            import_universal_package(config, crypto_package, "crypto"),
            import_universal_package(config, metals_package, "metals"),
            import_mtg(config, mtg_package, mtg_repo),
        ]

        database_hash = sha256(config.database_path)
        now = datetime.now(timezone.utc)
        publication_id = f"uip-rich-production-{now.strftime('%Y%m%dT%H%M%SZ')}-{database_hash[:12]}"

        duck = duckdb.connect(str(config.database_path), read_only=True)
        try:
            base = build_presentation_publication(
                ROOT,
                config.database_path,
                duck,
                publication_id=publication_id,
                published_at_utc=now.isoformat(),
            )
        finally:
            duck.close()

        publication = compose_rich_candidate(
            base, artifact_roots["crypto"], artifact_roots["metals"], ROOT
        )

        validate_publication_bundle(publication)
        generic_counts = assert_required_presentation_surfaces(publication)
        assert_unique_records(publication)

        if generic_counts != EXPECTED_GENERIC_COUNTS:
            raise RuntimeError(
                f"Generic presentation counts drifted from rehearsed candidate: {generic_counts}"
            )

        counts = Counter((record.domain_id, record.record_type) for record in publication.records)
        metals_expected = expected_metals_counts(artifact_roots["metals"])
        metals_observed = {
            record_type: counts[("metals", record_type)]
            for record_type in metals_expected
        }
        mtg_observed = {
            record_type: counts[("mtg", record_type)]
            for record_type in MTG_RICH_EXPECTED_COUNTS
        }
        crypto_current_price_count = counts[("crypto", "crypto_current_price")]
        if crypto_current_price_count != 6:
            raise RuntimeError(f"Crypto current-price count drifted: {crypto_current_price_count}")
        if counts[("metals", "metals_vehicle_implementation")] != 10:
            raise RuntimeError("Metals implementation count drifted")
        if metals_observed != metals_expected:
            raise RuntimeError(
                f"Metals rich presentation counts drifted: {metals_observed} != {metals_expected}"
            )
        if mtg_observed != MTG_RICH_EXPECTED_COUNTS:
            raise RuntimeError(
                f"MTG rich presentation counts drifted: {mtg_observed} != {MTG_RICH_EXPECTED_COUNTS}"
            )
        if len(publication.records) != args.expected_record_count:
            raise RuntimeError(
                "Rich publication candidate record count drifted: "
                f"expected={args.expected_record_count} observed={len(publication.records)}"
            )

        preactivation = {
            "status": "RICH_CANDIDATE_PREACTIVATION_GATE_PASS",
            "record_count": len(publication.records),
            "content_fingerprint": publication.content_fingerprint,
            "generic_surface_counts": generic_counts,
            "metals_rich_record_counts": metals_observed,
            "crypto_current_price_record_count": crypto_current_price_count,
            "mtg_rich_record_counts": mtg_observed,
            "mtg_head": observed_mtg_head,
            "source_run_ids": {
                "crypto": args.crypto_source_run_id,
                "metals": args.metals_source_run_id,
                "mtg": args.mtg_source_run_id,
            },
            "postgres_connection_opened": False,
            "publication_persisted": False,
            "publication_activated": False,
        }

        # PostgreSQL is opened only after the complete rich candidate passes every gate.
        store = PostgresPresentationRepository.from_dsn(dsn)
        store.initialize()
        previous = store.active_metadata()
        result = publish_presentation_bundle(store, publication)
        active = store.active_metadata()
        if result.status != "ACTIVE" or not active or active.get("publication_id") != publication_id:
            raise RuntimeError("Validated rich publication did not become the active PostgreSQL publication")

        evidence = {
            "status": "UIP_RICH_PRODUCTION_PUBLICATION_PASS",
            "published_at_utc": now.isoformat(),
            "publication_id": publication_id,
            "content_fingerprint": publication.content_fingerprint,
            "source_database_sha256": database_hash,
            "record_count": len(publication.records),
            "crypto_current_price_record_count": crypto_current_price_count,
            "previous_active_publication_id": None if not previous else previous.get("publication_id"),
            "active_publication_id": active.get("publication_id"),
            "imports": imports,
            "preactivation_gate": preactivation,
            "mtg_sidecar_paths": mtg_sidecars,
            "postgres_connection_opened_after_full_validation": True,
            "publication_persisted": True,
            "publication_activated": True,
            "automatic_schedule_modified": os.getenv("UIIP_AUTOMATED_PUBLICATION", "").strip() == "1",
            "failure_policy": "NO_POSTGRES_CONNECTION_UNTIL_GOVERNED_SOURCE_CONTRACTS_COUNTS_AND_AUTHORITIES_PASS",
        }

    output = args.evidence_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    print("UIP_RICH_PRODUCTION_PUBLICATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
