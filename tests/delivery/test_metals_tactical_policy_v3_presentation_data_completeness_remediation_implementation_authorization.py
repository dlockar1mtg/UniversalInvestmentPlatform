from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config/metals/tactical_policy_v3_presentation_data_completeness_remediation_implementation_authorization.json"
VERIFIER = ROOT / "scripts/verify_metals_tactical_policy_v3_presentation_data_completeness_remediation_implementation_authorization.py"


def payload() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_authorization_is_bound_to_certified_design_and_database() -> None:
    data = payload()
    assert data["source_design_id"] == "METALS-TACTICAL-POLICY-V3-PRESENTATION-DATA-COMPLETENESS-REMEDIATION-DESIGN-1"
    assert data["source_design_head"] == "8f734bcf496fb80754d4533653754370fd4abd8f"
    assert data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_authorization_is_exactly_four_bounded_files() -> None:
    data = payload()
    assert set(data["authorized_files"]) == {
        "foundation/presentation/metals_tactical_projection.py",
        "config/presentation/dash_read_1_metals_tactical_extension.json",
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
    }


def test_existing_evidence_wiring_is_required() -> None:
    required = payload()["required_behavior"]
    for key in (
        "vehicle_tactical_metrics_from_current_authority",
        "vehicle_uncertainty_adjusted_forecast_context_from_current_authority",
        "vehicle_recommendation_explanation_from_current_authority",
        "commodity_model_components_from_current_authority",
        "commodity_regime_probabilities_from_current_authority",
        "bil_reference_control_only",
        "unsupported_fields_remain_explicitly_unavailable",
        "not_applicable_distinguished_from_missing",
    ):
        assert required[key] is True


def test_false_semantic_substitutions_remain_forbidden() -> None:
    required = payload()["required_behavior"]
    assert required["no_false_current_price_substitution"] is True
    assert required["no_false_forecast_bound_substitution"] is True
    assert required["no_false_risk_score_substitution"] is True
    assert set(payload()["unresolved_fields"]) == {
        "numeric_current_price",
        "forecast_upper_bound",
        "forecast_lower_bound",
        "generic_risk_level",
        "commodity_tactical_state",
    }


def test_downstream_mutations_and_deployment_remain_forbidden() -> None:
    boundaries = payload()["boundaries"]
    assert all(value is False for value in boundaries.values())


def test_verifier_is_static_and_read_only() -> None:
    source = VERIFIER.read_text(encoding="utf-8")
    assert "read_only" in source
    forbidden = ("duckdb.connect", "requests.", "urllib.request", "subprocess", "os.system", "UPDATE ", "INSERT ", "DELETE ")
    assert not any(token in source for token in forbidden)
