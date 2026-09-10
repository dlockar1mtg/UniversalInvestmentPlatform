from pathlib import Path


WORKFLOW = Path(".github/workflows/metals-production-cycle.yml")


def test_metals_production_cycle_builds_and_uploads_native_freshness_v1() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "Build UIP-native freshness V1 sidecar" in text
    assert "scripts/build_metals_native_freshness_sidecar.py" in text
    assert "--benchmark data/operations/metals/benchmark_input.csv" in text
    assert "--daily-market data/operations/metals/daily_market_input.csv" in text
    assert "--contract config/presentation/metals_data_freshness_v1.json" in text
    assert "--output-root data/operations/metals/native_freshness_v1" in text
    assert "data/operations/metals/native_freshness_v1/" in text


def test_metals_freshness_production_wiring_does_not_activate_publication() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "activate_presentation" not in text
    assert "production-publication-cycle" not in text
