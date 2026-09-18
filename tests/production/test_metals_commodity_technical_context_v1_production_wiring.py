from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "metals-production-cycle.yml"


def test_metals_production_cycle_wires_certified_commodity_technical_context_v1():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'cron: "23 12 * * *"' in workflow
    assert "collect_metals_benchmark_history.py" in workflow
    assert "--output data/operations/metals/commodity_benchmark_history.csv" in workflow
    assert "build_metals_commodity_technical_context_sidecar.py" in workflow
    assert "--history data/operations/metals/commodity_benchmark_history.csv" in workflow
    assert "--contract config/presentation/metals_commodity_technical_context_v1.json" in workflow
    assert "--output-root data/operations/metals/native_commodity_technical_context_v1" in workflow
    assert "data/operations/metals/commodity_benchmark_history.csv" in workflow
    assert "data/operations/metals/native_commodity_technical_context_v1/" in workflow


def test_commodity_technical_context_wiring_does_not_activate_central_publication():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "production-publication-cycle" not in workflow
    assert "PUBLISH_REHEARSED_RICH_CANDIDATE" not in workflow
