import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_tracking_benchmark_source_v1.json"
DESIGN = ROOT / "docs" / "project_control" / "metals_tracking_benchmark_source_design_v1.md"


def test_exact_tracking_vehicle_benchmark_map_is_defined():
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert doc["required_tracking_vehicles"] == ["GLD", "IAU", "SGOL", "SLV", "SIVR", "PPLT", "CPER"]
    benchmarks = doc["benchmarks"]
    assert benchmarks["GLD"]["benchmark_id"] == "LBMA_GOLD_PRICE_PM"
    assert benchmarks["IAU"]["benchmark_id"] == "LBMA_GOLD_PRICE_PM"
    assert benchmarks["SGOL"]["benchmark_id"] == "LBMA_GOLD_PRICE_PM"
    assert benchmarks["SLV"]["benchmark_id"] == "LBMA_SILVER_PRICE"
    assert benchmarks["SIVR"]["benchmark_id"] == "LBMA_SILVER_PRICE"
    assert benchmarks["PPLT"]["benchmark_id"] == "LBMA_PLATINUM_PRICE_PM"
    assert benchmarks["CPER"]["benchmark_id"] == "SUMMERHAVEN_COPPER_INDEX_TOTAL_RETURN"


def test_tracking_history_requires_exact_252_aligned_observations():
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    req = doc["history_requirements"]
    assert req["minimum_aligned_return_observations"] == 252
    assert req["same_currency_required"] is True
    assert req["date_alignment_required"] is True
    assert req["missing_values_may_default"] is False


def test_history_collection_and_ranking_remain_closed():
    doc = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert doc["benchmark_history_collection_authorized"] is False
    assert doc["tracking_quality_calculation_authorized"] is False
    assert doc["preferred_vehicle_ranking_ready"] is False
    assert "spot_proxy_for_cper" in doc["forbidden"]
    assert "unlicensed_or_unauthorized_benchmark_history_ingestion" in doc["forbidden"]


def test_design_preserves_fail_closed_access_boundary():
    text = DESIGN.read_text(encoding="utf-8")
    assert "Benchmark identity and benchmark-history access are separate certification questions." in text
    assert "NOT YET CERTIFIED" in text
    assert "FAIL-CLOSED" in text
    assert "restore the central publication cron" in text
