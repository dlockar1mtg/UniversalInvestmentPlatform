from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config" / "metals" / "tactical_policy_v3_production_persistence_authorization.json"
DESIGN = ROOT / "config" / "metals" / "tactical_policy_v3_production_persistence_authorization_design.json"
REVIEW = ROOT / "config" / "metals" / "tactical_policy_v3_current_state_materialization_review.json"

EXPECTED_STATE_SHA = "00ea9954ead2eaa66085a38468972315b0414f0ad1039f833518d70d40882c3a"
EXPECTED_MANIFEST_SHA = "f8bbeedfbfe16bea01bdf7bd6c53d5d5b9db22e197bec533c84daa9ae8bb5a75"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def main() -> int:
    auth = json.loads(AUTH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))

    require(auth["authorization_id"] == "METALS-TACTICAL-POLICY-V3-PRODUCTION-PERSISTENCE-AUTHORIZATION-1", "unexpected authorization id")
    require(auth["source_design_id"] == design["design_id"], "source design mismatch")
    require(auth["source_review_id"] == review["review_id"], "source review mismatch")
    require(auth["source_state_sha256"] == EXPECTED_STATE_SHA, "state sha mismatch")
    require(auth["source_manifest_sha256"] == EXPECTED_MANIFEST_SHA, "manifest sha mismatch")
    require(auth["source_as_of_date"] == "2026-08-21", "as-of date mismatch")
    require(auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_V3_PRODUCTION_PERSISTENCE_IMPLEMENTATION", "unexpected authorization decision")

    storage = auth["authorized_storage"]
    require(storage["database_path"] == "data/universal/universal_investment.duckdb", "database path mismatch")
    require(storage["history_table"] == "metals_tactical_state_history", "history table mismatch")
    require(storage["current_view"] == "metals_tactical_state_current", "current view mismatch")
    require(storage["history_is_append_only"] is True, "history must be append-only")
    require(storage["current_state_is_view_derived"] is True, "current state must be view-derived")
    require(storage["schema_migration_authorized"] is True, "schema migration must be authorized")
    require(storage["persistence_implementation_authorized"] is True, "persistence implementation must be authorized")
    require(storage["production_database_write_authorized"] is False, "database write must remain unauthorized")

    scope = auth["authorized_source_scope"]
    require(scope["exact_state_sha256"] == EXPECTED_STATE_SHA, "authorized source state sha mismatch")
    require(scope["exact_manifest_sha256"] == EXPECTED_MANIFEST_SHA, "authorized source manifest sha mismatch")
    require(scope["exact_as_of_date"] == "2026-08-21", "authorized as-of mismatch")
    require(scope["exact_row_count"] == 11, "row count mismatch")
    require(scope["exact_opportunity_row_count"] == 10, "opportunity row count mismatch")
    require(scope["exact_reference_control_row_count"] == 1, "reference row count mismatch")
    require(scope["price_semantics"] == "UNADJUSTED_CLOSE", "price semantics mismatch")
    require(scope["classifier_rule_version"] == "METALS-V3-REGIME-CANDIDATE-RULES-1", "classifier mismatch")
    require(scope["action_mapping_version"] == "METALS-V3-ACTION-MAPPING-1", "mapping mismatch")

    for key, value in auth["required_transaction_controls"].items():
        require(value is True, f"transaction control not true: {key}")

    boundary = auth["downstream_authorization_boundary"]
    for key, value in boundary.items():
        require(value is False, f"downstream authority prematurely enabled: {key}")

    for key, value in auth["semantic_guardrails"].items():
        require(value is True, f"semantic guardrail not true: {key}")

    require(auth["next_decision"] == "IMPLEMENT_METALS_TACTICAL_POLICY_V3_PRODUCTION_PERSISTENCE", "unexpected next decision")

    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "authorization_id": auth["authorization_id"],
        "authorization_decision": auth["authorization_decision"],
        "schema_migration_authorized": storage["schema_migration_authorized"],
        "persistence_implementation_authorized": storage["persistence_implementation_authorized"],
        "production_database_write_authorized": storage["production_database_write_authorized"],
        "history_table": storage["history_table"],
        "current_view": storage["current_view"],
        "source_state_sha256": auth["source_state_sha256"],
        "source_manifest_sha256": auth["source_manifest_sha256"],
        "presentation_activation_authorized": boundary["presentation_activation_authorized"],
        "next_decision": auth["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
