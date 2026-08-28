from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "composite_presentation_recovery_authorization.json"

data = json.loads(PATH.read_text(encoding="utf-8"))

checks = {
    "authorization_id_bound": data.get("authorization_id") == "METALS-COMPOSITE-PRESENTATION-RECOVERY-AUTHORIZATION-1",
    "source_publications_bound": (
        data.get("active_publication_id") == "mtg-premium-stage-rehearsal-ac8adb415f03"
        and data.get("certified_metals_publication_id") == "metals-final-decision-presentation-r1-20260827"
    ),
    "database_sha_bound": data.get("source_database_sha256") == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
    "provenance_bound": (
        data["provenance_finding"]["active_final_action_match_count"] == 0
        and data["provenance_finding"]["certified_final_action_match_count"] == 12
    ),
    "differential_bound": data["differential_contract"] == {
        "changed_preexisting_record_count": 12,
        "changed_metals_recommendation_count": 12,
        "other_changed_preexisting_record_count": 0,
        "active_only_record_count": 787,
        "active_only_is_exactly_787_mtg_premium_records": True,
        "certified_only_record_count": 0,
        "safe_composite_recovery_shape": True,
    },
    "candidate_contract_bound": (
        data["recovery_contract"]["candidate_record_count"] == 13264
        and data["recovery_contract"]["expected_metals_final_action_match_count_after_recovery"] == 12
        and all(v is True for k, v in data["recovery_contract"].items() if k not in {"candidate_record_count", "expected_metals_final_action_match_count_after_recovery"})
    ),
    "local_materialization_authorized": (
        data["authorization_scope"]["read_hosted_presentation_records_authorized"] is True
        and data["authorization_scope"]["materialize_local_composite_candidate_authorized"] is True
        and data["authorization_scope"]["local_candidate_validation_authorized"] is True
    ),
    "hosted_writes_closed": (
        data["authorization_scope"]["hosted_publication_stage_authorized"] is False
        and data["authorization_scope"]["hosted_publication_activation_authorized"] is False
        and data["authorization_scope"]["active_pointer_mutation_authorized"] is False
    ),
    "other_writes_closed": all(
        data["authorization_scope"][key] is False
        for key in (
            "repository_code_change_authorized",
            "analytical_database_write_authorized",
            "model_refresh_authorized",
            "forecast_refresh_authorized",
            "recommendation_recompute_authorized",
            "mtg_premium_recompute_authorized",
            "manual_render_deployment_authorized",
            "allocation_or_execution_authorized",
        )
    ),
    "decision_bound": data.get("authorization_decision") == "AUTHORIZE_BOUNDED_COMPOSITE_PRESENTATION_RECOVERY_CANDIDATE_MATERIALIZATION",
    "next_decision_bound": data.get("next_decision") == "MATERIALIZE_AND_CERTIFY_BOUNDED_COMPOSITE_PRESENTATION_RECOVERY_CANDIDATE",
}

result = {**checks, "status": "PASS" if all(checks.values()) else "FAIL"}
print(json.dumps(result, indent=2, sort_keys=True))
raise SystemExit(0 if result["status"] == "PASS" else 1)
