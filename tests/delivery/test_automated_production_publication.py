from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "production-publication-cycle.yml"
PUBLISHER = ROOT / "scripts" / "publish_rehearsed_rich_candidate.py"


def test_production_publication_runs_daily_after_source_cycles():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'cron: "0 14 * * *"' in text
    assert "workflow_dispatch:" in text
    assert "Resolve current governed source runs" in text
    assert "crypto-production-cycle.yml" in text
    assert "metals-production-cycle.yml" in text
    assert "mtg-marketplace-production.yml" in text


def test_production_publication_no_longer_pins_september_source_run_ids():
    text = WORKFLOW.read_text(encoding="utf-8")
    for stale_pin in (
        'EXPECTED_CRYPTO_RUN_ID',
        'EXPECTED_CRYPTO_HEAD',
        'EXPECTED_CRYPTO_ARTIFACT_ID',
        'EXPECTED_CRYPTO_ARTIFACT_DIGEST',
        'EXPECTED_MTG_RUN_ID',
        'EXPECTED_METALS_RUN_ID',
        'EXPECTED_MTG_HEAD',
    ):
        assert stale_pin not in text
    assert '${{ steps.sources.outputs.crypto_run_id }}' in text
    assert '${{ steps.sources.outputs.metals_run_id }}' in text
    assert '${{ steps.sources.outputs.mtg_run_id }}' in text


def test_automated_publication_fails_closed_on_latest_source_failure_or_staleness():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'Latest governed source run is not complete' in text
    assert 'Latest governed source run failed' in text
    assert 'age_hours > 30' in text
    assert 'No current source artifact found' in text
    assert 'Artifact digest mismatch' in text
    assert 'Re-certify current rich source contracts before any PostgreSQL connection' in text


def test_manual_publication_still_requires_explicit_confirmation():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert 'if [ "$GITHUB_EVENT_NAME" = "workflow_dispatch" ]' in text
    assert 'PUBLISH_REHEARSED_RICH_CANDIDATE' in text
    assert 'Unauthorized publication event' in text


def test_publisher_records_automated_schedule_and_governed_failure_policy():
    text = PUBLISHER.read_text(encoding="utf-8")
    assert 'UIIP_AUTOMATED_PUBLICATION' in text
    assert '"automatic_schedule_modified": False' in text
    assert 'automated_publication_triggered' in text
    assert 'NO_POSTGRES_CONNECTION_UNTIL_GOVERNED_SOURCE_CONTRACTS_COUNTS_AND_AUTHORITIES_PASS' in text
    assert 'temporary' in text and 'DuckDB before any PostgreSQL connection is opened' in text


def test_production_publication_freshness_check_avoids_shell_heredoc():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "<<'PY'" not in text
    assert '\nPY\n' not in text
    assert "python -c 'import sys; from datetime import datetime, timezone;" in text
    assert 'age_hours > 30' in text
