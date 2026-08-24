from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_forward_validation_contract_exists() -> None:
    path = ROOT / "config" / "metals" / "momentum_state_forward_validation_contract.json"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert '"contract_id": "METALS-MOMENTUM-FORWARD-VALIDATION-1"' in text
    assert '"candidate_state_forward_validation_authorized": true' in text
    assert '"momentum_interpretation_policy_authorized": false' in text
    assert '"tactical_posture_authorized": false' in text


def test_forward_validation_script_is_read_only_and_uses_forward_windows() -> None:
    path = ROOT / "scripts" / "validate_metals_momentum_state_forward_behavior.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert 'BEGIN READ ONLY' in text
    assert '"1m": 21' not in text  # windows come from governed contract, not script literals
    assert 'state_forward_summary' in text
    assert 'positive_rate_pct' in text
    assert 'median_pct' in text
    assert 'production_database_write_executed": False' in text
    assert 'momentum_interpretation_policy_authorized": False' in text
    assert 'tactical_posture_authorized": False' in text


def test_forward_validation_preserves_candidate_state_boundary() -> None:
    text = (ROOT / "scripts" / "validate_metals_momentum_state_forward_behavior.py").read_text(encoding="utf-8")
    for state in (
        "ESTABLISHED_UPWARD",
        "STRENGTHENING_UPWARD",
        "WEAKENING_UPWARD",
        "NEUTRAL_CONSOLIDATING",
        "STRENGTHENING_DOWNWARD",
        "ESTABLISHED_DOWNWARD",
        "POTENTIALLY_REVERSING",
    ):
        assert state in text
    assert 'next_decision": "REVIEW_METALS_MOMENTUM_STATE_FORWARD_VALIDATION"' in text
