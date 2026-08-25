from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
IMPLEMENTATION_PATH = ROOT / "config/metals/tactical_policy_v3_decision_utility_completion_implementation.json"
PROJECTION_PATH = ROOT / "foundation/presentation/metals_tactical_projection.py"
EXTENSION_PATH = ROOT / "config/presentation/dash_read_1_metals_tactical_extension.json"
TACTICAL_UI_PATH = ROOT / "foundation/production/dashboard_assets/metals_tactical_ui.js"
RECOMMENDATION_UI_PATH = ROOT / "foundation/production/dashboard_assets/recommendation_ui.js"


def _implementation() -> dict:
    return json.loads(IMPLEMENTATION_PATH.read_text(encoding="utf-8"))


def test_implementation_is_bound_to_authorization_and_database() -> None:
    payload = _implementation()
    assert payload["implementation_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-COMPLETION-IMPLEMENTATION-1"
    assert payload["source_authorization_head"] == "96b47cf19ff2d3c3bb5b64bb11e4d71956105185"
    assert payload["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_runtime_delta_is_three_authorized_files() -> None:
    payload = _implementation()
    assert sorted(payload["runtime_files_changed"]) == sorted([
        "config/presentation/dash_read_1_metals_tactical_extension.json",
        "foundation/presentation/metals_tactical_projection.py",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
    ])
    assert payload["authorized_file_deliberately_unchanged"] == "foundation/production/dashboard_assets/recommendation_ui.js"


def test_external_market_authority_is_hash_locked_and_unadjusted() -> None:
    projection = PROJECTION_PATH.read_text(encoding="utf-8")
    extension = json.loads(EXTENSION_PATH.read_text(encoding="utf-8"))
    external = extension["external_price_package"]
    assert external["package_id"] == "metals-price-history-20260824"
    assert external["current_price_sha256"] == "e18ece1a8dbc5b23f6ec7bb2d014822bdccd8a7f82fca0b6c23d5fda3bc8a4ed"
    assert external["price_history_sha256"] == "c3749acbcf3a6d11ee9a6ca392b8421e7654936af489fbb93a2f4ae659470f31"
    assert external["manifest_sha256"] == "82ead8e711e0fde4b30fa4e0e7196681e41e7f0ffa363af201c0ee0737473dcf"
    assert external["price_semantics"] == "UNADJUSTED_CLOSE"
    assert 'records.append(_record("metals_current_price"' in projection
    assert 'records.append(_record("metals_price_history"' in projection
    assert 'payload["price_semantics"] = "UNADJUSTED_CLOSE"' in projection


def test_projection_keeps_missing_external_package_non_synthetic() -> None:
    projection = PROJECTION_PATH.read_text(encoding="utf-8")
    assert "if package_root is None:" in projection
    assert "return []" in projection
    assert "missing_authority_may_be_synthesized" in EXTENSION_PATH.read_text(encoding="utf-8")


def test_vehicle_ui_surfaces_current_price_and_history() -> None:
    source = TACTICAL_UI_PATH.read_text(encoding="utf-8")
    for token in [
        "metals_current_price",
        "metals_price_history",
        "Current price",
        "Price as of",
        "Historical market price",
        "metals-price-history-panel",
        "close_usd",
        "UNADJUSTED_CLOSE",
    ]:
        assert token in source


def test_vehicle_ui_distinguishes_raw_and_adjusted_return() -> None:
    source = TACTICAL_UI_PATH.read_text(encoding="utf-8")
    assert "Raw expected return" in source
    assert "Adjusted return" in source
    assert "raw_expected_return" in source
    assert "adjusted_expected_return" in source
    assert "uncertainty_penalty" in source
    assert "downside_penalty" in source


def test_recommendation_change_is_supporting_evidence_not_full_thesis() -> None:
    source = TACTICAL_UI_PATH.read_text(encoding="utf-8")
    assert "Recommendation-change evidence:" in source
    assert "Full investment-thesis narrative is not populated" in source
    payload = _implementation()
    assert payload["semantic_guardrails"]["recommendation_change_explanation_not_relabelled_as_full_thesis"] is True


def test_forecast_empty_state_is_semantically_repaired() -> None:
    source = TACTICAL_UI_PATH.read_text(encoding="utf-8")
    assert "Certified vehicle return forecasts are available below" in source
    assert "Price-point and bear/base/bull bounds are not populated for this vehicle." in source
    assert "No standard commodity forecast is currently available for Uranium" in source
    assert "UIP does not infer one from URA or URNM vehicle evidence." in source


def test_unsupported_fields_and_downstream_boundaries_remain_closed() -> None:
    payload = _implementation()
    assert sorted(payload["unsupported_fields"]) == sorted([
        "commodity_numeric_current_price",
        "forecast_lower_bound",
        "forecast_point_price",
        "forecast_upper_bound",
        "full_investment_rationale",
        "recommendation_risk_summary",
        "uranium_standard_commodity_forecast",
    ])
    assert all(value is True for value in payload["semantic_guardrails"].values())
    assert all(value is False for value in payload["boundaries"].values())


def test_next_decision_requires_local_certification_not_deployment() -> None:
    payload = _implementation()
    assert payload["implementation_status"] == "IMPLEMENTED_REQUIRES_LOCAL_REGRESSION_AND_LOCAL_PUBLICATION_PROJECTION_CERTIFICATION"
    assert payload["next_decision"] == "CERTIFY_METALS_DECISION_UTILITY_COMPLETION_AND_LOCAL_PUBLICATION_PROJECTION"
