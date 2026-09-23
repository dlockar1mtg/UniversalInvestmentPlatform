from pathlib import Path
import importlib.util


ROOT = Path(__file__).resolve().parents[2]
PROJECTION = ROOT / "foundation" / "presentation" / "metals_rich_projection.py"
SCRIPT = ROOT / "scripts" / "rehearse_rich_publication_candidate.py"
WORKFLOW = ROOT / ".github" / "workflows" / "rich-publication-candidate-rehearsal.yml"


def _load_projection():
    spec = importlib.util.spec_from_file_location("metals_rich_projection_test", PROJECTION)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_projection_covers_exactly_eleven_certified_metals_families():
    module = _load_projection()
    assert set(module.FAMILY_PROJECTION) == {
        "current_price",
        "price_history",
        "data_freshness",
        "commodity_technical_context",
        "platform_health",
        "model_component",
        "risk",
        "recommendation_change",
        "regime_probability",
        "uncertainty_adjusted",
        "tactical_state",
    }
    assert module.FAMILY_PROJECTION["current_price"]["record_type"] == "metals_current_price"
    assert module.FAMILY_PROJECTION["price_history"]["record_type"] == "metals_price_history"
    assert module.FAMILY_PROJECTION["price_history"]["key_fields"] == (
        "asset_id",
        "observation_date",
        "source_run_id",
    )
    assert module.FAMILY_PROJECTION["commodity_technical_context"]["record_type"] == "metals_commodity_technical_context"
    assert module.FAMILY_PROJECTION["commodity_technical_context"]["asset_field"] == "universal_asset_id"
    assert module.FAMILY_PROJECTION["commodity_technical_context"]["key_fields"] == ("universal_asset_id",)
    assert module.FAMILY_PROJECTION["risk"]["record_type"] == "risk"
    assert module.FAMILY_PROJECTION["tactical_state"]["record_type"] == "tactical_state"


def test_price_history_revision_key_preserves_same_day_source_revisions():
    module = _load_projection()
    fields = module.FAMILY_PROJECTION["price_history"]["key_fields"]
    original = {
        "asset_id": "metals:vehicle:BIL",
        "observation_date": "2026-07-23",
        "source_run_id": "gha-30205292529",
    }
    backfill = {
        "asset_id": "metals:vehicle:BIL",
        "observation_date": "2026-07-23",
        "source_run_id": "metals-market-history-backfill-20260824",
    }
    original_key = module._record_key(original, fields, "price_history")
    backfill_key = module._record_key(backfill, fields, "price_history")
    assert original_key != backfill_key
    assert original_key == "metals:vehicle:BIL|2026-07-23|gha-30205292529"
    assert backfill_key == "metals:vehicle:BIL|2026-07-23|metals-market-history-backfill-20260824"


def test_candidate_script_is_non_persistent_and_binds_rich_sources_explicitly():
    text = SCRIPT.read_text(encoding="utf-8")
    assert "build_metals_rich_records" in text
    assert "UIP_MTG_PREMIUM_SIDECAR_PATH" in text
    assert "UIP_MTG_COLLECTOR_RESEARCH_PATH" in text
    assert "UIP_MTG_PRECOLLECTOR_RESEARCH_PATH" in text
    assert '"postgres_connection_opened": False' in text
    assert '"postgres_write_performed": False' in text
    assert '"publication_persisted": False' in text
    assert '"publication_activated": False' in text
    assert "PostgresPresentationRepository" not in text
    assert "publish_presentation_bundle" not in text


def test_workflow_is_manual_only_and_never_receives_postgres_dsn():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "UIIP_DATABASE_URL" not in text
    assert "scripts/audit_rich_publication_source_contract.py" in text
    assert "scripts/rehearse_rich_publication_candidate.py" in text
    assert 'assert source["metals_certified_family_count"] == 11' in text
    assert 'assert source["metals_remaining_family_count"] == 0' in text
    assert 'assert candidate["publication_activated"] is False' in text
    assert "RICH_PUBLICATION_CANDIDATE_REHEARSAL=PASS" in text


def test_candidate_rehearsal_remains_non_persistent_while_central_publisher_is_now_scheduled():
    central = (ROOT / ".github" / "workflows" / "production-publication-cycle.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in central
    assert "schedule:" in central
    assert 'cron: "0 14 * * *"' in central
    assert "Resolve current governed source runs" in central
    assert "Re-certify current rich source contracts before any PostgreSQL connection" in central
