from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config/metals/tactical_policy_v3_live_presentation_activation_authorization.json"

EXPECTED_DB = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_STATE = "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
EXPECTED_MANIFEST = "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"
EXPECTED_FINGERPRINT = "21a3e3c8a1e73b7370d23f0704081f7ac01f28609bed22f94d00d4f4c2e7c126"


def main() -> None:
    payload = json.loads(AUTH.read_text(encoding="utf-8"))
    assert payload["authorization_id"] == "METALS-TACTICAL-POLICY-V3-LIVE-PRESENTATION-ACTIVATION-AUTHORIZATION-1"
    assert payload["source_implementation_id"] == "METALS-TACTICAL-POLICY-V3-PRESENTATION-PUBLICATION-AND-UI-IMPLEMENTATION-1"
    assert payload["source_implementation_head"] == "b52210de66169ebacb0afccf363f27e320c5624e"
    assert payload["source_database_sha256"] == EXPECTED_DB
    assert payload["source_state_sha256"] == EXPECTED_STATE
    assert payload["source_manifest_sha256"] == EXPECTED_MANIFEST
    assert payload["authorization_decision"] == "AUTHORIZE_ONE_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION"
    assert payload["execution_limit"] == 1
    assert payload["execution_is_one_time"] is True
    certified = payload["certified_non_active_publication"]
    assert certified["publication_status"] == "STAGED"
    assert certified["content_fingerprint"] == EXPECTED_FINGERPRINT
    assert certified["total_record_count"] == 4181
    assert certified["metals_tactical_state_count"] == 10
    assert certified["metals_recommendation_count"] == 12
    assert certified["metals_forecast_count"] == 16
    assert certified["metals_risk_count"] == 11
    implementation = payload["authorized_live_activation"]
    for value in implementation.values():
        if isinstance(value, bool):
            assert value is True
    for value in payload["required_execution_controls"].values():
        assert value is True
    for value in payload["semantic_guardrails"].values():
        assert value is True
    boundary = payload["authorization_boundary"]
    assert boundary["live_presentation_activation_authorized"] is True
    assert boundary["live_presentation_activation_executed"] is False
    for key, value in boundary.items():
        if key not in {"live_presentation_activation_authorized", "live_presentation_activation_executed"}:
            assert value is False
    assert payload["next_decision"] == "IMPLEMENT_AND_EXECUTE_ONE_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION"
    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": payload["authorization_id"],
        "authorization_decision": payload["authorization_decision"],
        "source_database_sha256": payload["source_database_sha256"],
        "certified_content_fingerprint": certified["content_fingerprint"],
        "certified_total_record_count": certified["total_record_count"],
        "certified_metals_tactical_state_count": certified["metals_tactical_state_count"],
        "execution_limit": payload["execution_limit"],
        "live_presentation_activation_authorized": boundary["live_presentation_activation_authorized"],
        "live_presentation_activation_executed": boundary["live_presentation_activation_executed"],
        "analytical_database_write_authorized": boundary["analytical_database_write_authorized"],
        "next_decision": payload["next_decision"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
