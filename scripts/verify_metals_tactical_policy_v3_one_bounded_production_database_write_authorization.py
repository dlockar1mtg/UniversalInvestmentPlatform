from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_one_bounded_production_database_write_authorization.json"

EXPECTED_STATE_SHA = "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
EXPECTED_MANIFEST_SHA = "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"
EXPECTED_PREWRITE_DB_SHA = "dff98e56d27cbc5ef879c18939309c5ab8661fa8fa6dfe74e82537fd53954f7c"


def main() -> int:
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    if auth.get("authorization_id") != "METALS-TACTICAL-POLICY-V3-ONE-BOUNDED-PRODUCTION-DATABASE-WRITE-AUTHORIZATION-1":
        raise RuntimeError("unexpected one-bounded-write authorization ID")
    if auth.get("source_implementation_id") != "METALS-TACTICAL-POLICY-V3-PRODUCTION-PERSISTENCE-IMPLEMENTATION-1":
        raise RuntimeError("unexpected source implementation ID")
    if auth.get("source_implementation_head") != "d64d2b3d3d948d61a3a3525bef3e4bd682720ad6":
        raise RuntimeError("unexpected source implementation HEAD")
    if auth.get("authorization_decision") != "AUTHORIZE_ONE_BOUNDED_METALS_V3_PRODUCTION_DATABASE_WRITE":
        raise RuntimeError("unexpected authorization decision")
    if auth.get("production_database_write_authorized") is not True:
        raise RuntimeError("production database write is not authorized")
    if int(auth.get("execution_limit", -1)) != 1 or auth.get("execution_is_one_time") is not True:
        raise RuntimeError("authorization is not exactly one-time")
    if auth.get("required_prewrite_database_sha256") != EXPECTED_PREWRITE_DB_SHA:
        raise RuntimeError("prewrite database SHA binding changed")
    if auth.get("exact_state_sha256") != EXPECTED_STATE_SHA:
        raise RuntimeError("state SHA binding changed")
    if auth.get("exact_manifest_sha256") != EXPECTED_MANIFEST_SHA:
        raise RuntimeError("manifest SHA binding changed")
    if auth.get("exact_as_of_date") != "2026-08-21":
        raise RuntimeError("as-of date changed")
    if int(auth.get("exact_row_count", -1)) != 11:
        raise RuntimeError("row count changed")
    if int(auth.get("exact_opportunity_row_count", -1)) != 10:
        raise RuntimeError("opportunity row count changed")
    if int(auth.get("exact_reference_control_row_count", -1)) != 1:
        raise RuntimeError("reference-control row count changed")
    if auth.get("history_table") != "metals_tactical_state_history":
        raise RuntimeError("history table changed")
    if auth.get("current_view") != "metals_tactical_state_current":
        raise RuntimeError("current view changed")
    for key, value in auth.get("required_execution_controls", {}).items():
        if value is not True:
            raise RuntimeError(f"required execution control is not TRUE: {key}")
    for key, value in auth.get("semantic_guardrails", {}).items():
        if value is not True:
            raise RuntimeError(f"semantic guardrail is not TRUE: {key}")
    for key, value in auth.get("downstream_authorization_boundary", {}).items():
        if value is not False:
            raise RuntimeError(f"downstream authority prematurely enabled: {key}")
    if auth.get("next_decision") != "EXECUTE_ONE_BOUNDED_METALS_TACTICAL_POLICY_V3_PRODUCTION_DATABASE_WRITE":
        raise RuntimeError("unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": auth["authorization_id"],
        "authorization_decision": auth["authorization_decision"],
        "production_database_write_authorized": True,
        "execution_limit": 1,
        "target_database_path": auth["target_database_path"],
        "required_prewrite_database_sha256": EXPECTED_PREWRITE_DB_SHA,
        "exact_state_sha256": EXPECTED_STATE_SHA,
        "exact_manifest_sha256": EXPECTED_MANIFEST_SHA,
        "history_table": auth["history_table"],
        "current_view": auth["current_view"],
        "presentation_activation_authorized": False,
        "next_decision": auth["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
