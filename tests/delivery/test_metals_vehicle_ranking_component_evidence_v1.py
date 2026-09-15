import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "config" / "presentation" / "metals_vehicle_ranking_component_evidence_v1.json"
DOC = ROOT / "docs" / "project_control" / "metals_vehicle_ranking_component_evidence_certification_v1.md"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_component_evidence_is_exactly_pinned_to_certified_rehearsal():
    data = _load()
    assert data["authority_id"] == "UIP_NATIVE_METALS_VEHICLE_RANKING_COMPONENT_EVIDENCE_V1"
    assert data["ranking_authority_id"] == "UIP_NATIVE_METALS_VEHICLE_RANKING_V1"
    assert data["ranking_methodology_version"] == "1.2.0"
    assert data["source_run_id"] == 34983030032
    assert data["source_artifact_id"] == 10402526066
    assert data["source_artifact_digest"] == "sha256:708a76c8defea92b89c30618608d802d6399b17309a6fed70d02358a5df5d015"
    assert data["rehearsal_json_sha256"] == "e2499f90ade51d1f396af327ee196baaf46ad7522d88fc1228fa5c99b49705b7"
    assert data["risk_output_sha256"] == "e44ffa3b57e55f0a36482db057fa6f4cf34d8f0cdf34cc67a6096d9feab59f09"
    assert data["adv_output_sha256"] == "7ea64b5b975fea4c51c8fdb3e00fec83bcf1527e6b65a2eb2a23f64775913d65"


def test_weights_and_exact_vehicle_universe_are_preserved():
    data = _load()
    assert data["weights"] == {
        "exposure_fidelity": 0.35,
        "cost_efficiency": 0.25,
        "liquidity_implementation_friction": 0.25,
        "risk_efficiency": 0.15,
    }
    vehicles = [v for g in data["groups"] for v in g["vehicles"]]
    assert {v["ticker"] for v in vehicles} == {
        "GLD", "SGOL", "IAU", "SLV", "SIVR", "PPLT", "COPX", "CPER", "URA", "URNM"
    }
    assert len(vehicles) == 10


def test_certified_ordering_and_gold_component_values_are_exact():
    data = _load()
    groups = {g["commodity_id"]: g for g in data["groups"]}
    assert groups["metals:commodity:gold"]["certified_order"] == ["GLD", "SGOL", "IAU"]
    assert groups["metals:commodity:silver"]["certified_order"] == ["SLV", "SIVR"]
    assert groups["metals:commodity:platinum"]["certified_order"] == ["PPLT"]
    assert groups["metals:commodity:copper"]["certified_order"] == ["COPX", "CPER"]
    assert groups["metals:commodity:uranium"]["certified_order"] == ["URA", "URNM"]

    gold = {v["ticker"]: v for v in groups["metals:commodity:gold"]["vehicles"]}
    assert gold["GLD"]["total_score"] == 85.48544649732895
    assert gold["GLD"]["exposure_fidelity_score"] == 100.0
    assert gold["GLD"]["cost_efficiency_score"] == 42.5
    assert gold["GLD"]["liquidity_implementation_friction_score"] == 100.0
    assert gold["GLD"]["risk_efficiency_score"] == 99.06964331552635
    assert gold["GLD"]["average_dollar_volume_usd"] == 3758288420.8526664
    assert gold["GLD"]["bid_ask_spread_bps"] == 0.4896385164486847


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
