import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config" / "presentation" / "metals_vehicle_presentation_authorization_v1.json"
DOC = ROOT / "docs" / "project_control" / "metals_vehicle_presentation_authorization_v1.md"


def _config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_authority_pins_certified_ranking_and_tactical_sources():
    cfg = _config()
    assert cfg["authority_id"] == "UIP_NATIVE_METALS_VEHICLE_PRESENTATION_AUTHORIZATION_V1"
    assert cfg["ranking_evidence_authority_id"] == "UIP_NATIVE_METALS_VEHICLE_RANKING_EVIDENCE_V1"
    assert cfg["ranking_methodology_version"] == "1.2.0"
    assert cfg["ranking_source_run_id"] == 34983030032
    assert cfg["ranking_source_artifact_id"] == 10402526066
    assert cfg["ranking_source_artifact_digest"] == "sha256:708a76c8defea92b89c30618608d802d6399b17309a6fed70d02358a5df5d015"
    assert cfg["commodity_state_authority_id"] == "UIP_NATIVE_METALS_TACTICAL_STATE_V1"
    assert cfg["commodity_state_source_production_run_id"] == 34849676771
    assert cfg["commodity_state_output_sha256"] == "615757072a8efc23b4553870abc439583e6a8723bdad4f286c3e991f33e19b0e"


def test_preferred_labels_are_authorized_only_for_supportive_actionable_groups():
    cfg = _config()
    rows = {row["commodity_id"]: row for row in cfg["commodities"]}

    assert rows["metals:commodity:gold"]["authorized_preferred_vehicle"] == "GLD"
    assert rows["metals:commodity:copper"]["authorized_preferred_vehicle"] == "COPX"
    assert rows["metals:commodity:uranium"]["authorized_preferred_vehicle"] == "URA"
    for commodity in ("gold", "copper", "uranium"):
        row = rows[f"metals:commodity:{commodity}"]
        assert row["recommendation"] in {"BUY", "STRONG_BUY"}
        assert row["tactical_state"] == "TACTICAL_SUPPORTIVE"
        assert row["authorized_label"] == "PREFERRED_IMPLEMENTATION_CANDIDATE"


def test_platinum_is_only_registered_implementation_not_preferred_ranking():
    row = {r["commodity_id"]: r for r in _config()["commodities"]}["metals:commodity:platinum"]
    assert row["recommendation"] == "BUY"
    assert row["tactical_state"] == "TACTICAL_SUPPORTIVE"
    assert row["certified_vehicle_order"] == ["PPLT"]
    assert row["authorized_preferred_vehicle"] is None
    assert row["authorized_label"] == "ONLY_REGISTERED_IMPLEMENTATION"


def test_silver_defensive_state_suppresses_preferred_buy_label():
    row = {r["commodity_id"]: r for r in _config()["commodities"]}["metals:commodity:silver"]
    assert row["recommendation"] == "REDUCE"
    assert row["tactical_state"] == "TACTICAL_DEFENSIVE"
    assert row["certified_vehicle_order"] == ["SLV", "SIVR"]
    assert row["presentation_state"] == "RANKING_INFORMATIONAL_ONLY_UPSTREAM_DEFENSIVE"
    assert row["authorized_preferred_vehicle"] is None
    assert row["authorized_label"] is None


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
