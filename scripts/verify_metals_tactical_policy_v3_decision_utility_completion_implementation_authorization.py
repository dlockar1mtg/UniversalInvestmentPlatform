from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "tactical_policy_v3_decision_utility_completion_implementation_authorization.json"


def main() -> int:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    expected_files = {
        "foundation/presentation/metals_tactical_projection.py",
        "config/presentation/dash_read_1_metals_tactical_extension.json",
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
    }
    assert data["authorization_id"] == "METALS-TACTICAL-POLICY-V3-DECISION-UTILITY-COMPLETION-IMPLEMENTATION-AUTHORIZATION-1"
    assert data["source_design_head"] == "caa82377a6bd5ac997bbf4d248c4fd091baedd54"
    assert data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert data["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_DECISION_UTILITY_COMPLETION_IMPLEMENTATION"
    assert set(data["authorized_files"]) == expected_files
    assert len(data["authorized_files"]) == 4
    assert all(data["required_behavior"].values())
    assert all(data["semantic_guardrails"].values())
    assert not any(data["boundaries"].values())
    assert data["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_DECISION_UTILITY_COMPLETION"
    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": data["authorization_id"],
        "authorization_decision": data["authorization_decision"],
        "authorized_file_count": len(data["authorized_files"]),
        "current_price_authorized": data["required_behavior"]["vehicle_current_price_uses_current_price_usd"],
        "price_history_authorized": data["required_behavior"]["vehicle_price_history_uses_close_usd"],
        "unadjusted_close_locked": data["required_behavior"]["history_semantics_remain_unadjusted_close"],
        "unsupported_fields_preserved": data["required_behavior"]["unsupported_fields_remain_explicitly_unavailable"],
        "analytical_database_write_authorized": data["boundaries"]["analytical_database_write_authorized"],
        "hosted_publication_write_authorized": data["boundaries"]["hosted_publication_write_authorized"],
        "main_deployment_authorized": data["boundaries"]["main_deployment_authorized"],
        "next_decision": data["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
