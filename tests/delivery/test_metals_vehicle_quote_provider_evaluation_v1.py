import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_quote_provider_evaluation_v1.json"
DESIGN = ROOT / "docs" / "project_control" / "metals_vehicle_quote_provider_evaluation_v1.md"
CERTIFICATION = ROOT / "docs" / "project_control" / "metals_alpaca_sip_provider_certification_v1.md"


def test_alpaca_sip_provider_is_certified_from_exact_live_evidence():
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert doc["required_tickers"] == ["GLD","IAU","SGOL","SLV","SIVR","PPLT","CPER","COPX","URA","URNM"]
    candidate = doc["provider_candidates"][0]
    assert candidate["provider"] == "alpaca_market_data"
    assert candidate["state"] == "CERTIFIED_SIP_QUOTE_PROVIDER_SUITABILITY_V1"
    assert candidate["preferred_feed"] == "sip"
    assert candidate["allow_silent_feed_downgrade"] is False
    assert doc["provider_certified"] is True
    assert doc["certified_provider"] == "alpaca_market_data"
    assert doc["certified_feed"] == "sip"
    assert doc["quote_collection_authorized"] is False
    assert doc["preferred_vehicle_ranking_ready"] is False

    evidence = candidate["certification_evidence"]
    assert evidence["workflow_run_id"] == 34904378863
    assert evidence["artifact_id"] == 10372366176
    assert evidence["artifact_digest"] == "sha256:772f903988a7f8ea94dd2e013f59c96f8eb04ad025231832199cf9f11a7425bd"
    assert evidence["source_head_sha"] == "acfb831b325d262ed5e7662674c6be599c030cc4"
    assert evidence["status"] == "METALS_ALPACA_QUOTE_SUITABILITY_REHEARSAL_PASS"
    assert evidence["required_ticker_count"] == 10
    assert evidence["resolved_ticker_count"] == 10
    assert evidence["minimum_distinct_sessions_per_ticker"] == 20


def test_live_rehearsal_proof_contract_is_retained():
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    required = set(doc["provider_candidates"][0]["live_proof_required"])
    assert {
        "exact_10_ticker_resolution",
        "positive_bid_ask_semantics",
        "20_distinct_regular_market_sessions_per_ticker",
        "deterministic_pagination_complete",
        "feed_and_source_provenance_retained",
    } <= required


def test_certification_keeps_collection_and_ranking_fail_closed():
    design = DESIGN.read_text(encoding="utf-8")
    certification = CERTIFICATION.read_text(encoding="utf-8")
    assert "fail closed rather than silently downgrade to IEX" in design
    assert "provider_certified = true" in certification
    assert "quote_collection_authorized = false" in certification
    assert "preferred_vehicle_ranking_ready = false" in certification
    assert "production quote collection remains unauthorized" in certification
    assert "deterministic per-session sampling or aggregation rule" in certification
