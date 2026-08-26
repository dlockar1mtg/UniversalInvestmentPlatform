from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN_PATH = ROOT / "config" / "metals" / "native_uranium_limited_historical_evidence_assessment_design.json"
AUTH_PATH = ROOT / "config" / "metals" / "native_uranium_limited_historical_evidence_assessment_execution_authorization.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    design = load(DESIGN_PATH)
    auth = load(AUTH_PATH)
    expected_outputs = sorted(design["required_outputs_for_future_execution"].keys())
    auth_outputs = sorted(auth["required_outputs"].keys())
    boundaries = auth["authorization_boundary"]
    open_boundaries = sorted(k for k, v in boundaries.items() if v is True)
    expected_open = sorted([
        "limited_historical_evidence_assessment_authorized",
        "local_evidence_artifact_write_authorized",
    ])
    checks = {
        "read_only_inputs": True,
        "authorization_id_bound": auth["authorization_id"] == "METALS-NATIVE-URANIUM-LIMITED-HISTORICAL-EVIDENCE-ASSESSMENT-EXECUTION-AUTHORIZATION-1",
        "source_design_bound": auth["source_design_id"] == design["design_id"],
        "source_head_bound": auth["source_design_head"] == "992817f8056ff4b4f6dd480d5f40dabc7e9b2246",
        "source_derivation_bound": auth["source_derivation_id"] == design["source_derivation_id"],
        "database_sha_bound": auth["source_database_sha256"] == design["source_database_sha256"],
        "scope_bound": auth["authorized_assessment_scope"]["asset_id"] == "METALS:COMMODITY:URANIUM",
        "outcome_values_bound": abs(float(auth["authorized_assessment_scope"]["realized_return"]) - 0.11020651310563934) <= 1e-15,
        "independence_bound": int(auth["authorized_assessment_scope"]["effective_independent_outcome_n"]) == 1,
        "hold_bound": auth["authorized_assessment_scope"]["reconstructed_recommendation"] == "HOLD",
        "execution_behavior_all_true": all(v is True for v in auth["required_execution_behavior"].values()),
        "required_outputs_exact": auth_outputs == expected_outputs,
        "required_outputs_all_true": all(v is True for v in auth["required_outputs"].values()),
        "assessment_authorized": boundaries["limited_historical_evidence_assessment_authorized"] is True,
        "local_evidence_write_authorized": boundaries["local_evidence_artifact_write_authorized"] is True,
        "hosted_read_only_remains_closed": boundaries["hosted_read_only_access_authorized"] is False,
        "all_other_execution_boundaries_closed": open_boundaries == expected_open,
        "design_outputs_match": auth_outputs == expected_outputs,
        "decision_bound": auth["authorization_decision"] == "AUTHORIZE_NATIVE_URANIUM_LIMITED_HISTORICAL_EVIDENCE_ASSESSMENT",
        "next_decision_bound": auth["next_decision"] == "EXECUTE_AND_CERTIFY_NATIVE_URANIUM_LIMITED_HISTORICAL_EVIDENCE_ASSESSMENT",
    }
    result = {**checks, "status": "PASS" if all(checks.values()) else "FAIL"}
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
