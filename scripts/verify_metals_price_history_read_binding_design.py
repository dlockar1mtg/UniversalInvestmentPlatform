from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "presentation" / "metals_price_history_read_binding_design.json"
READ_API_PATH = ROOT / "foundation" / "presentation" / "read_api.py"
TACTICAL_PROJECTION_PATH = ROOT / "foundation" / "presentation" / "metals_tactical_projection.py"


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("design_id") != "METALS-PRICE-HISTORY-READ-BINDING-DESIGN-1":
        raise RuntimeError("unexpected Metals price/history binding design")
    if contract.get("version") != "1.0.0":
        raise RuntimeError("unsupported Metals price/history binding design version")
    if contract.get("source_authority") != "METALS-MARKET-HISTORY-1":
        raise RuntimeError("unexpected Metals market-history source authority")
    if contract.get("transport_contract") != "VERSIONED_EXPORT_PACKAGE_REQUIRED":
        raise RuntimeError("durable export package is not required")

    architecture = contract.get("architecture") or {}
    expected_architecture = {
        "native_store_may_be_read_by_exporter": True,
        "universal_production_may_query_native_tables_directly": False,
        "presentation_projection_may_query_native_tables_directly": False,
        "read_api_may_query_native_tables_directly": False,
        "versioned_export_package_required": True,
        "export_manifest_sha256_required": True,
        "source_run_id_required": True,
        "source_authority_required": True,
        "missing_authority_may_be_synthesized": False,
    }
    if architecture != expected_architecture:
        raise RuntimeError("Metals price/history architecture controls changed unexpectedly")

    controls = contract.get("controls") or {}
    if controls.get("design_authorized") is not True:
        raise RuntimeError("Metals price/history binding design is not authorized")
    for key in (
        "export_execution_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "tactical_posture_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited control changed unexpectedly: {key}")

    targets = contract.get("presentation_targets") or {}
    if targets.get("current_price_record_type") != "metals_current_price":
        raise RuntimeError("unexpected current-price record type")
    if targets.get("price_history_record_type") != "metals_price_history":
        raise RuntimeError("unexpected price-history record type")
    if int(targets.get("expected_vehicle_count", 0)) != 11:
        raise RuntimeError("unexpected Metals vehicle count")
    if int(targets.get("expected_history_points", 0)) != 8283:
        raise RuntimeError("unexpected certified Metals history point count")

    read_api_text = READ_API_PATH.read_text(encoding="utf-8")
    tactical_projection_text = TACTICAL_PROJECTION_PATH.read_text(encoding="utf-8")
    forbidden_native_names = (
        "metals_vehicle_observations",
        "metals_market_benchmark_observations",
    )
    for native_name in forbidden_native_names:
        if native_name in read_api_text:
            raise RuntimeError(f"read API directly references native table: {native_name}")
        if native_name in tactical_projection_text:
            raise RuntimeError(f"presentation projection directly references native table: {native_name}")

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": contract["design_id"],
        "source_authority": contract["source_authority"],
        "transport_contract": contract["transport_contract"],
        "current_price_record_type": targets["current_price_record_type"],
        "price_history_record_type": targets["price_history_record_type"],
        "expected_vehicle_count": int(targets["expected_vehicle_count"]),
        "expected_history_points": int(targets["expected_history_points"]),
        "direct_native_query_prohibited": True,
        "versioned_export_package_required": True,
        "export_execution_authorized": False,
        "presentation_activation_authorized": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "tactical_posture_authorized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
