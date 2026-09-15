import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_tracking_applicability_v1.json"
DESIGN = ROOT / "docs" / "project_control" / "metals_vehicle_tracking_applicability_v1.md"


def test_exact_tracking_applicability_universe():
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = doc["vehicles"]
    assert set(rows) == {"GLD","IAU","SGOL","SLV","SIVR","PPLT","CPER","COPX","URA","URNM"}
    assert doc["window_sessions"] == 252


def test_direct_and_futures_vehicles_require_available_tracking():
    rows = json.loads(CONFIG.read_text(encoding="utf-8"))["vehicles"]
    for ticker in ("GLD","IAU","SGOL","SLV","SIVR","PPLT","CPER"):
        assert rows[ticker]["tracking_state_required"] == "AVAILABLE"
        assert rows[ticker]["benchmark_class"] is not None
    assert rows["CPER"]["benchmark_class"] == "governed_copper_futures_index_benchmark"


def test_indirect_equity_vehicles_use_explicit_not_applicable_state():
    rows = json.loads(CONFIG.read_text(encoding="utf-8"))["vehicles"]
    for ticker in ("COPX","URA","URNM"):
        assert rows[ticker]["tracking_state_required"] == "NOT_APPLICABLE_INDIRECT_EXPOSURE"
        assert rows[ticker]["benchmark_class"] is None


def test_fail_closed_boundaries_remain_explicit():
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    rules = doc["rules"]
    assert rules["spot_commodity_may_not_proxy_indirect_equity_tracking"] is True
    assert rules["missing_benchmark_may_not_default"] is True
    assert rules["preferred_vehicle_ranking_ready"] is False
    text = DESIGN.read_text(encoding="utf-8")
    assert "spot-copper series is not sufficient authority" in text
    assert "No synthetic spot-commodity tracking error" in text
    assert "restore the central publication cron" in text
