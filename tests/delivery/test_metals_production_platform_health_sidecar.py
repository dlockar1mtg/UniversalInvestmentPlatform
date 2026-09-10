from pathlib import Path


WORKFLOW = Path(".github/workflows/metals-production-cycle.yml")


def test_metals_production_cycle_builds_and_uploads_native_platform_health_sidecar() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "Build UIP-native platform health V1 sidecar" in text
    assert "scripts/build_metals_native_platform_health_sidecar.py" in text
    assert "--freshness data/operations/metals/native_freshness_v1/metals_data_freshness.csv" in text
    assert "--freshness-manifest data/operations/metals/native_freshness_v1/manifest.json" in text
    assert "--native-cycle data/operations/metals/native_cycle/latest.json" in text
    assert "--history-manifest data/operations/metals/native_rich_history/manifest.json" in text
    assert "--contract config/presentation/metals_platform_health_v1.json" in text
    assert "--output-root data/operations/metals/native_platform_health_v1" in text
    assert "data/operations/metals/native_platform_health_v1/" in text


def test_metals_production_platform_health_wiring_does_not_activate_presentation_publication() -> None:
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "activate_presentation" not in text
    assert "production-publication-cycle" not in text
