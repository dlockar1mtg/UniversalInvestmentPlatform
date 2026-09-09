"""Build and atomically activate a UIP presentation publication from fresh domain artifacts.

This command is intentionally fail-closed. Crypto and Metals are imported through the
certified universal-package engine; MTG is imported through the certified MTG A2
binding. PostgreSQL activation occurs only after all three imports and presentation
validation succeed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.import_engine.audit import apply_audit_registry_migration, synchronize_successful_import
from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.integrity import validate_package_integrity
from foundation.import_engine.loader import import_package
from foundation.import_engine.package import discover_package
from foundation.integrations.mtg.v1_integration_binding import import_mtg_v1_authority
from foundation.presentation.postgres_read_model import PostgresPresentationRepository
from foundation.presentation.publication_model import build_presentation_publication
from foundation.presentation.publication_service import publish_presentation_bundle, validate_publication_bundle


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().lower()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def find_package(root: Path, domain: str) -> Path:
    candidates: list[Path] = []
    for summary_path in root.rglob("package_summary.json"):
        try:
            payload = load_json(summary_path)
        except Exception:
            continue
        platform = str(payload.get("platform_id") or payload.get("domain") or "").strip().lower()
        status = str(payload.get("status") or payload.get("validation_status") or "").strip().upper()
        posix = summary_path.as_posix()

        if domain == "crypto":
            # Crypto artifacts legitimately contain both a production universal_package
            # and the prepared UIP delivery package. The R1 consumer boundary is the
            # prepared UIP delivery, so select only that path.
            if platform == "crypto" and status == "PASS" and "/uip_delivery/" in posix:
                candidates.append(summary_path.parent)
        elif domain == "mtg":
            # MTG artifacts retain a history copy, a timestamped hosted package, and
            # the canonical current delivery. Production UIP consumes only the
            # source-owned declared live boundary: operations/mtg_uip_delivery/latest.
            if status == "PASS" and posix.endswith("/operations/mtg_uip_delivery/latest/package_summary.json"):
                candidates.append(summary_path.parent)
        elif platform == domain and status == "PASS":
            candidates.append(summary_path.parent)

    unique = sorted({path.resolve() for path in candidates}, key=lambda p: p.as_posix())
    if len(unique) != 1:
        raise RuntimeError(f"Expected exactly one PASS {domain} package, found {len(unique)}: {unique}")
    return unique[0]


def import_universal_package(config: ImportEngineConfig, package_root: Path, domain: str) -> dict:
    package = discover_package(package_root)
    validation = validate_package_integrity(package)
    if not validation.passed:
        raise RuntimeError(f"{domain} package integrity failed with {validation.error_count} error(s)")
    result = import_package(config, package_root)
    synchronize_successful_import(config, import_id=result.import_id)
    return {
        "domain": domain,
        "package_id": package.identity.package_id,
        "import_id": result.import_id,
        "imported_rows": result.imported_row_count,
    }


def import_mtg(config: ImportEngineConfig, package_root: Path, mtg_repo: Path) -> dict:
    native_authority = package_root / "mtg_native_authority.csv"
    summary = package_root / "package_summary.json"
    if not native_authority.is_file() or not summary.is_file():
        raise RuntimeError("MTG package is missing native authority or package summary")
    summary_payload = load_json(summary)
    overlay = summary_payload.get("live_overlay") or {}
    if overlay.get("status") != "PASS":
        raise RuntimeError(f"MTG live overlay is not PASS: {overlay}")

    export_root = mtg_repo / "docs" / "phase_9" / "uip_export"
    governance_root = mtg_repo / "config" / "mtg" / "governance"
    result = import_mtg_v1_authority(
        repository_root=ROOT,
        payload_path=native_authority,
        manifest_path=export_root / "mtg_v1_uip_export_manifest.json",
        schema_contract_path=governance_root / "mtg_v1_uip_export_schema_contract.json",
        export_contract_path=governance_root / "mtg_v1_uip_export_contract.json",
        portability_correction_path=governance_root / "mtg_v1_uip_export_hash_portability_correction.json",
        database_path=config.database_path,
        workspace_root=config.integration_root / "mtg-production",
        validation_root=config.validation_root / "mtg-production",
    )
    if result.status != "UIP_MTG_A2_INTEGRATION_CERTIFICATION_PASS":
        raise RuntimeError(f"MTG certified import failed: {result.status}")
    if result.lineage_missing_rows != 0:
        raise RuntimeError("MTG certified import contains missing lineage")
    if result.execution_ready_true_rows != 0 or result.automatic_execution_true_rows != 0:
        raise RuntimeError("MTG import unexpectedly created execution authority")
    if not result.native_fields_preserved:
        raise RuntimeError("MTG native fields were not preserved")
    return {
        "domain": "mtg",
        "status": result.status,
        "payload_rows": result.payload_rows,
        "imported_rows": result.imported_row_count,
        "lane_counts": result.lane_counts,
    }


def assert_required_presentation_surfaces(publication) -> dict[str, dict[str, int]]:
    counts = Counter((record.domain_id, record.record_type) for record in publication.records)
    required = {
        "crypto": ("asset", "domain_health", "forecast", "recommendation", "risk"),
        "metals": ("asset", "domain_health", "forecast", "recommendation"),
        "mtg": ("asset", "domain_health", "native_authority", "recommendation"),
    }
    for domain, surfaces in required.items():
        for surface in surfaces:
            if counts[(domain, surface)] < 1:
                raise RuntimeError(f"Required presentation surface is empty: {domain}/{surface}")
        if counts[(domain, "domain_health")] != 1:
            raise RuntimeError(f"Expected exactly one domain_health record for {domain}")
    return {
        domain: {surface: counts[(domain, surface)] for surface in surfaces}
        for domain, surfaces in required.items()
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crypto-artifact", type=Path, required=True)
    parser.add_argument("--metals-artifact", type=Path, required=True)
    parser.add_argument("--mtg-artifact", type=Path, required=True)
    parser.add_argument("--mtg-repo", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args()

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

    with tempfile.TemporaryDirectory(prefix="uip-production-publication-") as temp_name:
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
        publication_id = f"uip-production-{now.strftime('%Y%m%dT%H%M%SZ')}-{database_hash[:12]}"
        duck = duckdb.connect(str(config.database_path), read_only=True)
        try:
            publication = build_presentation_publication(
                ROOT,
                config.database_path,
                duck,
                publication_id=publication_id,
                published_at_utc=now.isoformat(),
            )
        finally:
            duck.close()

        validate_publication_bundle(publication)
        surface_counts = assert_required_presentation_surfaces(publication)

        store = PostgresPresentationRepository.from_dsn(dsn)
        store.initialize()
        previous = store.active_metadata()
        result = publish_presentation_bundle(store, publication)
        active = store.active_metadata()
        if result.status != "ACTIVE" or not active or active.get("publication_id") != publication_id:
            raise RuntimeError("Validated publication did not become the active PostgreSQL publication")

        evidence = {
            "status": "UIP_PRODUCTION_PUBLICATION_PASS",
            "published_at_utc": now.isoformat(),
            "publication_id": publication_id,
            "content_fingerprint": publication.content_fingerprint,
            "source_database_sha256": database_hash,
            "record_count": len(publication.records),
            "previous_active_publication_id": None if not previous else previous.get("publication_id"),
            "active_publication_id": active.get("publication_id"),
            "imports": imports,
            "presentation_surface_counts": surface_counts,
            "artifact_roots": {domain: str(path) for domain, path in artifact_roots.items()},
            "failure_policy": "NO_ACTIVATION_UNTIL_ALL_DOMAIN_IMPORTS_AND_PRESENTATION_VALIDATION_PASS",
        }
        output = args.evidence_output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
        print(json.dumps(evidence, indent=2, sort_keys=True, default=str))
        print("UIP_PRODUCTION_PUBLICATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
