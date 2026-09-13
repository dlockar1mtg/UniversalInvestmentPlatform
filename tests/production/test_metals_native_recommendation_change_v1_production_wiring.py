from pathlib import Path


WORKFLOW = Path('.github/workflows/metals-production-cycle.yml')


def test_metals_production_cycle_builds_and_uploads_native_recommendation_change_v1():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'Build UIP-native recommendation change V1 sidecar' in text
    assert 'scripts/build_metals_native_recommendation_change_sidecar.py' in text
    assert '--contract config/presentation/metals_recommendation_change_v1.json' in text
    assert '--methodology config/metals/model_methodology_registry.json' in text
    assert '--native-cycle data/operations/metals/native_cycle/latest.json' in text
    assert '--output-root data/operations/metals/native_recommendation_change_v1' in text
    assert 'data/operations/metals/native_recommendation_change_v1/' in text


def test_metals_production_cycle_keeps_existing_schedule_and_no_central_activation():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'cron: "23 12 * * *"' in text
    assert 'production-publication-cycle' not in text
    assert 'publication_activated' not in text
    assert 'environment: staging' in text
