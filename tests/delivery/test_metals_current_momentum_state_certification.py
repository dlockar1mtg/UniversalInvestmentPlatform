from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "metals" / "momentum_interpretation_policy_contract.json"
SCRIPT = ROOT / "scripts" / "certify_metals_current_momentum_states.py"


def test_contract_and_script_exist() -> None:
    assert CONTRACT.exists()
    assert SCRIPT.exists()


def test_semantic_scope_is_descriptive() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert '"momentum_interpretation_policy_authorized": true' in text
    assert '"state_is_descriptive_not_predictive": true' in text
    assert '"tactical_posture_authorized": false' in text
    assert '"automatic_execution_authorized": false' in text


def test_script_is_read_only_and_fail_closed() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'BEGIN READ ONLY' in text
    assert 'METALS-MOMENTUM-INTERPRETATION-1' in text
    assert 'DESCRIPTIVE_CURRENT_MARKET_STATE_NOT_FORWARD_RETURN_FORECAST' in text or 'semantic_scope' in text
    assert 'tactical_posture_authorized": False' in text
    assert 'automatic_execution_authorized": False' in text
    assert 'UPDATE ' not in text
    assert 'INSERT ' not in text
    assert 'DELETE ' not in text
