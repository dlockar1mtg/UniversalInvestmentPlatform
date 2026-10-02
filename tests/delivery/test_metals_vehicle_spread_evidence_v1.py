import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "config" / "presentation" / "metals_vehicle_spread_evidence_v1.json"
EXPECTED = {"GLD", "IAU", "SGOL", "SLV", "SIVR", "PPLT", "CPER", "COPX", "URA", "URNM"}


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
