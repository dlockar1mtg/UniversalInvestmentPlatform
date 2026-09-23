from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "production-publication-cycle.yml"
SCRIPT = ROOT / "scripts" / "publish_rehearsed_rich_candidate.py"
SCRIPT_V2 = ROOT / "scripts" / "publish_rehearsed_rich_candidate_v2.py"


def test_rich_production_publication_is_scheduled_and_resolves_current_governed_sources():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in text
    assert "schedule:" in text
    assert 'cron: "0 14 * * *"' in text
    assert "PUBLISH_REHEARSED_RICH_CANDIDATE" in text
    assert "EXPECTED_RICH_RECORD_COUNT" not in text
    assert "--expected-record-count" not in text
    assert "EXPECTED_CRYPTO_RUN_ID" not in text
    assert "EXPECTED_MTG_RUN_ID" not in text
    assert "EXPECTED_METALS_RUN_ID" not in text
    assert "Resolve current governed source runs" in text
    assert "crypto-production-cycle.yml" in text
    assert "metals-production-cycle.yml" in text
    assert "mtg-marketplace-production.yml" in text
    assert "download_current" in text
    assert "scripts/audit_rich_publication_source_contract.py" in text
    assert "scripts/publish_rehearsed_rich_candidate_v2.py" in text


def test_rich_production_script_bootstraps_repository_before_local_imports():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "import sys" in text
    root = text.index('ROOT = Path(__file__).resolve().parents[1]')
    path_insert = text.index("sys.path.insert(0, str(ROOT))")
    foundation_import = text.index("from foundation.import_engine.audit import")
    assert root < path_insert < foundation_import


def test_rich_production_v2_bootstraps_repository_before_local_imports():
    text = SCRIPT_V2.read_text(encoding="utf-8")

    assert "import sys" in text
    root = text.index('ROOT = Path(__file__).resolve().parents[1]')
    path_insert = text.index("sys.path.insert(0, str(ROOT))")
    publisher_import = text.index("import scripts.publish_rehearsed_rich_candidate as publisher")
    assert root < path_insert < publisher_import


def test_rich_production_script_validates_complete_candidate_before_postgres():
    text = SCRIPT.read_text(encoding="utf-8")

    assert "build_metals_rich_records" in text
    assert "configure_mtg_sidecars" in text
    assert "assert_unique_records" in text
    assert "expected_metals_counts" in text
    assert "MTG_RICH_EXPECTED_COUNTS" in text
    assert "EXPECTED_FIXED_GENERIC_COUNTS" in text
    assert "assert_fixed_generic_counts" in text
    assert "RICH_CANDIDATE_PREACTIVATION_GATE_PASS" in text
    assert '"forecast": 129,' not in text

    validation = text.index('"status": "RICH_CANDIDATE_PREACTIVATION_GATE_PASS"')
    postgres = text.index("PostgresPresentationRepository.from_dsn")
    assert validation < postgres

    assert '"postgres_connection_opened": False' in text
    assert '"publication_persisted": False' in text
    assert '"publication_activated": False' in text
    assert '"automatic_schedule_modified": False' in text


def test_v2_uses_shared_rich_candidate_composition():
    text = SCRIPT_V2.read_text(encoding="utf-8")
    rehearsal = (ROOT / "scripts" / "rehearse_rich_publication_candidate.py").read_text(encoding="utf-8")
    publisher = SCRIPT.read_text(encoding="utf-8")
    assert "compose_rich_candidate(" in rehearsal
    assert "compose_rich_candidate(" in publisher
    assert "return publisher.main()" in text
    assert "automatic_execution" not in text


def test_existing_legacy_latest_publisher_is_not_used_by_workflow():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "publish_latest_domain_artifacts.py" not in workflow
    assert "publish_rehearsed_rich_candidate_v2.py" in workflow


def test_daily_publication_does_not_pin_variable_forecast_or_total_record_counts():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    publisher = SCRIPT.read_text(encoding="utf-8")

    assert "EXPECTED_RICH_RECORD_COUNT" not in workflow
    assert "--expected-record-count" not in workflow
    assert '"forecast": 129' not in publisher
    assert "args.expected_record_count" not in publisher
    assert "assert_fixed_generic_counts(generic_counts)" in publisher
    assert 'if len(publication.records) < 1:' in publisher
