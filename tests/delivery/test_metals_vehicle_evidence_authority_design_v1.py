import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_evidence_v1.json"
DESIGN = ROOT / "docs" / "project_control" / "metals_vehicle_evidence_authority_design_v1.md"


def test_vehicle_evidence_authority_requires_complete_nondefaulted_evidence():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["authority_id"] == "UIP_NATIVE_METALS_VEHICLE_EVIDENCE_V1"
    assert config["methodology_version"] == "1.0.0"
    assert config["preferred_ranking_readiness"]["require_all_required_evidence"] is True
    assert config["preferred_ranking_readiness"]["allow_missing_defaults"] is False


def test_vehicle_evidence_windows_and_tracking_policy_are_explicit():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    liquidity = config["evidence_families"]["liquidity"]
    tracking = config["evidence_families"]["tracking_quality"]
    assert liquidity["average_dollar_volume_window_sessions"] == 30
    assert liquidity["bid_ask_spread_window_sessions"] == 20
    assert tracking["window_sessions"] == 252
    assert config["tracking_policy"]["futures_fund"] == "governed_futures_index_required"
    assert config["tracking_policy"]["miners_etf"] == "NOT_APPLICABLE_INDIRECT_EXPOSURE"
    assert config["tracking_policy"]["thematic_equity_etf"] == "NOT_APPLICABLE_INDIRECT_EXPOSURE"


def test_design_preserves_exact_registered_implementation_universe():
    text = DESIGN.read_text(encoding="utf-8")
    for ticker in ("GLD", "IAU", "SGOL", "SLV", "SIVR", "PPLT", "CPER", "COPX", "URA", "URNM"):
        assert ticker in text
    assert "BIL remains a reserve reference" in text


def test_design_forbids_false_precision_and_bad_proxies():
    text = DESIGN.read_text(encoding="utf-8")
    assert "Daily trading volume is not a substitute for quoted bid/ask spread" in text
    assert "NOT_APPLICABLE_INDIRECT_EXPOSURE" in text
    assert "Vehicle risk never becomes commodity risk" in text
    assert "preferred vehicle ranking remains fail-closed" in text
    assert "automatic execution" in text
