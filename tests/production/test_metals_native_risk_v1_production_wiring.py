from pathlib import Path


WORKFLOW = Path('.github/workflows/metals-production-cycle.yml')


def test_metals_production_cycle_builds_and_uploads_native_risk_v1():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'Build UIP-native risk V1 sidecar' in text
    assert 'scripts/build_metals_native_risk_sidecar.py' in text
    assert '--history data/operations/metals/native_rich_history/metals_price_history.csv' in text
    assert '--history-manifest data/operations/metals/native_rich_history/manifest.json' in text
    assert '--contract config/presentation/metals_risk_v1.json' in text
    assert '--output-root data/operations/metals/native_risk_v1' in text
    assert 'data/operations/metals/native_risk_v1/' in text


def test_metals_production_cycle_keeps_existing_schedule_and_no_central_activation():
    text = WORKFLOW.read_text(encoding='utf-8')
    assert 'cron: "23 12 * * *"' in text
    assert 'production-publication-cycle' not in text
    assert 'publication_activated' not in text
    assert 'stage' not in text.lower() or 'environment: staging' in text
