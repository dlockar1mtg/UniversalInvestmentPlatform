from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "audit_metals_risk_authority_design.py"
WORKFLOW = ROOT / ".github" / "workflows" / "metals-risk-authority-design-audit.yml"


def test_risk_design_audit_is_read_only_and_manual():
    script = SCRIPT.read_text(encoding="utf-8")
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "AUTHORIZE_UIP_NATIVE_METALS_RISK_V1_DESIGN" in script
    assert "DO_NOT_AUTHORIZE_RISK_V1_UNTIL_MISSING_SEMANTICS_ARE_GOVERNED" in script
    assert '"postgres_write_performed": False' in script
    assert '"publication_staged": False' in script
    assert '"publication_activated": False' in script
    assert '"legacy_equivalent": False' in script
    assert "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1" in script
    assert "UNADJUSTED_CLOSE" in script

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "metals-production-cycle.yml" in workflow
    assert "audit_metals_rich_lineage.py" in workflow
    assert "audit_metals_risk_authority_design.py" in workflow
    assert "restore_rich_presentation_publication.py" not in workflow
    assert "production-publication-cycle.yml" not in workflow


def test_risk_design_audit_requires_methodology_governance_before_builder():
    script = SCRIPT.read_text(encoding="utf-8")

    required = [
        "lookback window(s)",
        "minimum observation count",
        "return convention (simple vs log)",
        "annualization convention",
        "VaR confidence level and method if VaR is included",
        "vehicle-only authority boundary; no silent vehicle-to-commodity projection",
    ]
    for phrase in required:
        assert phrase in script
