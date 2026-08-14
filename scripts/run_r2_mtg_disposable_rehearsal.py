from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from foundation.integrations.mtg.v1_integration_binding import import_mtg_v1_authority, result_to_dict

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_RUN_ID = "31843560745"
EXPECTED_SOURCE_COMMIT = "c40b1dd1191f7f3c2a760fd307fe1041e02ea24c"
EXPECTED_ARTIFACT_SHA256 = "1885fd950f4b01d00d71719c5ba34261a5b9a442ec61b17e19587decd4b265bc"
EXPECTED_ROWS = 968
EXPECTED_LANES = {
    "COLLECTOR_V1": 50,
    "PRE_COLLECTOR_V1": 131,
    "SECRET_LAIR_V1_1": 787,
}
EXPECTED_LIVE_PRICES = 161
EXPECTED_LIVE_DECISIONS = 49


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def find_one(root: Path, filename: str) -> Path:
    matches = list(root.rglob(filename))
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {filename}; found {len(matches)}")
    return matches[0]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run fail-closed disposable UIP rehearsal for fresh MTG R2 artifact.")
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--mtg-repo", type=Path, required=True)
    parser.add_argument(
        "--evidence-output",
        type=Path,
        default=ROOT / "docs" / "project_control" / "generated" / "r2_refreshed_data_rehearsal" / "mtg_r2_rehearsal_evidence.json",
    )
    args = parser.parse_args()

    artifact = args.artifact.resolve()
    mtg_repo = args.mtg_repo.resolve()

    if not artifact.is_file():
        raise RuntimeError(f"Artifact not found: {artifact}")
    if not mtg_repo.is_dir():
        raise RuntimeError(f"MTG repository not found: {mtg_repo}")

    artifact_hash = sha256(artifact)
    if artifact_hash != EXPECTED_ARTIFACT_SHA256:
        raise RuntimeError(
            f"Unexpected run #401 artifact SHA-256: {artifact_hash}; expected {EXPECTED_ARTIFACT_SHA256}"
        )

    with tempfile.TemporaryDirectory(prefix="uip-r2-mtg-") as temp_name:
        temp_root = Path(temp_name)
        extract_root = temp_root / "artifact"
        extract_root.mkdir()
        with zipfile.ZipFile(artifact) as archive:
            archive.extractall(extract_root)

        native_authority = find_one(extract_root, "mtg_native_authority.csv")
        package_summary_path = find_one(extract_root, "package_summary.json")
        package_summary = load_json(package_summary_path)
        live_overlay = package_summary.get("live_overlay") or {}

        if live_overlay.get("status") != "PASS":
            raise RuntimeError(f"Fresh MTG overlay did not report PASS: {live_overlay}")
        if int(live_overlay.get("certified_price_rows_available", 0) or 0) != EXPECTED_LIVE_PRICES:
            raise RuntimeError("Fresh MTG certified price count changed from run #401 evidence.")
        if int(live_overlay.get("products_with_live_prices", 0) or 0) != EXPECTED_LIVE_PRICES:
            raise RuntimeError("Fresh MTG run #401 did not preserve all 161 applied live prices.")
        if int(live_overlay.get("certified_decision_rows_available", 0) or 0) != EXPECTED_LIVE_DECISIONS:
            raise RuntimeError("Fresh MTG certified decision count changed from run #401 evidence.")
        if int(live_overlay.get("products_with_live_decisions", 0) or 0) != EXPECTED_LIVE_DECISIONS:
            raise RuntimeError("Fresh MTG run #401 did not preserve all 49 applied live decisions.")

        export_root = mtg_repo / "docs" / "phase_9" / "uip_export"
        governance_root = mtg_repo / "config" / "mtg" / "governance"

        manifest_path = export_root / "mtg_v1_uip_export_manifest.json"
        schema_contract_path = governance_root / "mtg_v1_uip_export_schema_contract.json"
        export_contract_path = governance_root / "mtg_v1_uip_export_contract.json"
        portability_path = governance_root / "mtg_v1_uip_export_hash_portability_correction.json"

        for required in (manifest_path, schema_contract_path, export_contract_path, portability_path):
            if not required.is_file():
                raise RuntimeError(f"Required certified MTG authority missing: {required}")

        database_path = temp_root / "uip_r2_mtg.duckdb"
        workspace_root = temp_root / "integration_workspace"
        validation_root = temp_root / "validation"

        result = import_mtg_v1_authority(
            repository_root=ROOT,
            payload_path=native_authority,
            manifest_path=manifest_path,
            schema_contract_path=schema_contract_path,
            export_contract_path=export_contract_path,
            portability_correction_path=portability_path,
            database_path=database_path,
            workspace_root=workspace_root,
            validation_root=validation_root,
        )

        result_data = result_to_dict(result)

        if result.status != "UIP_MTG_A2_INTEGRATION_CERTIFICATION_PASS":
            raise RuntimeError(f"Disposable MTG import did not certify: {result.status}")
        if result.payload_rows != EXPECTED_ROWS:
            raise RuntimeError(f"Unexpected MTG payload rows: {result.payload_rows}")
        if result.imported_row_count != EXPECTED_ROWS:
            raise RuntimeError(f"Unexpected imported row count: {result.imported_row_count}")
        if result.history_row_count != EXPECTED_ROWS or result.current_row_count != EXPECTED_ROWS:
            raise RuntimeError("Disposable UIP MTG history/current counts did not reconcile to 968.")
        if result.lane_counts != EXPECTED_LANES:
            raise RuntimeError(f"MTG lane counts changed: {result.lane_counts}")
        if result.lineage_missing_rows != 0:
            raise RuntimeError("Disposable UIP MTG import has missing lineage.")
        if result.execution_ready_true_rows != 0 or result.automatic_execution_true_rows != 0:
            raise RuntimeError("Disposable UIP rehearsal created execution authority.")
        if not result.native_fields_preserved:
            raise RuntimeError("Disposable UIP rehearsal did not preserve MTG native fields.")

        evidence = {
            "status": "UIP_R2_MTG_DISPOSABLE_REHEARSAL_PASS",
            "source_domain": "mtg",
            "source_repository": "dlockar1mtg/mtg-investment-terminal",
            "source_workflow_run_id": EXPECTED_RUN_ID,
            "source_commit": EXPECTED_SOURCE_COMMIT,
            "source_artifact_sha256": artifact_hash,
            "fresh_overlay": {
                "status": live_overlay.get("status"),
                "certified_price_rows_available": EXPECTED_LIVE_PRICES,
                "products_with_live_prices": EXPECTED_LIVE_PRICES,
                "certified_decision_rows_available": EXPECTED_LIVE_DECISIONS,
                "products_with_live_decisions": EXPECTED_LIVE_DECISIONS,
                "products_with_any_live_overlay": int(live_overlay.get("products_with_any_live_overlay", 0) or 0),
                "products_using_baseline_fallback": int(live_overlay.get("products_using_baseline_fallback", 0) or 0),
                "quality_status": live_overlay.get("quality_status"),
                "decision_status": live_overlay.get("decision_status"),
            },
            "disposable_uip_import": result_data,
            "production_uip_database_modified": False,
            "new_live_marketplace_collection_executed": False,
            "native_semantics_reinterpreted": False,
            "cross_asset_rank_created": False,
            "automatic_purchase_execution_created": False,
            "next_gate": "R2_METALS_FRESH_REHEARSAL",
        }

        output = args.evidence_output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        print(json.dumps(evidence, indent=2, sort_keys=True))
        print("UIP_R2_MTG_DISPOSABLE_REHEARSAL=PASS")
        print(f"EVIDENCE_OUTPUT={output}")
        print("PRODUCTION_UIP_DATABASE_MODIFIED=FALSE")
        print("NEW_LIVE_MARKETPLACE_COLLECTION_EXECUTED=FALSE")
        print("NEXT_GATE=R2_METALS_FRESH_REHEARSAL")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
