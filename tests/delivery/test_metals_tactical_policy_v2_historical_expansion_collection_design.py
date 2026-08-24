import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "metals" / "tactical_policy_v2_historical_expansion_collection_design.json"
VERIFIER = ROOT / "scripts" / "verify_metals_tactical_policy_v2_historical_expansion_collection_design.py"


def load_contract():
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def test_collection_boundary_is_exact_and_disjoint():
    contract = load_contract()
    boundary = contract["collection_boundary"]
    assert boundary["common_start_date"] == "2019-12-04"
    assert boundary["common_end_date"] == "2023-08-21"
    assert boundary["existing_certified_history_start_date"] == "2023-08-22"
    assert boundary["expected_common_observation_count"] == 934
    assert boundary["interval_disjoint_from_v1"] is True


def test_all_governed_symbols_are_locked():
    contract = load_contract()
    assert contract["source_contract"]["symbols"] == [
        "BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"
    ]
    assert contract["collection_boundary"]["vehicle_count"] == 11
    assert contract["collection_boundary"]["opportunity_vehicle_count"] == 10
    assert contract["collection_boundary"]["reference_control_asset_id"] == "metals:vehicle:BIL"


def test_artifact_contract_is_hash_bound_and_fail_closed():
    artifacts = load_contract()["artifact_contract"]
    assert artifacts["sha256_required_for_every_artifact"] is True
    assert artifacts["manifest_must_bind_candidate_design_id"] is True
    assert artifacts["manifest_must_bind_collection_boundary"] is True
    assert artifacts["manifest_must_bind_symbols"] is True
    assert artifacts["manifest_must_bind_source_provider"] is True
    assert artifacts["missing_rows_may_not_be_synthesized"] is True
    assert artifacts["common_calendar_intersection_required"] is True
    assert artifacts["exact_common_observation_count_must_reconcile"] is True


def test_collection_is_outcome_blind():
    blindness = load_contract()["outcome_blindness"]
    assert blindness["candidate_postures_may_not_be_calculated_during_collection"] is True
    assert blindness["forward_returns_may_not_be_calculated_during_collection"] is True
    assert blindness["mae_or_mfe_may_not_be_calculated_during_collection"] is True
    assert blindness["policy_pass_fail_checks_may_not_be_calculated_during_collection"] is True
    assert blindness["new_validation_outcomes_may_not_be_inspected_during_collection"] is True
    assert blindness["raw_price_rows_may_be_persisted_as_collection_artifact"] is True


def test_collection_execution_is_not_authorized_yet():
    controls = load_contract()["controls"]
    assert controls["historical_expansion_collection_design_authorized"] is True
    assert controls["historical_expansion_execution_authorized"] is False
    assert controls["validation_package_review_authorized"] is False
    assert controls["historical_candidate_evaluation_authorized"] is False
    assert controls["new_validation_outcome_inspection_authorized"] is False
    assert controls["tactical_posture_authorized"] is False
    assert controls["production_database_write_authorized"] is False


def test_verifier_does_not_import_or_calculate_market_outcomes():
    text = VERIFIER.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "yfinance" not in lowered
    assert "forward_return" not in lowered
    assert "maximum_adverse_excursion" not in lowered
    assert "maximum_favorable_excursion" not in lowered
    assert "candidate_posture" not in lowered
