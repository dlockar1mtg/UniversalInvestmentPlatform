import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_liquidity_v1.json"
DESIGN = ROOT / "docs" / "project_control" / "metals_vehicle_liquidity_evidence_design_v1.md"


def test_adv_uses_existing_governed_history_and_exact_30_session_window():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    adv = config["average_dollar_volume"]
    assert config["authority_id"] == "UIP_NATIVE_METALS_VEHICLE_LIQUIDITY_V1"
    assert adv["source_authority"] == "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1"
    assert adv["window_sessions"] == 30
    assert adv["minimum_sessions"] == 30
    assert "close_usd * volume" in adv["formula"]
    assert adv["missing_values_may_default"] is False


def test_spread_requires_real_bid_and_ask_and_20_sessions():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    spread = config["quoted_spread"]
    assert spread["required_metric"] == "median_relative_bid_ask_spread_bps"
    assert spread["window_sessions"] == 20
    assert spread["minimum_sessions"] == 20
    assert {"bid", "ask", "observed_at_utc", "source_authority"} <= set(spread["required_observation_fields"])
    assert spread["daily_ohlcv_may_proxy_spread"] is False
    assert spread["missing_values_may_default"] is False


def test_design_forbids_fake_spread_proxies_and_keeps_ranking_closed():
    text = DESIGN.read_text(encoding="utf-8")
    assert "Daily OHLCV does **not** contain quoted bid and ask" in text
    assert "daily high-low range" in text
    assert "close-to-close volatility" in text
    assert "ATR" in text
    assert "PREFERRED IMPLEMENTATION CANDIDATE" in text
    assert "FAIL-CLOSED UNTIL REQUIRED EVIDENCE IS COMPLETE" in text


def test_liquidity_design_does_not_authorize_execution_or_cron_restore():
    text = DESIGN.read_text(encoding="utf-8")
    assert "does not modify the Metals source collection schedule" in text
    assert "authorize allocation or execution" in text
    assert "restore the central publication cron" in text
