from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "tactical_policy_v3_decision_utility_completion_design.json"


def _data() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_identity_and_source_binding() -> None:
    data = _data()
    assert data["design_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-COMPLETION-DESIGN-1"
    assert data["source_jsonl_audit_head"] == "3a1117c358f01f7940ed0490bcf7845c48f7a65e"


def test_vehicle_price_authority() -> None:
    data = _data()["resolved_authorities"]
    current = data["vehicle_current_price"]
    assert current["source"] == "metals_current_price.jsonl"
    assert current["identity"] == "asset_id"
    assert current["value"] == "current_price_usd"
    assert current["date"] == "observation_date"
    assert current["coverage_rows"] == 11


def test_vehicle_history_authority_uses_unadjusted_close() -> None:
    history = _data()["resolved_authorities"]["vehicle_price_history"]
    assert history["source"] == "metals_price_history.jsonl"
    assert history["value"] == "close_usd"
    assert history["date"] == "observation_date"
    assert history["coverage_rows"] == 8283
    assert history["price_semantics"] == "UNADJUSTED_CLOSE"


def test_commodity_expected_return_scope() -> None:
    forecast = _data()["resolved_authorities"]["commodity_expected_return"]
    assert forecast["horizons_months"] == [3, 6, 12, 24]
    assert set(forecast["assets"]) == {
        "metals:commodity:copper",
        "metals:commodity:gold",
        "metals:commodity:platinum",
        "metals:commodity:silver",
    }


def test_presentation_requirements_all_true() -> None:
    assert all(_data()["presentation_requirements"].values())


def test_unsupported_fields_remain_explicit() -> None:
    unsupported = _data()["unsupported_fields"]
    assert unsupported["forecast_point_price"] is True
    assert unsupported["forecast_lower_bound"] is True
    assert unsupported["forecast_upper_bound"] is True
    assert unsupported["full_investment_rationale"] is True
    assert unsupported["recommendation_risk_summary_text"] is True
    assert unsupported["uranium_standard_commodity_forecast"] is True
    assert unsupported["commodity_numeric_current_price_from_vehicle_package"] is True


def test_semantic_guardrails_all_true() -> None:
    assert all(_data()["semantic_guardrails"].values())


def test_exact_candidate_implementation_files() -> None:
    assert _data()["candidate_implementation_files"] == [
        "foundation/presentation/metals_tactical_projection.py",
        "config/presentation/dash_read_1_metals_tactical_extension.json",
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
    ]


def test_no_implementation_or_downstream_authority_yet() -> None:
    assert not any(_data()["boundaries"].values())


def test_design_decision_and_next_step() -> None:
    data = _data()
    assert data["design_decision"] == "APPROVE_METALS_DECISION_UTILITY_COMPLETION_DESIGN_FOR_IMPLEMENTATION_CONSIDERATION"
    assert data["next_decision"] == "AUTHORIZE_METALS_DECISION_UTILITY_COMPLETION_IMPLEMENTATION"
