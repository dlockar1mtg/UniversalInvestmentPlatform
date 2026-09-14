import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_quote_provider_evaluation_v1.json"
DESIGN = ROOT / "docs" / "project_control" / "metals_vehicle_quote_provider_evaluation_v1.md"


def test_alpaca_is_provisional_not_certified():
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert doc["required_tickers"] == ["GLD","IAU","SGOL","SLV","SIVR","PPLT","CPER","COPX","URA","URNM"]
    candidate = doc["provider_candidates"][0]
    assert candidate["provider"] == "alpaca_market_data"
    assert candidate["state"] == "PROVISIONAL_CANDIDATE_PENDING_LIVE_10_TICKER_REHEARSAL"
    assert candidate["preferred_feed"] == "sip"
    assert candidate["allow_silent_feed_downgrade"] is False
    assert doc["provider_certified"] is False
    assert doc["quote_collection_authorized"] is False
    assert doc["preferred_vehicle_ranking_ready"] is False


def test_live_rehearsal_must_prove_coverage_and_semantics():
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    required = set(doc["provider_candidates"][0]["live_proof_required"])
    assert {
        "exact_10_ticker_resolution",
        "positive_bid_ask_semantics",
        "20_distinct_regular_market_sessions_per_ticker",
        "deterministic_pagination_complete",
        "feed_and_source_provenance_retained",
    } <= required


def test_design_forbids_silent_iex_downgrade_and_keeps_writes_closed():
    text = DESIGN.read_text(encoding="utf-8")
    assert "fail closed rather than silently downgrade to IEX" in text
    assert "PROVISIONAL_CANDIDATE_PENDING_LIVE_10_TICKER_REHEARSAL" in text
    assert "No quote collection, ranking activation, publication write" in text
