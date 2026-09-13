from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_metals_uncertainty_adjusted_authority_design.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-uncertainty-adjusted-authority-design-audit.yml"
DOC = ROOT / "docs" / "project_control" / "metals_uncertainty_adjusted_authority_design_v1.md"


def test_uncertainty_adjusted_design_audit_is_manual_read_only_and_fail_closed():
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
    assert "AUTHORIZE_UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1_DESIGN" in script
    assert "DO_NOT_AUTHORIZE_UNCERTAINTY_ADJUSTED_V1_UNTIL_MISSING_AUTHORITY_IS_RESOLVED" in script
    assert "DESIGN AUDIT ONLY" in doc


def test_uncertainty_adjusted_design_preserves_current_authority_boundaries():
    script = SCRIPT.read_text(encoding="utf-8")
    doc = DOC.read_text(encoding="utf-8")

    assert "metals_uncertainty_adjusted" in script
    assert "METALS_NATIVE_REGIME_PROBABILITY_V1_PASS" in script
    assert "METALS_NATIVE_RISK_V1_PASS" in script
    assert 'risk.get("scope") == "VEHICLE_ONLY"' in script
    assert "METALS_NATIVE_RECOMMENDATION_CHANGE_V1_PASS" in script
    assert '"candidate_authority_boundary": "BENCHMARK_COMMODITY_ASSET_BY_FORECAST_HORIZON"' in script
    assert "vehicle-to-commodity mapping" in script
    assert "statistically calibrated" in script
    assert "restored 32" in doc
    assert "cross-asset ranking" in doc
    assert "automatic execution" in doc


def test_workflow_consumes_latest_certified_production_evidence_only():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "metals-production-cycle.yml/runs?branch=main&status=success" in workflow
    assert "native_cycle/latest.json" in workflow
    assert "native_regime_probability_v1/manifest.json" in workflow
    assert "native_risk_v1/manifest.json" in workflow
    assert "native_recommendation_change_v1/manifest.json" in workflow
    assert "audit_metals_rich_lineage.py" in workflow
    assert "audit_metals_uncertainty_adjusted_authority_design.py" in workflow
    assert "metals-uncertainty-adjusted-authority-design-${{ github.run_id }}" in workflow
