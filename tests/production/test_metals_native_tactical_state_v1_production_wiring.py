from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "metals-production-cycle.yml"


def test_tactical_state_v1_is_wired_into_normal_metals_production_cycle():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "Build UIP-native tactical state V1 sidecar" in workflow
    assert "scripts/build_metals_native_tactical_state_sidecar.py" in workflow
    assert "config/presentation/metals_tactical_state_v1.json" in workflow
    assert "--native-cycle data/operations/metals/native_cycle/latest.json" in workflow
    assert "--regime-probability-csv data/operations/metals/native_regime_probability_v1/metals_regime_probability.csv" in workflow
    assert "--regime-probability-manifest data/operations/metals/native_regime_probability_v1/manifest.json" in workflow
    assert "--uncertainty-adjusted-csv data/operations/metals/native_uncertainty_adjusted_v1/metals_uncertainty_adjusted.csv" in workflow
    assert "--uncertainty-adjusted-manifest data/operations/metals/native_uncertainty_adjusted_v1/manifest.json" in workflow
    assert "--output-root data/operations/metals/native_tactical_state_v1" in workflow
    assert "data/operations/metals/native_tactical_state_v1/" in workflow


def test_tactical_state_v1_is_built_after_certified_supporting_authorities():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    regime = workflow.index("Build UIP-native regime probability V1 sidecar")
    uncertainty = workflow.index("Build UIP-native uncertainty adjusted V1 sidecar")
    tactical = workflow.index("Build UIP-native tactical state V1 sidecar")
    publish = workflow.index("Publish UIP-native package")

    assert regime < uncertainty < tactical < publish


def test_tactical_state_v1_production_wiring_preserves_existing_cycle_boundaries():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'cron: "23 12 * * *"' in workflow
    assert "production-publication-cycle" not in workflow
    assert "publication_activated" not in workflow
    assert "publication_staged" not in workflow
