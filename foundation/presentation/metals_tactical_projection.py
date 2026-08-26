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
GOLD_ASSET_ID = "metals:commodity:gold"
URANIUM_ASSET_ID = "metals:commodity:uranium"
COMMODITY_EXPLANATION_RECORD_TYPE = "metals_commodity_decision_explanation"


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


def _validate_derived_config(extension: Mapping[str, Any]) -> Mapping[str, Any]:
    surfaces = extension.get("derived_surfaces")
    if not isinstance(surfaces, dict):
        raise RuntimeError("Metals derived presentation surfaces are missing.")
    derived = surfaces.get(COMMODITY_EXPLANATION_RECORD_TYPE)
    if not isinstance(derived, dict):
        raise RuntimeError("Metals commodity decision-explanation contract is missing.")
    if derived.get("eligible_assets") != [GOLD_ASSET_ID]:
        raise RuntimeError("Gold eligibility for commodity decision explanation changed unexpectedly.")
    unavailable = derived.get("unavailable_assets") or {}
    if unavailable.get(URANIUM_ASSET_ID) != "NO_CURRENT_COMMODITY_FORECAST_MODEL_OR_REGIME_AUTHORITY":
        raise RuntimeError("Uranium commodity explanation availability contract changed unexpectedly.")
    if derived.get("required_forecast_horizons_months") != [3, 6, 12, 24]:
        raise RuntimeError("Gold commodity explanation forecast-horizon contract changed unexpectedly.")
    if derived.get("source_record_types") != [
        "recommendation",
        "forecast",
        "metals_model_component",
        "metals_regime_probability",
    ]:
        raise RuntimeError("Commodity decision-explanation source record types changed unexpectedly.")
    if derived.get("derived_rationale_semantic_label") != "Derived decision rationale":
        raise RuntimeError("Derived rationale semantic label changed unexpectedly.")
    if derived.get("risk_context_semantic_label") != "Forecast / regime risk context":
        raise RuntimeError("Forecast/regime risk-context semantic label changed unexpectedly.")
    if derived.get("vehicle_risk_inheritance_allowed") is not False:
        raise RuntimeError("Vehicle risk inheritance must remain blocked for commodities.")
    if derived.get("vehicle_forecast_or_tactical_inheritance_allowed") is not False:
        raise RuntimeError("Vehicle forecast/tactical inheritance must remain blocked for commodities.")
    if derived.get("native_recommendation_fields_mutable") is not False:
        raise RuntimeError("Native recommendation fields must remain immutable.")
    if derived.get("native_risk_metrics_mutable") is not False:
        raise RuntimeError("Native risk metrics must remain immutable.")
    return derived


def load_and_validate_extension(repository_root: Path, connection: Any, source_database_sha256: str) -> dict[str, Any]:
    path = repository_root.resolve() / EXTENSION_PATH
    if not path.is_file():
        raise RuntimeError(f"Metals tactical presentation extension is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("extension_id") != "DASH-READ-1-METALS-TACTICAL-EVIDENCE":
        raise RuntimeError("Unexpected Metals tactical presentation extension ID.")
    if payload.get("version") != "1.2.0":
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
        "derived_explanatory_surface_authorized": True,
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
    derived = _validate_derived_config(payload)
    required_sources = derived.get("required_sources") or {}
    for source in required_sources.values():
        _columns(connection, str(source))
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


def _pct_text(value: Any) -> str:
    return f"{float(value) * 100.0:.1f}%"


def _score_text(value: Any) -> str:
    if value is None:
        return "unavailable"
    return f"{float(value):.2f}"


def _regime_key(value: Any) -> str:
    return str(value or "").strip().upper().replace(" ", "_").replace("-", "_")


def _commodity_decision_explanation_records(connection: Any, extension: Mapping[str, Any]) -> list[PresentationRecord]:
    derived = _validate_derived_config(extension)
    source_record_types = list(derived["source_record_types"])

    recommendation_rows = _rows(
        connection,
        "SELECT universal_asset_id, recommendation, normalized_score, confidence_score, rationale, risk_summary "
        "FROM recommendations_current WHERE lower(platform_id)='metals' AND universal_asset_id='metals:commodity:gold'",
    )
    if len(recommendation_rows) != 1:
        raise RuntimeError("Gold commodity decision explanation requires exactly one current recommendation row.")
    recommendation = recommendation_rows[0]
    if str(recommendation.get("rationale") or "").strip():
        raise RuntimeError("Gold native rationale is no longer absent; derived explanation requires governance review.")
    if str(recommendation.get("risk_summary") or "").strip():
        raise RuntimeError("Gold native risk summary is no longer absent; derived explanation requires governance review.")

    typed_risk_count = connection.execute(
        "SELECT COUNT(*) FROM risk_metrics_current WHERE lower(platform_id)='metals' AND universal_asset_id=?",
        [GOLD_ASSET_ID],
    ).fetchone()[0]
    if int(typed_risk_count) != 0:
        raise RuntimeError("Gold typed risk authority is no longer absent; derived risk context requires governance review.")

    forecast_rows = _rows(
        connection,
        "SELECT universal_asset_id, forecast_horizon_months, expected_return, forecast_method, model_version "
        "FROM forecasts_current WHERE lower(platform_id)='metals' AND universal_asset_id='metals:commodity:gold' "
        "ORDER BY forecast_horizon_months",
    )
    horizons = [int(row["forecast_horizon_months"]) for row in forecast_rows]
    if horizons != list(derived["required_forecast_horizons_months"]):
        raise RuntimeError(f"Gold governed forecast horizons changed unexpectedly: {horizons}")
    if any(row.get("expected_return") is None for row in forecast_rows):
        raise RuntimeError("Gold governed forecast path contains a missing expected return.")

    model_rows = _rows(
        connection,
        "SELECT universal_asset_id, horizon_months, model_name, model_forecast, model_weight "
        "FROM metals_forecast_model_component_current WHERE universal_asset_id='metals:commodity:gold' "
        "ORDER BY horizon_months, model_name",
    )
    if not model_rows:
        raise RuntimeError("Gold commodity decision explanation requires current model-component authority.")

    regime_rows = _rows(
        connection,
        "SELECT universal_asset_id, regime, probability "
        "FROM metals_regime_probability_current WHERE universal_asset_id='metals:commodity:gold' ORDER BY regime",
    )
    if not regime_rows:
        raise RuntimeError("Gold commodity decision explanation requires current regime-probability authority.")

    regimes = {_regime_key(row["regime"]): float(row["probability"]) for row in regime_rows}
    high_vol = regimes.get("HIGH_VOL_STRESS")
    normal = regimes.get("NORMAL")
    low_vol = regimes.get("LOW_VOL_GROWTH")
    if high_vol is None or normal is None or low_vol is None:
        raise RuntimeError(f"Gold governed regime set changed unexpectedly: {sorted(regimes)}")

    dominant_row = max(regime_rows, key=lambda row: float(row["probability"]))
    dominant_key = _regime_key(dominant_row["regime"])
    dominant_probability = float(dominant_row["probability"])
    if high_vol >= 0.50:
        risk_context_level = "ELEVATED"
        risk_rule = "HIGH_VOL_STRESS_GTE_0_50"
    elif dominant_key == "LOW_VOL_GROWTH":
        risk_context_level = "LOWER_REGIME_STRESS"
        risk_rule = "LOW_VOL_GROWTH_LARGEST"
    elif dominant_key == "NORMAL" and high_vol < 0.50:
        risk_context_level = "MODERATE"
        risk_rule = "NORMAL_LARGEST_AND_HIGH_VOL_STRESS_LT_0_50"
    else:
        raise RuntimeError("Gold forecast/regime risk context no longer matches the authorized deterministic mapping.")

    positive_components = sum(1 for row in model_rows if float(row["model_forecast"]) > 0)
    negative_components = sum(1 for row in model_rows if float(row["model_forecast"]) < 0)
    zero_components = len(model_rows) - positive_components - negative_components
    path_text = ", ".join(
        f"{int(row['forecast_horizon_months'])} months {_pct_text(row['expected_return'])}"
        for row in forecast_rows
    )
    regime_text = ", ".join(
        f"{str(row['regime']).replace('_', ' ').title()} {_pct_text(row['probability'])}"
        for row in sorted(regime_rows, key=lambda row: float(row["probability"]), reverse=True)
    )
    longest = forecast_rows[-1]
    rationale = (
        "Derived decision explanation from governed Gold evidence. "
        f"The native recommendation is {str(recommendation['recommendation']).upper()} with normalized score "
        f"{_score_text(recommendation['normalized_score'])} and confidence score {_score_text(recommendation['confidence_score'])}. "
        f"Governed expected returns are {path_text}; the longest governed horizon is "
        f"{int(longest['forecast_horizon_months'])} months at {_pct_text(longest['expected_return'])}. "
        f"Across {len(model_rows)} certified model-component rows, {positive_components} are positive, "
        f"{negative_components} are negative, and {zero_components} are zero. "
        f"Current forecast-regime probabilities are {regime_text}. "
        "This is a derived decision explanation, not the native recommendation rationale and not a probability of success."
    )
    risk_explanation = (
        f"{str(dominant_row['regime']).replace('_', ' ').title()} is the dominant forecast regime at "
        f"{_pct_text(dominant_probability)}. The authorized mapping therefore assigns {risk_context_level} "
        "forecast/regime risk context. This context is not a native typed asset-risk rating and does not populate risk_metrics_current."
    )

    gold_payload = {
        "universal_asset_id": GOLD_ASSET_ID,
        "explanation_state": "AVAILABLE",
        "derived_rationale_semantic_label": "Derived decision rationale",
        "derived_rationale": rationale,
        "native_rationale_present": False,
        "native_risk_summary_present": False,
        "typed_risk_record_present": False,
        "native_recommendation": recommendation["recommendation"],
        "normalized_score": recommendation["normalized_score"],
        "confidence_score": recommendation["confidence_score"],
        "forecast_path": [
            {
                "horizon_months": int(row["forecast_horizon_months"]),
                "expected_return": row["expected_return"],
            }
            for row in forecast_rows
        ],
        "longest_horizon_months": int(longest["forecast_horizon_months"]),
        "longest_horizon_expected_return": longest["expected_return"],
        "model_component_row_count": len(model_rows),
        "positive_model_component_count": positive_components,
        "negative_model_component_count": negative_components,
        "zero_model_component_count": zero_components,
        "risk_context_semantic_label": "Forecast / regime risk context",
        "risk_context_state": "AVAILABLE",
        "risk_context_level": risk_context_level,
        "risk_context_rule": risk_rule,
        "risk_context_explanation": risk_explanation,
        "dominant_regime": dominant_row["regime"],
        "dominant_regime_probability": dominant_probability,
        "regime_probabilities": [
            {"regime": row["regime"], "probability": row["probability"]}
            for row in sorted(regime_rows, key=lambda row: float(row["probability"]), reverse=True)
        ],
        "source_record_types": source_record_types,
        "vehicle_risk_inherited": False,
        "vehicle_forecast_or_tactical_evidence_inherited": False,
        "native_fields_mutated": False,
    }

    uranium_payload = {
        "universal_asset_id": URANIUM_ASSET_ID,
        "explanation_state": "UNAVAILABLE",
        "derived_rationale_semantic_label": "Derived decision rationale",
        "derived_rationale": None,
        "risk_context_semantic_label": "Forecast / regime risk context",
        "risk_context_state": "UNAVAILABLE",
        "risk_context_level": None,
        "availability_reason": "NO_CURRENT_COMMODITY_FORECAST_MODEL_OR_REGIME_AUTHORITY",
        "availability_explanation": (
            "Derived commodity rationale and forecast/regime risk context are unavailable because current Uranium "
            "commodity forecast, model-component, and regime-probability authority is not present. UIP does not infer "
            "these fields from URA or URNM vehicle evidence."
        ),
        "source_record_types": [],
        "vehicle_risk_inherited": False,
        "vehicle_forecast_or_tactical_evidence_inherited": False,
        "native_fields_mutated": False,
    }

    return [
        _record(COMMODITY_EXPLANATION_RECORD_TYPE, GOLD_ASSET_ID, GOLD_ASSET_ID, gold_payload),
        _record(COMMODITY_EXPLANATION_RECORD_TYPE, URANIUM_ASSET_ID, URANIUM_ASSET_ID, uranium_payload),
    ]


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

    records.extend(_commodity_decision_explanation_records(connection, extension))
    records.extend(_external_market_records(repository_root, extension))
    return records
