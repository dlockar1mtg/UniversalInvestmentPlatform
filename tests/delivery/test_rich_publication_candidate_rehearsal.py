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


def test_projection_covers_exactly_ten_certified_metals_families():
    module = _load_projection()
    assert set(module.FAMILY_PROJECTION) == {
        "current_price",
        "price_history",
        "data_freshness",
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
    assert module.FAMILY_PROJECTION["risk"]["record_type"] == "risk"
    assert module.FAMILY_PROJECTION["tactical_state"]["record_type"] == "tactical_state"


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
    assert 'assert source["metals_certified_family_count"] == 10' in text
    assert 'assert source["metals_remaining_family_count"] == 0' in text
    assert 'assert candidate["publication_activated"] is False' in text
    assert "RICH_PUBLICATION_CANDIDATE_REHEARSAL=PASS" in text


def test_candidate_rehearsal_does_not_modify_central_publisher():
    central = (ROOT / ".github" / "workflows" / "production-publication-cycle.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in central
    assert "schedule:" not in central
