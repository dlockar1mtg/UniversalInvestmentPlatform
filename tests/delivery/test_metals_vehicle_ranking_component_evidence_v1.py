import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "config" / "presentation" / "metals_vehicle_ranking_component_evidence_v1.json"
DOC = ROOT / "docs" / "project_control" / "metals_vehicle_ranking_component_evidence_certification_v1.md"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_singleton_platinum_does_not_gain_invented_competitive_scores():
    data = _load()
    platinum = next(g for g in data["groups"] if g["commodity_id"] == "metals:commodity:platinum")
    assert platinum["state"] == "ONLY_REGISTERED_IMPLEMENTATION"
    assert platinum["certified_leader"] is None
    pplt = platinum["vehicles"][0]
    assert pplt["ticker"] == "PPLT"
    assert "total_score" not in pplt
    assert "cost_efficiency_score" not in pplt
    assert "liquidity_implementation_friction_score" not in pplt
    assert "risk_efficiency_score" not in pplt


def test_safety_boundaries_remain_closed_and_documented():
    data = _load()
    assert data["presentation_only"] is True
    assert data["ranking_recalculated"] is False
    assert data["preferred_vehicle_labels_authorized"] is False
    assert data["publication_write_authorized"] is False
    assert data["allocation_authorized"] is False
    assert data["position_sizing_authorized"] is False
    assert data["automatic_execution_authorized"] is False
    assert data["central_publication_cron_restoration_authorized"] is False

    text = DOC.read_text(encoding="utf-8")
    assert "PPLT remains a singleton" in text
    assert "browser must not recalculate scores" in text
    assert "COPX is miners-equity exposure" in text
    assert "central publication cron restoration" in text
