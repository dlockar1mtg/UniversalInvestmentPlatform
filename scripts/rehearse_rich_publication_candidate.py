"""Build and validate a complete rich publication candidate without PostgreSQL persistence.

The rehearsal consumes the latest certified domain artifacts, uses a temporary local
DuckDB import database, binds the already-certified MTG research sidecars explicitly,
projects the ten certified Metals rich families and the governed Metals vehicle
implementation records explicitly, and stops before any staging or activation against
PostgreSQL.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
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
from foundation.presentation.crypto_current_price_projection import (
    RECORD_TYPE as CRYPTO_CURRENT_PRICE_RECORD_TYPE,
    build_crypto_current_price_records,
)
from foundation.presentation.metals_rich_projection import (
    FAMILY_PROJECTION,
    build_metals_rich_records,
)
from foundation.presentation.metals_vehicle_implementation_projection import (
    ONLY_LABEL,
    PREFERRED_LABEL,
    RECORD_TYPE as METALS_VEHICLE_IMPLEMENTATION_RECORD_TYPE,
    build_metals_vehicle_implementation_records,
)
from foundation.presentation.publication_model import (
    PresentationPublication,
    build_presentation_publication,
)
from foundation.presentation.publication_service import validate_publication_bundle
from scripts.audit_rich_publication_source_contract import NATIVE_METALS_CERTIFIED_CONTRACTS
from scripts.publish_latest_domain_artifacts import (
    assert_required_presentation_surfaces,
    find_package,
    import_mtg,
    import_universal_package,
)

MTG_RICH_EXPECTED_COUNTS = {
    "mtg_premium_research": 787,
    "mtg_collector_research": 50,
    "mtg_collector_forecast_horizon": 294,
    "mtg_precollector_research": 131,
    "mtg_precollector_scenario_horizon": 190,
}

MTG_ENV_PATHS = {
    "UIP_MTG_PREMIUM_SIDECAR_PATH": "docs/phase_9/uip_export/premium_research/mtg_secret_lair_premium_research.csv",
    "UIP_MTG_COLLECTOR_RESEARCH_PATH": "docs/phase_9/uip_export/research_sidecars/mtg_collector_research.csv",
    "UIP_MTG_COLLECTOR_HORIZON_RESEARCH_PATH": "docs/phase_9/uip_export/research_sidecars/mtg_collector_forecast_horizon.csv",
    "UIP_MTG_PRECOLLECTOR_RESEARCH_PATH": "docs/phase_9/uip_export/research_sidecars/mtg_precollector_research.csv",
    "UIP_MTG_PRECOLLECTOR_SCENARIO_RESEARCH_PATH": "docs/phase_9/uip_export/research_sidecars/mtg_precollector_scenario_horizon.csv",
}


def csv_rows(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.reader(handle)) - 1


def configure_mtg_sidecars(mtg_repo: Path) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for env_name, relative in MTG_ENV_PATHS.items():
        path = (mtg_repo / relative).resolve()
        if not path.is_file():
            raise RuntimeError(f"Certified MTG rich sidecar is missing: {path}")
        os.environ[env_name] = str(path)
        resolved[env_name] = str(path)
    return resolved


def expected_metals_counts(root: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for family, projection in FAMILY_PROJECTION.items():
        spec = NATIVE_METALS_CERTIFIED_CONTRACTS[family]
        counts[str(projection["record_type"])] = csv_rows(root / str(spec["csv"]))
    return counts


def assert_unique_records(publication: PresentationPublication) -> None:
    identities = [
        (record.domain_id, record.record_type, record.asset_id, record.record_key)
        for record in publication.records
    ]
    if len(identities) != len(set(identities)):
        duplicates = [item for item, count in Counter(identities).items() if count > 1]
        raise RuntimeError(f"Candidate publication contains duplicate record identities: {duplicates[:20]}")


def assert_metals_vehicle_implementation_semantics(records) -> dict[str, object]:
    rows = [record for record in records if record.record_type == METALS_VEHICLE_IMPLEMENTATION_RECORD_TYPE]
    if len(rows) != 10:
        raise RuntimeError(f"Expected exactly 10 Metals vehicle implementation records, observed {len(rows)}")

    by_commodity: dict[str, list] = {}
    for record in rows:
        if record.domain_id != "metals":
            raise RuntimeError("Metals vehicle implementation record has wrong domain")
        if not record.asset_id:
            raise RuntimeError("Metals vehicle implementation record is missing commodity identity")
        by_commodity.setdefault(record.asset_id, []).append(record)

    expected_orders = {
        "metals:commodity:gold": ["GLD", "SGOL", "IAU"],
        "metals:commodity:silver": ["SLV", "SIVR"],
        "metals:commodity:platinum": ["PPLT"],
        "metals:commodity:copper": ["COPX", "CPER"],
        "metals:commodity:uranium": ["URA", "URNM"],
    }
    if set(by_commodity) != set(expected_orders):
        raise RuntimeError(f"Unexpected Metals implementation commodity set: {sorted(by_commodity)}")

    summary: dict[str, object] = {}
    for commodity_id, expected in expected_orders.items():
        ordered = sorted(
            by_commodity[commodity_id],
            key=lambda record: int(record.payload["certified_rank_within_commodity"]),
        )
        tickers = [str(record.payload["ticker"]) for record in ordered]
        if tickers != expected:
            raise RuntimeError(f"Metals implementation order mismatch for {commodity_id}: {tickers} != {expected}")
        labels = {
            str(record.payload["ticker"]): record.payload.get("presentation_label")
            for record in ordered
        }
        summary[commodity_id] = {"order": tickers, "labels": labels}

    if summary["metals:commodity:gold"]["labels"]["GLD"] != PREFERRED_LABEL:
        raise RuntimeError("Gold preferred implementation label is not GLD")
    if summary["metals:commodity:copper"]["labels"]["COPX"] != PREFERRED_LABEL:
        raise RuntimeError("Copper preferred implementation label is not COPX")
    if summary["metals:commodity:uranium"]["labels"]["URA"] != PREFERRED_LABEL:
        raise RuntimeError("Uranium preferred implementation label is not URA")
    if summary["metals:commodity:platinum"]["labels"]["PPLT"] != ONLY_LABEL:
        raise RuntimeError("Platinum only-registered implementation label is not PPLT")
    if any(label == PREFERRED_LABEL for label in summary["metals:commodity:silver"]["labels"].values()):
        raise RuntimeError("Defensive Silver received a preferred implementation label")

    for record in rows:
        if record.payload.get("automatic_execution_authorized") is not False:
            raise RuntimeError("Vehicle implementation rehearsal refuses automatic execution authority")
        if record.payload.get("central_publication_cron_restoration_authorized") is not False:
            raise RuntimeError("Vehicle implementation rehearsal refuses cron restoration authority")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crypto-artifact", type=Path, required=True)
    parser.add_argument("--metals-artifact", type=Path, required=True)
    parser.add_argument("--mtg-artifact", type=Path, required=True)
    parser.add_argument("--mtg-repo", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args()

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

    mtg_sidecars = configure_mtg_sidecars(mtg_repo)

    with tempfile.TemporaryDirectory(prefix="uip-rich-candidate-") as temp_name:
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

        duck = duckdb.connect(str(config.database_path), read_only=True)
        try:
            base = build_presentation_publication(
                config.repository_root,
                config.database_path,
                duck,
                publication_id="rich-publication-candidate-rehearsal",
                published_at_utc=datetime.now(timezone.utc).isoformat(),
            )
        finally:
            duck.close()

        crypto_current_price = build_crypto_current_price_records(artifact_roots["crypto"])
        metals_rich = build_metals_rich_records(artifact_roots["metals"])
        metals_vehicle_implementation = build_metals_vehicle_implementation_records(config.repository_root)
        combined = (
            list(base.records)
            + list(crypto_current_price)
            + metals_rich
            + metals_vehicle_implementation
        )
        combined.sort(key=lambda item: (item.record_type, item.domain_id, item.asset_id or "", item.record_key))
        candidate = PresentationPublication(
            publication_id=base.publication_id,
            publication_version=base.publication_version,
            source_database_sha256=base.source_database_sha256,
            source_database_classification=base.source_database_classification,
            published_at_utc=base.published_at_utc,
            publication_status="STAGED",
            records=tuple(combined),
        )

        validate_publication_bundle(candidate)
        generic_surface_counts = assert_required_presentation_surfaces(candidate)
        assert_unique_records(candidate)
        vehicle_implementation_summary = assert_metals_vehicle_implementation_semantics(candidate.records)

        counts = Counter((record.domain_id, record.record_type) for record in candidate.records)
        metals_expected = expected_metals_counts(artifact_roots["metals"])
        observed_metals = {record_type: counts[("metals", record_type)] for record_type in metals_expected}
        observed_mtg = {record_type: counts[("mtg", record_type)] for record_type in MTG_RICH_EXPECTED_COUNTS}
        implementation_count = counts[("metals", METALS_VEHICLE_IMPLEMENTATION_RECORD_TYPE)]
        crypto_current_price_count = counts[("crypto", CRYPTO_CURRENT_PRICE_RECORD_TYPE)]

        if crypto_current_price_count != 6:
            raise RuntimeError(
                "Crypto current-price candidate count must be 6, "
                f"observed {crypto_current_price_count}"
            )
        if observed_metals != metals_expected:
            raise RuntimeError(f"Metals rich candidate counts do not match certified inputs: {observed_metals} != {metals_expected}")
        if observed_mtg != MTG_RICH_EXPECTED_COUNTS:
            raise RuntimeError(f"MTG rich candidate counts do not match certified inputs: {observed_mtg} != {MTG_RICH_EXPECTED_COUNTS}")
        if implementation_count != 10:
            raise RuntimeError(f"Metals vehicle implementation candidate count must be 10, observed {implementation_count}")
        if candidate.publication_status != "STAGED":
            raise RuntimeError("Candidate publication did not remain STAGED in memory")

        evidence = {
            "status": "UIP_RICH_PUBLICATION_CANDIDATE_REHEARSAL_PASS",
            "publication_id": candidate.publication_id,
            "publication_status": candidate.publication_status,
            "record_count": len(candidate.records),
            "content_fingerprint": candidate.content_fingerprint,
            "source_database_sha256": candidate.source_database_sha256,
            "imports": imports,
            "generic_surface_counts": generic_surface_counts,
            "crypto_current_price_record_count": crypto_current_price_count,
            "metals_rich_family_count": len(metals_expected),
            "metals_rich_record_counts": observed_metals,
            "metals_vehicle_implementation_record_count": implementation_count,
            "metals_vehicle_implementation_summary": vehicle_implementation_summary,
            "mtg_rich_record_counts": observed_mtg,
            "mtg_sidecar_paths": mtg_sidecars,
            "postgres_connection_opened": False,
            "postgres_write_performed": False,
            "publication_persisted": False,
            "publication_activated": False,
            "automatic_schedule_modified": False,
            "central_publication_cron_restored": False,
            "failure_policy": "NO_POSTGRES_PERSISTENCE_OR_ACTIVATION_DURING_RICH_CANDIDATE_REHEARSAL",
        }

    output = args.evidence_output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
    print("UIP_RICH_PUBLICATION_CANDIDATE_REHEARSAL=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
