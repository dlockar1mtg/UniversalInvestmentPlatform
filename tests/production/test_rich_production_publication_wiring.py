from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "production-publication-cycle.yml"
SCRIPT = ROOT / "scripts" / "publish_rehearsed_rich_candidate.py"


def test_first_rich_production_publication_is_manual_and_exactly_pinned():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "PUBLISH_REHEARSED_RICH_CANDIDATE" in text
    assert 'EXPECTED_CRYPTO_RUN_ID: "34871765453"' in text
    assert 'EXPECTED_MTG_RUN_ID: "34768868851"' in text
    assert 'EXPECTED_METALS_RUN_ID: "34849676771"' in text
    assert 'EXPECTED_MTG_HEAD: "2e8b1a77c1bdd3b79141fffc94f84d91222e4266"' in text
    assert 'EXPECTED_RICH_RECORD_COUNT: "14228"' in text
    assert "download_exact" in text
    assert "scripts/audit_rich_publication_source_contract.py" in text
    assert "scripts/publish_rehearsed_rich_candidate.py" in text


def test_rich_production_script_validates_complete_candidate_before_postgres():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "build_metals_rich_records" in text
    assert "configure_mtg_sidecars" in text
    assert "assert_unique_records" in text
    assert "expected_metals_counts" in text
    assert "MTG_RICH_EXPECTED_COUNTS" in text
    assert "EXPECTED_GENERIC_COUNTS" in text
    assert "RICH_CANDIDATE_PREACTIVATION_GATE_PASS" in text

    validation = text.index('"status": "RICH_CANDIDATE_PREACTIVATION_GATE_PASS"')
    postgres = text.index("PostgresPresentationRepository.from_dsn")
    assert validation < postgres

    assert '"postgres_connection_opened": False' in text
    assert '"publication_persisted": False' in text
    assert '"publication_activated": False' in text
    assert '"automatic_schedule_modified": False' in text


def test_existing_legacy_latest_publisher_is_not_used_by_workflow():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "publish_latest_domain_artifacts.py" not in workflow
    assert "publish_rehearsed_rich_candidate.py" in workflow
