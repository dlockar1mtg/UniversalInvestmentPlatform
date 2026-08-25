from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "tactical_policy_v3_decision_utility_completion_design.json"


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))

    assert data["design_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-COMPLETION-DESIGN-1"
    assert data["source_jsonl_audit_head"] == "3a1117c358f01f7940ed0490bcf7845c48f7a65e"
    assert data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert data["objective"] == "COMPLETE_METALS_DECISION_UTILITY_FROM_RESOLVED_GOVERNED_AUTHORITIES"

    auth = data["resolved_authorities"]
    assert auth["vehicle_current_price"]["source"] == "metals_current_price.jsonl"
    assert auth["vehicle_current_price"]["value"] == "current_price_usd"
    assert auth["vehicle_current_price"]["coverage_rows"] == 11
    assert auth["vehicle_price_history"]["source"] == "metals_price_history.jsonl"
    assert auth["vehicle_price_history"]["value"] == "close_usd"
    assert auth["vehicle_price_history"]["coverage_rows"] == 8283
    assert auth["vehicle_price_history"]["price_semantics"] == "UNADJUSTED_CLOSE"
    assert auth["commodity_expected_return"]["horizons_months"] == [3, 6, 12, 24]

    assert all(data["presentation_requirements"].values())
    assert all(data["unsupported_fields"].values())
    assert all(data["semantic_guardrails"].values())

    assert data["candidate_implementation_files"] == [
        "foundation/presentation/metals_tactical_projection.py",
        "config/presentation/dash_read_1_metals_tactical_extension.json",
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
    ]
    assert not any(data["boundaries"].values())
    assert data["design_decision"] == "APPROVE_METALS_DECISION_UTILITY_COMPLETION_DESIGN_FOR_IMPLEMENTATION_CONSIDERATION"
    assert data["next_decision"] == "AUTHORIZE_METALS_DECISION_UTILITY_COMPLETION_IMPLEMENTATION"

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "design_id": data["design_id"],
        "current_price_authority_resolved": True,
        "dated_history_authority_resolved": True,
        "history_semantics_unadjusted_close": True,
        "forecast_bounds_remain_unavailable": True,
        "full_rationale_remains_unavailable": True,
        "implementation_authorized": False,
        "next_decision": data["next_decision"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
