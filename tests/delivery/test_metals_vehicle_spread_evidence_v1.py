import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "config" / "presentation" / "metals_vehicle_spread_evidence_v1.json"
EXPECTED = {"GLD", "IAU", "SGOL", "SLV", "SIVR", "PPLT", "CPER", "COPX", "URA", "URNM"}


def test_certified_spread_evidence_is_exact_and_provenanced():
    doc = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert doc["authority_id"] == "UIP_NATIVE_METALS_VEHICLE_SPREAD_EVIDENCE_V1"
    assert doc["methodology_version"] == "1.1.0"
    assert doc["provider"] == "alpaca_market_data"
    assert doc["feed"] == "sip"
    assert doc["source_run_id"] == 34968921414
    assert doc["source_head_sha"] == "c06ef0461e00562ab63261439b9025463d487140"
    assert doc["artifact_id"] == 10395879669
    assert doc["artifact_digest"] == "sha256:15ed4d1bdd06cee6e9e50eadced3f332dc21be6144b6a58f2ce932366820db6d"
    assert doc["required_ticker_count"] == 10
    assert doc["resolved_ticker_count"] == 10
    assert set(doc["vehicles"]) == EXPECTED
    assert doc["spread_evidence_certified"] is True


def test_certification_does_not_open_ranking_or_execution():
    doc = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert doc["production_quote_collection_authorized"] is False
    assert doc["preferred_vehicle_ranking_ready"] is False
    assert doc["publication_write_authorized"] is False
    assert doc["automatic_execution_authorized"] is False


def test_every_certified_spread_is_nonnegative():
    doc = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    for ticker, row in doc["vehicles"].items():
        assert row["median_bid_ask_spread_bps"] >= 0, ticker
