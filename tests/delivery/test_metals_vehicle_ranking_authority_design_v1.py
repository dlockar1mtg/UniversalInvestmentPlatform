import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_ranking_v1.json"
DESIGN = ROOT / "docs" / "project_control" / "metals_vehicle_ranking_authority_design_v1.md"


def test_vehicle_ranking_weights_and_fail_closed_contract():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["authority_id"] == "UIP_NATIVE_METALS_VEHICLE_RANKING_V1"
    assert config["methodology_version"] == "1.3.0"
    assert config["holding_period_months"] == 6
    assert config["liquidity_floor"]["minimum_average_dollar_volume_usd"] == 10000000
    assert config["liquidity_floor"]["maximum_bid_ask_spread_bps"] == 25
    assert abs(sum(config["weights"].values()) - 1.0) < 1e-9
    assert config["weights"] == {
        "exposure_fidelity": 0.40,
        "cost_efficiency": 0.45,
        "liquidity_implementation_friction": 0.0,
        "risk_efficiency": 0.15,
    }
    assert config["optional_informational_evidence"] == ["tracking_quality"]
    gate = config["preferred_vehicle_gate"]
    assert gate["require_complete_evidence_for_all_compared_vehicles"] is True
    assert gate["missing_values_may_default"] is False
    assert gate["preferred_label"] == "PREFERRED_IMPLEMENTATION_CANDIDATE"


def test_normalization_formulas_are_explicit_and_bounded():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    norm = config["normalization"]
    assert norm["comparison_scope"] == "WITHIN_SAME_COMMODITY_GROUP_ONLY"
    assert norm["score_range"] == [0.0, 100.0]
    assert "group_min_cost_of_ownership" in norm["cost_efficiency"]["formula"]
    assert "holding_period_months" in norm["cost_efficiency"]["formula"]
    liquidity = norm["liquidity_implementation_friction"]
    assert liquidity["adv_subweight"] == 0.50
    assert liquidity["spread_subweight"] == 0.50
    assert "group_max_average_dollar_volume" in liquidity["adv_formula"]
    assert "group_min_bid_ask_spread" in liquidity["spread_formula"]
    risk = norm["risk_efficiency"]
    assert abs(sum(risk["submetric_weights"].values()) - 1.0) < 1e-9
    assert risk["maximum_drawdown_transform"] == "ABSOLUTE_VALUE"
    assert norm["missing_required_input_policy"] == "FAIL_CLOSED"
    assert norm["zero_or_nonpositive_required_input_policy"] == "FAIL_CLOSED"


def test_exposure_types_are_not_relabelled_as_direct_commodity_exposure():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    scores = config["exposure_fidelity_class_scores"]
    assert scores["physical_backed_etf"] > scores["miners_etf"]
    assert scores["futures_fund"] > scores["miners_etf"]
    assert scores["thematic_equity_etf"] < scores["physical_backed_etf"]


def test_design_records_normalization_and_forbidden_shortcuts():
    text = DESIGN.read_text(encoding="utf-8")
    assert "methodology version: `1.3.0`" in text
    assert "cost_score = 100 * group_min_cost_of_ownership / vehicle_cost_of_ownership" in text
    assert "Liquidity floor" in text
    assert "adv_score = 100 * vehicle_ADV / group_max_ADV" in text
    assert "spread_score = 100 * group_min_spread / vehicle_spread" in text
    assert "Vehicle Risk V1 as commodity risk" in text
    assert "representative test scores" in text
    assert "unauthorized tracking proxies" in text
    assert "automatic execution" in text


def test_required_evidence_excludes_tracking_and_keeps_certified_inputs():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    required = set(config["required_evidence"])
    assert required == {
        "registered_exposure_type",
        "expense_ratio",
        "average_dollar_volume",
        "bid_ask_spread",
        "vehicle_risk_v1",
    }
    assert "tracking_quality_or_explicit_not_applicable_state" not in required
    assert "tracking_proxy_substitution" in config["forbidden"]
