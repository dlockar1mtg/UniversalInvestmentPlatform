import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_ranking_v1.json"
DESIGN = ROOT / "docs" / "project_control" / "metals_vehicle_ranking_authority_design_v1.md"


def test_vehicle_ranking_weights_and_fail_closed_contract():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["authority_id"] == "UIP_NATIVE_METALS_VEHICLE_RANKING_V1"
    assert config["methodology_version"] == "1.0.0"
    assert abs(sum(config["weights"].values()) - 1.0) < 1e-9
    assert config["weights"] == {
        "exposure_fidelity": 0.30,
        "cost_efficiency": 0.20,
        "liquidity_implementation_friction": 0.20,
        "tracking_quality": 0.15,
        "risk_efficiency": 0.15,
    }
    gate = config["preferred_vehicle_gate"]
    assert gate["require_complete_evidence_for_all_compared_vehicles"] is True
    assert gate["missing_values_may_default"] is False
    assert gate["preferred_label"] == "PREFERRED_IMPLEMENTATION_CANDIDATE"


def test_exposure_types_are_not_relabelled_as_direct_commodity_exposure():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    scores = config["exposure_fidelity_class_scores"]
    assert scores["physical_backed_etf"] > scores["miners_etf"]
    assert scores["futures_fund"] > scores["miners_etf"]
    assert scores["thematic_equity_etf"] < scores["physical_backed_etf"]


def test_design_records_current_evidence_gap_and_forbidden_shortcuts():
    text = DESIGN.read_text(encoding="utf-8")
    assert "PREFERRED_VEHICLE_RANKING = FAIL_CLOSED_INSUFFICIENT_EVIDENCE" in text
    assert "certified expense-ratio coverage in the registry: **0/10**" in text
    assert "certified average-dollar-volume field: **not currently published**" in text
    assert "certified bid/ask-spread field: **not currently published**" in text
    assert "certified tracking-quality field: **not currently published**" in text
    assert "representative test scores" in text
    assert "vehicle Risk V1 as commodity risk" in text
    assert "automatic execution" in text


def test_required_evidence_includes_cost_liquidity_tracking_and_risk():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    required = set(config["required_evidence"])
    assert {
        "registered_exposure_type",
        "expense_ratio",
        "average_dollar_volume",
        "bid_ask_spread",
        "tracking_quality_or_explicit_not_applicable_state",
        "vehicle_risk_v1",
    } <= required
