from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/metals/tactical_policy_v3_presentation_data_completeness_remediation_implementation_authorization.json"
EXPECTED_ID = "METALS-TACTICAL-POLICY-V3-PRESENTATION-DATA-COMPLETENESS-REMEDIATION-IMPLEMENTATION-AUTHORIZATION-1"
EXPECTED_DECISION = "AUTHORIZE_BOUNDED_METALS_PRESENTATION_DATA_COMPLETENESS_REMEDIATION_IMPLEMENTATION"
EXPECTED_NEXT = "IMPLEMENT_AND_CERTIFY_METALS_PRESENTATION_DATA_COMPLETENESS_REMEDIATION"
EXPECTED_FILES = {
    "foundation/presentation/metals_tactical_projection.py",
    "config/presentation/dash_read_1_metals_tactical_extension.json",
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
}


def main() -> None:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    assert payload["authorization_id"] == EXPECTED_ID
    assert payload["authorization_decision"] == EXPECTED_DECISION
    assert payload["next_decision"] == EXPECTED_NEXT
    assert set(payload["authorized_files"]) == EXPECTED_FILES
    assert all(payload["required_behavior"].values())
    assert all(value is False for value in payload["boundaries"].values())
    unresolved = set(payload["unresolved_fields"])
    assert unresolved == {
        "numeric_current_price",
        "forecast_upper_bound",
        "forecast_lower_bound",
        "generic_risk_level",
        "commodity_tactical_state",
    }
    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": payload["authorization_id"],
        "authorization_decision": payload["authorization_decision"],
        "authorized_file_count": len(payload["authorized_files"]),
        "existing_evidence_only": True,
        "unsupported_fields_preserved": True,
        "analytical_database_write_authorized": payload["boundaries"]["analytical_database_write_authorized"],
        "hosted_publication_write_authorized": payload["boundaries"]["hosted_publication_write_authorized"],
        "next_decision": payload["next_decision"],
    }, indent=2))


if __name__ == "__main__":
    main()
