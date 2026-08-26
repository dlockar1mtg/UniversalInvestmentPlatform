from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config" / "metals" / "commodity_decision_explanation_implementation_authorization.json"
DESIGN_PATH = ROOT / "config" / "metals" / "commodity_decision_explanation_design.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_authorization_binds_certified_design() -> None:
    auth = load(AUTH_PATH)
    design = load(DESIGN_PATH)
    assert auth["source_design_id"] == design["design_id"]
    assert auth["source_design_head"] == "327e72e4eb9ac7abff9d636bdaf3489b428abef3"
    assert auth["source_database_sha256"] == design["source_database_sha256"]
    assert auth["authorized_record_type"] == "metals_commodity_decision_explanation"


def test_runtime_scope_is_exact() -> None:
    auth = load(AUTH_PATH)
    assert sorted(auth["authorized_runtime_files"]) == sorted([
        "foundation/presentation/metals_tactical_projection.py",
        "config/presentation/dash_read_1_metals_tactical_extension.json",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
    ])


def test_gold_native_fields_cannot_be_fabricated() -> None:
    auth = load(AUTH_PATH)
    guards = auth["semantic_guardrails"]
    assert guards["do_not_populate_recommendations_current_rationale"] is True
    assert guards["do_not_populate_recommendations_current_risk_summary"] is True
    assert guards["do_not_populate_risk_metrics_current"] is True
    assert guards["do_not_copy_gld_risk_level_or_score_to_gold"] is True


def test_uranium_inference_remains_blocked() -> None:
    auth = load(AUTH_PATH)
    required = auth["required_implementation_behavior"]
    guards = auth["semantic_guardrails"]
    assert required["uranium_derived_rationale_remains_unavailable"] is True
    assert required["uranium_forecast_regime_risk_context_remains_unavailable"] is True
    assert required["ura_urnm_evidence_not_inherited_by_uranium"] is True
    assert guards["do_not_copy_ura_or_urnm_evidence_to_uranium"] is True


def test_only_runtime_implementation_is_authorized() -> None:
    auth = load(AUTH_PATH)
    boundary = auth["authorization_boundary"]
    assert boundary["runtime_implementation_authorized"] is True
    for key, value in boundary.items():
        if key == "runtime_implementation_authorized":
            continue
        assert value is False


def test_authorization_decision_and_next_step() -> None:
    auth = load(AUTH_PATH)
    assert auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_COMMODITY_DECISION_EXPLANATION_IMPLEMENTATION"
    assert auth["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_COMMODITY_DECISION_EXPLANATION"
