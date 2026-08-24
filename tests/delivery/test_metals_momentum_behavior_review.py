from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "metals" / "momentum_behavior_review_contract.json"
SCRIPT = ROOT / "scripts" / "review_metals_momentum_feature_behavior.py"


def test_momentum_behavior_review_files_exist() -> None:
    assert CONTRACT.is_file()
    assert SCRIPT.is_file()


def test_momentum_behavior_review_remains_non_interpretive() -> None:
    contract_text = CONTRACT.read_text(encoding="utf-8")
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert '"momentum_interpretation_policy_authorized": false' in contract_text
    assert '"tactical_posture_authorized": false' in contract_text
    assert '"cross_domain_rank_authorized": false' in contract_text
    assert '"allocation_policy_authorized": false' in contract_text
    assert '"automatic_execution_authorized": false' in contract_text
    assert '"next_decision": "DESIGN_METALS_MOMENTUM_INTERPRETATION_VALIDATION"' in script_text


def test_momentum_behavior_review_covers_consistency_and_sign_patterns() -> None:
    script_text = SCRIPT.read_text(encoding="utf-8")
    assert "family_consistency" in script_text
    assert "cross_section" in script_text
    assert "sign_patterns" in script_text
    assert "gold_physical" in CONTRACT.read_text(encoding="utf-8")
    assert "silver_physical" in CONTRACT.read_text(encoding="utf-8")
