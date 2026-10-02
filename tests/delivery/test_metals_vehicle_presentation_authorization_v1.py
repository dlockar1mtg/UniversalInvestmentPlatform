import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_presentation_authorization_v1.json"
DOC = ROOT / "docs" / "project_control" / "metals_vehicle_presentation_authorization_v1.md"


def _config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_platinum_is_only_registered_implementation_not_preferred_ranking():
    row = {r["commodity_id"]: r for r in _config()["commodities"]}["metals:commodity:platinum"]
    # A single vehicle is labelled only-registered and never preferred, whatever the
    # current recommendation and tactical state are.
    assert row["certified_vehicle_order"] == ["PPLT"]
    assert row["authorized_preferred_vehicle"] is None
    assert row["authorized_label"] == "ONLY_REGISTERED_IMPLEMENTATION"


def test_identity_and_safety_boundaries_remain_fail_closed():
    cfg = _config()
    gate = cfg["actionability_gate"]
    identity = cfg["identity_boundary"]
    assert gate["defensive_or_nonpositive_state_may_not_receive_preferred_buy_label"] is True
    assert gate["missing_or_conflicting_state_behavior"] == "FAIL_CLOSED"
    assert gate["ranking_may_not_override_commodity_recommendation"] is True
    assert identity["raw_tactical_source_contains_legacy_doubled_commodity_prefix"] is True
    assert identity["presentation_must_use_governed_metals_identity_bridge"] is True
    assert identity["incidental_source_id_normalization_authorized"] is False
    assert cfg["production_ranking_write_authorized"] is False
    assert cfg["portfolio_allocation_authorized"] is False
    assert cfg["position_sizing_authorized"] is False
    assert cfg["automatic_execution_authorized"] is False
    assert cfg["source_collection_schedule_change_authorized"] is False
    assert cfg["central_publication_cron_restoration_authorized"] is False


def test_document_records_silver_suppression_identity_boundary_and_paused_cron():
    text = DOC.read_text(encoding="utf-8")
    assert "Gold" in text and "GLD" in text
    assert "Copper" in text and "COPX" in text
    assert "Uranium" in text and "URA" in text
    assert "ONLY_REGISTERED_IMPLEMENTATION" in text
    assert "no `PREFERRED_IMPLEMENTATION_CANDIDATE` label is authorized" in text
    assert "doubled commodity prefix" in text
    assert "Incidental source-ID normalization remains prohibited" in text
    assert "central publication cron remains paused" in text.lower()
