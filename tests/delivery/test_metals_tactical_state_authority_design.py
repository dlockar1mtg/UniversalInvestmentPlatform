from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_metals_tactical_state_authority_design.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-tactical-state-authority-design-audit.yml"
DOC = ROOT / "docs" / "project_control" / "metals_tactical_state_authority_design_v1.md"


def test_tactical_state_design_audit_is_manual_read_only_and_fail_closed():
    script = SCRIPT.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "UIIP_DATABASE_URL" in workflow
    assert "SET TRANSACTION READ ONLY" in script
    assert '"postgres_write_performed": False' in script
    assert '"source_collection_performed": False' in script
    assert '"publication_staged": False' in script
    assert '"publication_activated": False' in script
    assert "INSERT " not in script
    assert "UPDATE " not in script
    assert "DELETE " not in script
    assert "AUTHORIZE_UIP_NATIVE_METALS_TACTICAL_STATE_V1_DESIGN" in script
    assert "DO_NOT_AUTHORIZE_TACTICAL_STATE_V1_UNTIL_MISSING_AUTHORITY_IS_RESOLVED" in script
    assert "DESIGN AUDIT ONLY" in doc


def test_tactical_state_design_preserves_subject_and_missing_authority_boundaries():
    script = SCRIPT.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert '((lineage.get("record_types") or {}).get("tactical_state") or {})' in script
    assert "METALS_NATIVE_REGIME_PROBABILITY_V1_PASS" in script
    assert "METALS_NATIVE_UNCERTAINTY_ADJUSTED_V1_PASS" in script
    assert "METALS_NATIVE_RISK_V1_PASS" in script
    assert 'risk.get("scope") == "VEHICLE_ONLY"' in script
    assert "METALS_NATIVE_RECOMMENDATION_CHANGE_V1_PASS" in script
    assert '"candidate_authority_boundary": "UNRESOLVED_SCOPE_REQUIRES_EXPLICIT_GOVERNANCE_BEFORE_BUILDER"' in script
    assert "SEPARATE_COMMODITY_AND_VEHICLE_AUTHORITIES" in script
    assert "missing authority must remain missing rather than defaulting to HOLD or WAIT" in script
    assert "vehicle-to-commodity projection" in script
    assert "restored tactical-state rows" in doc
    assert "cross-asset ranking" in doc
    assert "automatic execution" in doc


def test_workflow_consumes_latest_certified_production_evidence_only():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "metals-production-cycle.yml/runs?branch=main&status=success" in workflow
    assert "native_cycle/latest.json" in workflow
    assert "native_regime_probability_v1/manifest.json" in workflow
    assert "native_uncertainty_adjusted_v1/manifest.json" in workflow
    assert "native_risk_v1/manifest.json" in workflow
    assert "native_recommendation_change_v1/manifest.json" in workflow
    assert "audit_metals_rich_lineage.py" in workflow
    assert "audit_metals_tactical_state_authority_design.py" in workflow
    assert "metals-tactical-state-authority-design-${{ github.run_id }}" in workflow
