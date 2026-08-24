from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .publication_model import PresentationRecord


EXTENSION_PATH = Path("config/presentation/dash_read_1_metals_tactical_extension.json")
EXPECTED_SOURCE_SHA256 = "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"


def _rows(connection: Any, sql: str) -> tuple[dict[str, Any], ...]:
    cursor = connection.execute(sql)
    names = [str(item[0]) for item in cursor.description]
    return tuple(dict(zip(names, row)) for row in cursor.fetchall())


def _record(record_type: str, asset_id: str | None, key: str, payload: Mapping[str, Any]) -> PresentationRecord:
    return PresentationRecord(record_type, "metals", asset_id, key, dict(payload))


def _columns(connection: Any, source: str) -> set[str]:
    rows = connection.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='main' AND table_name=? ORDER BY ordinal_position",
        [source],
    ).fetchall()
    if not rows:
        raise RuntimeError(f"Metals tactical presentation source is missing: {source}")
    return {str(row[0]) for row in rows}


def load_and_validate_extension(repository_root: Path, connection: Any, source_database_sha256: str) -> dict[str, Any]:
    path = repository_root.resolve() / EXTENSION_PATH
    if not path.is_file():
        raise RuntimeError(f"Metals tactical presentation extension is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("extension_id") != "DASH-READ-1-METALS-TACTICAL-EVIDENCE":
        raise RuntimeError("Unexpected Metals tactical presentation extension ID.")
    if payload.get("version") != "1.0.0":
        raise RuntimeError("Unsupported Metals tactical presentation extension version.")
    if payload.get("source_database_sha256") != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("Metals tactical extension source hash changed unexpectedly.")
    if source_database_sha256.lower() != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("Source DuckDB is not the verified Metals tactical-evidence authority.")
    controls = payload.get("controls") or {}
    expected_controls = {
        "current_authority_only": True,
        "presentation_store_is_analytical_authority": False,
        "missing_authority_may_be_synthesized": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "tactical_posture_authorized": False,
    }
    if controls != expected_controls:
        raise RuntimeError("Metals tactical presentation controls changed unexpectedly.")
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, dict) or len(surfaces) != 6:
        raise RuntimeError("Metals tactical presentation surfaces are incomplete.")
    for record_type, surface in surfaces.items():
        source = str(surface.get("source", ""))
        required = tuple(str(value) for value in surface.get("required_fields") or ())
        if not source or not required:
            raise RuntimeError(f"Metals tactical surface is invalid: {record_type}")
        actual = _columns(connection, source)
        missing = sorted(set(required) - actual)
        if missing:
            raise RuntimeError(f"Metals tactical source {source} is missing fields: {missing}")
    return payload


def build_metals_tactical_records(repository_root: Path, connection: Any, source_database_sha256: str) -> list[PresentationRecord]:
    load_and_validate_extension(repository_root, connection, source_database_sha256)
    records: list[PresentationRecord] = []

    for row in _rows(connection, "SELECT * FROM metals_forecast_model_component_current ORDER BY universal_asset_id, horizon_months, model_name"):
        asset_id = str(row["universal_asset_id"])
        key = f"{asset_id}|{row['horizon_months']}|{row['model_name']}"
        records.append(_record("metals_model_component", asset_id, key, row))

    for row in _rows(connection, "SELECT * FROM metals_regime_probability_current ORDER BY universal_asset_id, regime"):
        asset_id = str(row["universal_asset_id"])
        key = f"{asset_id}|{row['regime']}"
        records.append(_record("metals_regime_probability", asset_id, key, row))

    for row in _rows(connection, "SELECT * FROM metals_uncertainty_adjusted_view_current ORDER BY universal_vehicle_id, horizon_months"):
        asset_id = str(row["universal_vehicle_id"])
        key = f"{asset_id}|{row['horizon_months']}"
        records.append(_record("metals_uncertainty_adjusted", asset_id, key, row))

    for row in _rows(connection, "SELECT * FROM metals_recommendation_change_current ORDER BY universal_vehicle_id"):
        asset_id = str(row["universal_vehicle_id"])
        records.append(_record("metals_recommendation_change", asset_id, asset_id, row))

    for row in _rows(connection, "SELECT * FROM metals_data_freshness_current ORDER BY series_key"):
        key = str(row["series_key"])
        records.append(_record("metals_data_freshness", None, key, row))

    for row in _rows(connection, "SELECT * FROM metals_platform_health_current ORDER BY decision_run_id"):
        key = str(row["decision_run_id"])
        records.append(_record("metals_platform_health", None, key, row))

    return records
