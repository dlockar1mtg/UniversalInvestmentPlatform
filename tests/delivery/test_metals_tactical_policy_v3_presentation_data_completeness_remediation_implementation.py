from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/metals/tactical_policy_v3_presentation_data_completeness_remediation_implementation.json"
TACTICAL_UI = ROOT / "foundation/production/dashboard_assets/metals_tactical_ui.js"
PROJECTION = ROOT / "foundation/presentation/metals_tactical_projection.py"
EXTENSION = ROOT / "config/presentation/dash_read_1_metals_tactical_extension.json"
RECOMMENDATION_UI = ROOT / "foundation/production/dashboard_assets/recommendation_ui.js"


def payload() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_implementation_is_bound_to_certified_authorization_and_database() -> None:
    data = payload()
    assert data["source_authorization_head"] == "416d70856774dbf3a10b9e1ca4b11a49608a199b"
    assert data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert data["implementation_strategy"] == "CONSUME_ALREADY_PROJECTED_CERTIFIED_METALS_EVIDENCE_WITHOUT_CHANGING_ANALYTICAL_AUTHORITY"


def test_runtime_delta_is_minimal_and_within_authorized_boundary() -> None:
    data = payload()
    assert data["runtime_files_changed"] == ["foundation/production/dashboard_assets/metals_tactical_ui.js"]
    assert set(data["authorized_files_intentionally_unchanged"]) == {
        "config/presentation/dash_read_1_metals_tactical_extension.json",
        "foundation/presentation/metals_tactical_projection.py",
        "foundation/production/dashboard_assets/recommendation_ui.js",
    }
    assert len(data["authorized_files"]) == 4


def test_projection_already_emits_required_certified_record_types() -> None:
    source = PROJECTION.read_text(encoding="utf-8")
    for value in (
        '"metals_model_component"',
        '"metals_regime_probability"',
        '"metals_uncertainty_adjusted"',
        '"metals_recommendation_change"',
        '"tactical_state"',
    ):
        assert value in source


def test_extension_preserves_certified_sources_and_no_synthesis() -> None:
    data = json.loads(EXTENSION.read_text(encoding="utf-8"))
    assert data["controls"]["missing_authority_may_be_synthesized"] is False
    assert data["surfaces"]["metals_uncertainty_adjusted"]["source"] == "metals_uncertainty_adjusted_view_current"
    assert data["surfaces"]["metals_recommendation_change"]["source"] == "metals_recommendation_change_current"
    assert data["surfaces"]["metals_model_component"]["source"] == "metals_forecast_model_component_current"
    assert data["surfaces"]["metals_regime_probability"]["source"] == "metals_regime_probability_current"


def test_vehicle_evidence_is_consumed_by_tactical_ui() -> None:
    source = TACTICAL_UI.read_text(encoding="utf-8")
    for value in (
        "uncertaintyRows",
        "bestUncertainty",
        "Forecast return context",
        "raw_expected_return",
        "adjusted_expected_return",
        "uncertainty_penalty",
        "downside_penalty",
        "Recommendation evidence",
        "previous_action",
        "current_action",
        "previous_confidence",
        "current_confidence",
    ):
        assert value in source


def test_commodity_evidence_is_consumed_without_synthesizing_tactical_state() -> None:
    source = TACTICAL_UI.read_text(encoding="utf-8")
    assert "Commodity model components" in source
    assert "Commodity regime probabilities" in source
    assert "Vehicle-level tactical context not applicable" in source
    assert "no commodity tactical state is synthesized" in source
    assert "regime_probability_not_vehicle_tactical_state" not in source


def test_vehicle_card_forecast_enrichment_uses_adjusted_return() -> None:
    source = TACTICAL_UI.read_text(encoding="utf-8")
    assert "setCardForecast" in source
    assert "adjusted_expected_return" in source
    assert "metals_uncertainty_adjusted" in source
    assert "enrichVisibleCards" in source


def test_unresolved_fields_and_semantic_guardrails_are_preserved() -> None:
    data = payload()
    assert set(data["unresolved_fields"]) == {
        "numeric_current_price",
        "forecast_upper_bound",
        "forecast_lower_bound",
        "generic_risk_level",
        "commodity_tactical_state",
    }
    assert all(data["semantic_guardrails"].values())
    assert "Unsupported fields remain unavailable" in TACTICAL_UI.read_text(encoding="utf-8")


def test_other_domain_contracts_remain_in_shared_recommendation_ui() -> None:
    source = RECOMMENDATION_UI.read_text(encoding="utf-8")
    assert 'REC_DOMAINS=["crypto","metals","mtg"]' in source
    assert "3-YEAR GROWTH OUTLOOK" in source
    assert "native_purchase_status" in source
    assert "automatic_purchase_execution" in source


def test_downstream_writes_and_deployment_remain_unauthorized() -> None:
    data = payload()
    assert all(value is False for value in data["boundaries"].values())
    assert data["next_decision"] == "CERTIFY_AND_PREVIEW_METALS_PRESENTATION_DATA_COMPLETENESS_REMEDIATION"
