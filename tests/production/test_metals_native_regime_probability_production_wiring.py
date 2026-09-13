from pathlib import Path


WORKFLOW = Path('.github/workflows/metals-production-cycle.yml')


def test_regime_probability_v1_is_built_in_normal_metals_production_cycle():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'Build UIP-native regime probability V1 sidecar' in text
    assert 'scripts/build_metals_native_regime_probability_sidecar.py' in text
    assert '--contract config/presentation/metals_regime_probability_v1.json' in text
    assert '--methodology config/metals/model_methodology_registry.json' in text
    assert '--native-cycle data/operations/metals/native_cycle/latest.json' in text
    assert '--output-root data/operations/metals/native_regime_probability_v1' in text


def test_regime_probability_v1_is_included_in_production_artifact_without_activation():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'data/operations/metals/native_regime_probability_v1/' in text
    assert 'production-publication-cycle' not in text
    assert 'presentation_active_publication' not in text


def test_regime_probability_v1_build_occurs_after_native_cycle_and_before_artifact_upload():
    text = WORKFLOW.read_text(encoding='utf-8')
    native_cycle = text.index('Run UIP-native forecasts')
    regime = text.index('Build UIP-native regime probability V1 sidecar')
    upload = text.index('actions/upload-artifact@v4')
    assert native_cycle < regime < upload
