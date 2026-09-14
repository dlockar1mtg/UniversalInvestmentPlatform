import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_quote_source_v1.json"
DESIGN = ROOT / "docs" / "project_control" / "metals_vehicle_quote_source_design_v1.md"


def test_quote_source_contract_covers_exact_vehicle_universe():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["authority_id"] == "UIP_NATIVE_METALS_VEHICLE_QUOTE_SOURCE_V1"
    assert set(config["eligible_tickers"]) == {
        "GLD", "IAU", "SGOL", "SLV", "SIVR", "PPLT", "CPER", "COPX", "URA", "URNM"
    }
    assert len(config["eligible_tickers"]) == 10


def test_quote_contract_requires_actual_bid_ask_and_20_sessions():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    provider = config["provider_selection"]
    assert provider["provider_preselected"] is False
    assert provider["require_actual_bid_and_ask"] is True
    assert provider["require_20_distinct_trading_sessions_per_ticker"] is True
    assert provider["minimum_sessions"] == 20
    assert provider["missing_values_may_default"] is False
    assert {"bid", "ask", "observed_at_utc", "source_authority", "source_run_id"} <= set(config["required_fields"])


def test_spread_formula_and_fail_closed_ranking_gate_are_explicit():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert config["validation"]["relative_spread_formula_bps"] == "((ask-bid)/((ask+bid)/2))*10000"
    assert config["ranking_readiness"]["all_tickers_must_have_complete_20_session_coverage"] is True
    assert config["ranking_readiness"]["preferred_vehicle_ranking_ready_before_quote_evidence"] is False


def test_design_forbids_proxy_spreads_and_preselected_provider():
    text = DESIGN.read_text(encoding="utf-8")
    assert "No provider is selected by this design" in text
    assert "PROVIDER_NOT_YET_CERTIFIED" in text
    assert "FAIL_CLOSED_INSUFFICIENT_QUOTE_EVIDENCE" in text
    assert "high-low range as bid/ask spread" in text
    assert "volatility or ATR as bid/ask spread" in text
    assert "last trade as a substitute for bid or ask" in text
    assert "automatic execution" in text
