from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tactical_policy_validation_design_exists() -> None:
    assert (ROOT / "config" / "metals" / "tactical_policy_validation_design.json").exists()


def test_tactical_policy_design_is_fail_closed() -> None:
    text = (ROOT / "scripts" / "verify_metals_tactical_policy_validation_design.py").read_text(encoding="utf-8")
    assert "METALS-TACTICAL-POLICY-VALIDATION-DESIGN-1" in text
    assert "metals:vehicle:BIL" in text
    assert "reference/control asset entered tactical opportunity universe" in text
    assert "historical_walk_forward_required" in text
    assert "threshold_lock_required_before_final_validation" in text


def test_tactical_policy_design_preserves_governance() -> None:
    text = (ROOT / "scripts" / "verify_metals_tactical_policy_validation_design.py").read_text(encoding="utf-8")
    assert '"tactical_posture_authorized": False' in text
    assert '"cross_domain_rank_authorized": False' in text
    assert '"allocation_policy_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text
    assert '"production_database_write_executed": False' in text
