import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "config" / "presentation" / "metals_vehicle_ranking_evidence_v1.json"
DOC = ROOT / "docs" / "project_control" / "metals_four_factor_ranking_evidence_certification_v1.md"


def _load():
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


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
