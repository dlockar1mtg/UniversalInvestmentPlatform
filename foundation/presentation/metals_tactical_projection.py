from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

from .publication_model import PresentationRecord


EXTENSION_PATH = Path("config/presentation/dash_read_1_metals_tactical_extension.json")
EXPECTED_SOURCE_SHA256 = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_EXTERNAL_PACKAGE_ID = "metals-price-history-20260824"
EXPECTED_CURRENT_PRICE_SHA256 = "e18ece1a8dbc5b23f6ec7bb2d014822bdccd8a7f82fca0b6c23d5fda3bc8a4ed"
EXPECTED_PRICE_HISTORY_SHA256 = "c3749acbcf3a6d11ee9a6ca392b8421e7654936af489fbb93a2f4ae659470f31"
EXPECTED_MANIFEST_SHA256 = "82ead8e711e0fde4b30fa4e0e7196681e41e7f0ffa363af201c0ee0737473dcf"


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


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonl_rows(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            text = raw.strip()
            if not text:
                continue
            payload = json.loads(text)
            if not isinstance(payload, dict):
                raise RuntimeError(f"Metals external JSONL row is not an object: {path}:{line_number}")
            rows.append(payload)
    return tuple(rows)


def _resolve_external_package_root(repository_root: Path, extension: Mapping[str, Any]) -> Path | None:
    configured = extension.get("external_price_package") or {}
    directory_name = str(configured.get("directory_name", "")).strip()
    if not directory_name:
        raise RuntimeError("Metals external price-package directory is not configured.")

    explicit = str(os.environ.get("UIP_METALS_PRICE_PACKAGE_ROOT", "")).strip()
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))

    root = repository_root.resolve()
    for base in (root, *tuple(root.parents)[:3]):
        candidates.append(base / "UIP_Evidence" / directory_name)
        candidates.append(base / directory_name)

    observed: set[str] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        marker = str(resolved).lower()
        if marker in observed:
            continue
        observed.add(marker)
        if resolved.is_dir():
            return resolved
    return None


def _validate_external_config(extension: Mapping[str, Any]) -> Mapping[str, Any]:
    external = extension.get("external_price_package")
    if not isinstance(external, dict):
        raise RuntimeError("Metals external price-package contract is missing.")
    expected = {
        "package_id": EXPECTED_EXTERNAL_PACKAGE_ID,
        "current_price_sha256": EXPECTED_CURRENT_PRICE_SHA256,
        "price_history_sha256": EXPECTED_PRICE_HISTORY_SHA256,
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "price_semantics": "UNADJUSTED_CLOSE",
    }
    for key, value in expected.items():
        if external.get(key) != value:
            raise RuntimeError(f"Metals external price-package contract changed unexpectedly: {key}")
    for field_name in ("current_price_required_fields", "price_history_required_fields"):
        values = external.get(field_name)
        if not isinstance(values, list) or not values:
            raise RuntimeError(f"Metals external price-package field contract is invalid: {field_name}")
    return external


def load_and_validate_extension(repository_root: Path, connection: Any, source_database_sha256: str) -> dict[str, Any]:
    path = repository_root.resolve() / EXTENSION_PATH
    if not path.is_file():
        raise RuntimeError(f"Metals tactical presentation extension is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("extension_id") != "DASH-READ-1-METALS-TACTICAL-EVIDENCE":
        raise RuntimeError("Unexpected Metals tactical presentation extension ID.")
    if payload.get("version") != "1.1.0":
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
        "tactical_posture_authorized": True,
    }
    if controls != expected_controls:
        raise RuntimeError("Metals tactical presentation controls changed unexpectedly.")
    surfaces = payload.get("surfaces")
    if not isinstance(surfaces, dict) or len(surfaces) != 7:
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
    _validate_external_config(payload)
    return payload


def _external_market_records(repository_root: Path, extension: Mapping[str, Any]) -> list[PresentationRecord]:
    external = _validate_external_config(extension)
    package_root = _resolve_external_package_root(repository_root, extension)
    if package_root is None:
        return []

    current_path = package_root / str(external["current_price_file"])
    history_path = package_root / str(external["price_history_file"])
    manifest_path = package_root / str(external["manifest_file"])
    for path in (current_path, history_path, manifest_path):
        if not path.is_file():
            raise RuntimeError(f"Certified Metals external price-package file is missing: {path}")

    observed_hashes = {
        "current_price": _sha256_file(current_path),
        "price_history": _sha256_file(history_path),
        "manifest": _sha256_file(manifest_path),
    }
    expected_hashes = {
        "current_price": EXPECTED_CURRENT_PRICE_SHA256,
        "price_history": EXPECTED_PRICE_HISTORY_SHA256,
        "manifest": EXPECTED_MANIFEST_SHA256,
    }
    if observed_hashes != expected_hashes:
        raise RuntimeError("Certified Metals external price-package hashes do not match the governed authority.")

    current_required = {str(value) for value in external["current_price_required_fields"]}
    history_required = {str(value) for value in external["price_history_required_fields"]}
    records: list[PresentationRecord] = []

    current_rows = _jsonl_rows(current_path)
    history_rows = _jsonl_rows(history_path)
    for row in current_rows:
        missing = sorted(current_required - set(row))
        if missing:
            raise RuntimeError(f"Metals current-price row is missing required fields: {missing}")
        asset_id = str(row["asset_id"])
        payload = dict(row)
        payload["price_semantics"] = "UNADJUSTED_CLOSE"
        payload["source_package_id"] = EXPECTED_EXTERNAL_PACKAGE_ID
        records.append(_record("metals_current_price", asset_id, asset_id, payload))

    for row in history_rows:
        missing = sorted(history_required - set(row))
        if missing:
            raise RuntimeError(f"Metals price-history row is missing required fields: {missing}")
        asset_id = str(row["asset_id"])
        observation_date = str(row["observation_date"])
        payload = dict(row)
        payload["price_semantics"] = "UNADJUSTED_CLOSE"
        payload["source_package_id"] = EXPECTED_EXTERNAL_PACKAGE_ID
        records.append(_record("metals_price_history", asset_id, f"{asset_id}|{observation_date}", payload))

    return records


def build_metals_tactical_records(repository_root: Path, connection: Any, source_database_sha256: str) -> list[PresentationRecord]:
    extension = load_and_validate_extension(repository_root, connection, source_database_sha256)
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

    for row in _rows(connection, "SELECT * FROM metals_tactical_state_current ORDER BY universal_asset_id"):
        asset_id = str(row["universal_asset_id"])
        if bool(row.get("is_reference_control")):
            continue
        records.append(_record("tactical_state", asset_id, asset_id, row))

    records.extend(_external_market_records(repository_root, extension))
    return records
