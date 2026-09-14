import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "config" / "presentation" / "metals_vehicle_cost_evidence_snapshot_v1.json"
SCRIPT = ROOT / "scripts" / "audit_metals_vehicle_cost_evidence_v1.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-vehicle-cost-evidence-v1-rehearsal.yml"


def test_snapshot_covers_exact_vehicle_universe_and_keeps_cper_missing():
    doc = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    rows = {row["ticker"]: row for row in doc["vehicles"]}
    assert set(rows) == {"GLD","IAU","SGOL","SLV","SIVR","PPLT","CPER","COPX","URA","URNM"}
    assert len(rows) == 10
    assert rows["CPER"]["expense_ratio_pct"] is None
    assert rows["CPER"]["status"] == "UNRESOLVED_OFFICIAL_RENDERED_VALUE"
    assert doc["ranking_authority"] is False


def test_known_issuer_cost_observations_are_versioned():
    rows = {row["ticker"]: row for row in json.loads(SNAPSHOT.read_text())["vehicles"]}
    assert rows["GLD"]["expense_ratio_pct"] == 0.40
    assert rows["IAU"]["expense_ratio_pct"] == 0.25
    assert rows["SGOL"]["expense_ratio_pct"] == 0.17
    assert rows["SLV"]["expense_ratio_pct"] == 0.50
    assert rows["SIVR"]["expense_ratio_pct"] == 0.30
    assert rows["PPLT"]["expense_ratio_pct"] == 0.60
    assert rows["COPX"]["expense_ratio_pct"] == 0.65
    assert rows["URA"]["expense_ratio_pct"] == 0.69
    assert rows["URNM"]["expense_ratio_pct"] == 0.75


def test_audit_is_fail_closed_and_read_only():
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"preferred_vehicle_ranking_ready": False' in text
    assert '"network_collection_performed": False' in text
    assert '"publication_write_performed": False' in text
    assert '"ranking_created": False' in text
    assert "CPER_expense_ratio" in text


def test_workflow_is_manual_only():
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "schedule:" not in text
    assert "audit_metals_vehicle_cost_evidence_v1.py" in text
