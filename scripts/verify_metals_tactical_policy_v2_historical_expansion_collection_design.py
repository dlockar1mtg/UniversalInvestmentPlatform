from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_historical_expansion_collection_design.json"

EXPECTED_SYMBOLS = ["BIL", "COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"]
EXPECTED_PRICE_FIELDS = ["open_usd", "high_usd", "low_usd", "close_usd", "adjusted_close_usd", "volume"]


def main() -> int:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    boundary = contract["collection_boundary"]
    source = contract["source_contract"]
    artifacts = contract["artifact_contract"]
    blindness = contract["outcome_blindness"]
    controls = contract["controls"]

    assert contract["design_id"] == "METALS-TACTICAL-POLICY-V2-HISTORICAL-EXPANSION-COLLECTION-DESIGN-1"
    assert contract["source_feasibility_audit"] == "METALS-TACTICAL-POLICY-V2-HISTORICAL-EXPANSION-FEASIBILITY-AUDIT-1"
    assert contract["source_candidate_rule_design"] == "METALS-TACTICAL-POLICY-V2-CANDIDATE-RULE-DESIGN-1"

    assert boundary["common_start_date"] == "2019-12-04"
    assert boundary["common_end_date"] == "2023-08-21"
    assert int(boundary["expected_common_observation_count"]) == 934
    assert boundary["existing_certified_history_start_date"] == "2023-08-22"
    assert boundary["interval_disjoint_from_v1"] is True
    assert int(boundary["vehicle_count"]) == 11
    assert int(boundary["opportunity_vehicle_count"]) == 10
    assert boundary["reference_control_asset_id"] == "metals:vehicle:BIL"

    assert source["provider"] == "yfinance"
    assert source["symbols"] == EXPECTED_SYMBOLS
    assert source["price_fields_required"] == EXPECTED_PRICE_FIELDS
    assert source["daily_interval_required"] is True
    assert source["date_field_required"] == "observation_date"
    assert source["source_timestamp_or_run_identity_required"] is True
    assert source["provider_metadata_required"] is True

    assert artifacts["package_id"] == "metals-v2-validation-history-20191204-20230821"
    assert artifacts["history_filename"] == "metals_v2_validation_history.jsonl"
    assert artifacts["manifest_filename"] == "manifest.json"
    assert artifacts["coverage_filename"] == "coverage.json"
    assert artifacts["sha256_required_for_every_artifact"] is True
    assert artifacts["manifest_must_bind_candidate_design_id"] is True
    assert artifacts["manifest_must_bind_collection_boundary"] is True
    assert artifacts["manifest_must_bind_symbols"] is True
    assert artifacts["manifest_must_bind_source_provider"] is True
    assert artifacts["missing_rows_may_not_be_synthesized"] is True
    assert artifacts["common_calendar_intersection_required"] is True
    assert artifacts["exact_common_observation_count_must_reconcile"] is True

    assert blindness["candidate_postures_may_not_be_calculated_during_collection"] is True
    assert blindness["forward_returns_may_not_be_calculated_during_collection"] is True
    assert blindness["mae_or_mfe_may_not_be_calculated_during_collection"] is True
    assert blindness["policy_pass_fail_checks_may_not_be_calculated_during_collection"] is True
    assert blindness["new_validation_outcomes_may_not_be_inspected_during_collection"] is True
    assert blindness["raw_price_rows_may_be_persisted_as_collection_artifact"] is True

    assert controls["historical_expansion_collection_design_authorized"] is True
    assert controls["historical_expansion_execution_authorized"] is False
    assert controls["validation_package_review_authorized"] is False
    assert controls["historical_candidate_evaluation_authorized"] is False
    assert controls["new_validation_outcome_inspection_authorized"] is False
    assert controls["tactical_posture_authorized"] is False
    assert controls["presentation_activation_authorized"] is False
    assert controls["production_database_write_authorized"] is False
    assert controls["forecast_refresh_authorized"] is False
    assert controls["model_retraining_authorized"] is False
    assert controls["cross_domain_rank_authorized"] is False
    assert controls["allocation_policy_authorized"] is False
    assert controls["automatic_execution_authorized"] is False
    assert controls["missing_authority_may_be_synthesized"] is False

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id": contract["design_id"],
        "source_feasibility_audit": contract["source_feasibility_audit"],
        "source_candidate_rule_design": contract["source_candidate_rule_design"],
        "common_start_date": boundary["common_start_date"],
        "common_end_date": boundary["common_end_date"],
        "expected_common_observation_count": boundary["expected_common_observation_count"],
        "vehicle_count": boundary["vehicle_count"],
        "opportunity_vehicle_count": boundary["opportunity_vehicle_count"],
        "reference_control_count": 1,
        "source_provider": source["provider"],
        "package_id": artifacts["package_id"],
        "candidate_rules_locked_before_collection": True,
        "new_validation_interval_disjoint_required": boundary["interval_disjoint_from_v1"],
        "outcome_blind_collection_required": True,
        "historical_expansion_execution_authorized": controls["historical_expansion_execution_authorized"],
        "validation_package_review_authorized": controls["validation_package_review_authorized"],
        "historical_candidate_evaluation_authorized": controls["historical_candidate_evaluation_authorized"],
        "new_validation_outcome_inspection_authorized": controls["new_validation_outcome_inspection_authorized"],
        "tactical_posture_authorized": controls["tactical_posture_authorized"],
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": controls["cross_domain_rank_authorized"],
        "allocation_policy_authorized": controls["allocation_policy_authorized"],
        "automatic_execution_authorized": controls["automatic_execution_authorized"],
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
