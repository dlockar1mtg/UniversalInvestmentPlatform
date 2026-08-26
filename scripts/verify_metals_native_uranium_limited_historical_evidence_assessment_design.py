from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "native_uranium_limited_historical_evidence_assessment_design.json"


def main() -> int:
    payload = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    expected_outputs = {
        "limited_evidence_assessment_json",
        "forecast_state_sensitivity_summary_json",
        "independence_limitations_json",
        "remaining_validation_gap_register_json",
        "assessment_summary_json",
    }

    rules = payload["required_assessment_rules"]
    boundaries = payload["boundaries"]
    findings = payload["certified_outcome_findings"]

    result = {
        "status": "PASS",
        "read_only": True,
        "design_id_bound": payload["design_id"] == "METALS-NATIVE-URANIUM-LIMITED-HISTORICAL-EVIDENCE-ASSESSMENT-DESIGN-1",
        "source_head_bound": payload["source_governed_head"] == "195e259816feaf151e52c791d8e5cd773e61b2f1",
        "source_derivation_bound": payload["source_derivation_id"] == "METALS-NATIVE-URANIUM-REALIZED-OUTCOME-DERIVATION-1",
        "database_sha_bound": payload["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "outcome_values_bound": findings["native_as_of_value"] == 50.36 and findings["future_native_value"] == 55.91 and abs(findings["realized_return"] - 0.11020651310563934) < 1e-15,
        "independence_bound": findings["forecast_state_count"] == 8 and findings["distinct_native_outcome_event_count"] == 1 and findings["effective_independent_outcome_n"] == 1,
        "hold_bound": findings["reconstructed_recommendation"] == "HOLD",
        "assessment_rules_all_true": len(rules) == 16 and all(value is True for value in rules.values()),
        "required_outputs_exact": set(payload["required_outputs_for_future_execution"].keys()) == expected_outputs,
        "required_outputs_all_true": all(value is True for value in payload["required_outputs_for_future_execution"].values()),
        "all_execution_boundaries_closed": len(boundaries) == 17 and all(value is False for value in boundaries.values()),
        "decision_bound": payload["design_decision"] == "APPROVE_NATIVE_URANIUM_LIMITED_HISTORICAL_EVIDENCE_ASSESSMENT_DESIGN_FOR_EXECUTION_AUTHORIZATION_CONSIDERATION",
        "next_decision_bound": payload["next_decision"] == "AUTHORIZE_NATIVE_URANIUM_LIMITED_HISTORICAL_EVIDENCE_ASSESSMENT",
    }

    if not all(value is True for key, value in result.items() if key != "status"):
        result["status"] = "FAIL"

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
