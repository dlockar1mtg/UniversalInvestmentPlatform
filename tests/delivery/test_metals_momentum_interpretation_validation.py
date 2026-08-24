from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "metals" / "momentum_interpretation_validation_contract.json"
SCRIPT = ROOT / "scripts" / "validate_metals_momentum_interpretation.py"


def test_validation_contract_and_script_exist() -> None:
    assert CONTRACT.is_file()
    assert SCRIPT.is_file()


def test_validation_contract_is_fail_closed() -> None:
    import json

    payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert payload["contract_id"] == "METALS-MOMENTUM-VALIDATION-1"
    assert payload["source_authority"] == "METALS-MOMENTUM-1"
    controls = payload["controls"]
    assert controls["candidate_state_evaluation_authorized"] is True
    for key in (
        "production_database_write_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "momentum_interpretation_policy_authorized",
        "tactical_posture_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        assert controls[key] is False


def test_validation_script_preserves_policy_boundary() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert '"momentum_interpretation_policy_authorized": False' in text
    assert '"tactical_posture_authorized": False' in text
    assert '"automatic_execution_authorized": False' in text
    assert '"next_decision": "REVIEW_METALS_MOMENTUM_INTERPRETATION_VALIDATION"' in text
