import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "config" / "presentation" / "metals_vehicle_ranking_evidence_v1.json"
DOC = ROOT / "docs" / "project_control" / "metals_four_factor_ranking_evidence_certification_v1.md"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_certified_source_run_and_artifact_are_exact():
    evidence = _load()
    assert evidence["authority_id"] == "UIP_NATIVE_METALS_VEHICLE_RANKING_EVIDENCE_V1"
    assert evidence["ranking_authority_id"] == "UIP_NATIVE_METALS_VEHICLE_RANKING_V1"
    assert evidence["ranking_methodology_version"] == "1.2.0"
    assert evidence["source_run_id"] == 34983030032
    assert evidence["source_head_sha"] == "1949dd03b4dd0d993b175763e44dd005c9e0d5a7"
    assert evidence["source_artifact_id"] == 10402526066
    assert evidence["source_artifact_digest"] == "sha256:708a76c8defea92b89c30618608d802d6399b17309a6fed70d02358a5df5d015"
    assert evidence["source_production_run_id"] == 34849676771
    assert evidence["source_production_artifact_id"] == 10349591580
    assert evidence["source_production_artifact_digest"] == "sha256:8c15699f4fa89f53039b4d1c4a5ea06882e7a9ea4ece4c1c984b69d7ae8edb7f"
    assert evidence["risk_output_sha256"] == "e44ffa3b57e55f0a36482db057fa6f4cf34d8f0cdf34cc67a6096d9feab59f09"


def test_certified_ordering_and_scores_match_rehearsal():
    evidence = _load()
    groups = {row["commodity_id"]: row for row in evidence["groups"]}
    assert groups["metals:commodity:gold"]["certified_order"] == ["GLD", "SGOL", "IAU"]
    assert groups["metals:commodity:gold"]["certified_leader"] == "GLD"
    assert groups["metals:commodity:silver"]["certified_order"] == ["SLV", "SIVR"]
    assert groups["metals:commodity:silver"]["certified_leader"] == "SLV"
    assert groups["metals:commodity:copper"]["certified_order"] == ["COPX", "CPER"]
    assert groups["metals:commodity:copper"]["certified_leader"] == "COPX"
    assert groups["metals:commodity:uranium"]["certified_order"] == ["URA", "URNM"]
    assert groups["metals:commodity:uranium"]["certified_leader"] == "URA"
    platinum = groups["metals:commodity:platinum"]
    assert platinum["state"] == "ONLY_REGISTERED_IMPLEMENTATION"
    assert platinum["certified_order"] == ["PPLT"]
    assert platinum["certified_leader"] is None

    assert groups["metals:commodity:gold"]["scores"] == {
        "GLD": 85.48544649732895,
        "SGOL": 77.88981280050356,
        "IAU": 73.67619141270399,
    }
    assert groups["metals:commodity:silver"]["scores"] == {
        "SLV": 89.53498202268918,
        "SIVR": 88.48041654419333,
    }
    assert groups["metals:commodity:copper"]["scores"] == {
        "COPX": 80.070548441811,
        "CPER": 76.77609981066686,
    }
    assert groups["metals:commodity:uranium"]["scores"] == {
        "URA": 84.25,
        "URNM": 60.9395767763326,
    }


def test_certification_remains_non_publishing_and_non_executing():
    evidence = _load()
    assert evidence["status"] == "METALS_FOUR_FACTOR_RANKING_EVIDENCE_CERTIFIED"
    assert evidence["ranking_evidence_certified"] is True
    assert evidence["preferred_vehicle_labels_authorized"] is False
    assert evidence["publication_write_authorized"] is False
    assert evidence["production_state_modification_authorized"] is False
    assert evidence["allocation_authorized"] is False
    assert evidence["position_sizing_authorized"] is False
    assert evidence["automatic_execution_authorized"] is False
    assert evidence["central_publication_cron_restoration_authorized"] is False


def test_document_records_separate_publication_gate():
    text = DOC.read_text(encoding="utf-8")
    assert "METALS_FOUR_FACTOR_RANKING_EVIDENCE = CERTIFIED" in text
    assert "PREFERRED_IMPLEMENTATION_CANDIDATE" in text
    assert "does not itself authorize publication" in text
    assert "upstream commodity-actionability gate" in text
