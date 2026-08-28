from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "composite_presentation_activation_authorization.json"

EXPECTED = {
    "authorization_id": "METALS-COMPOSITE-PRESENTATION-ACTIVATION-AUTHORIZATION-1",
    "source_governed_head": "5b55da63934a930bef0913d664c9507f5195fa2b",
    "source_database_sha256": "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
    "previous_active_publication_id": "mtg-premium-stage-rehearsal-ac8adb415f03",
    "candidate_id": "metals-mtg-composite-recovery-r1-20260828",
    "fingerprint": "67352221b51e7479fe9e154e12dd718a9cf392c794d2320461203fe980bfc009",
}


def verify() -> dict[str, object]:
    doc = json.loads(PATH.read_text(encoding="utf-8"))
    candidate = doc["candidate"]
    contract = doc["activation_contract"]
    scope = doc["authorization_scope"]

    checks = {
        "authorization_id_bound": doc["authorization_id"] == EXPECTED["authorization_id"],
        "source_head_bound": doc["source_governed_head"] == EXPECTED["source_governed_head"],
        "source_database_bound": doc["source_database_sha256"] == EXPECTED["source_database_sha256"],
        "previous_active_bound": doc["previous_active_publication_id"] == EXPECTED["previous_active_publication_id"],
        "candidate_identity_bound": (
            candidate["publication_id"] == EXPECTED["candidate_id"]
            and candidate["publication_status"] == "STAGED"
            and int(candidate["record_count"]) == 13264
            and candidate["content_fingerprint"] == EXPECTED["fingerprint"]
        ),
        "candidate_certification_bound": (
            int(candidate["metals_final_action_match_count"]) == 12
            and int(candidate["mtg_premium_record_count"]) == 787
            and candidate["hosted_content_matches_local_candidate"] is True
        ),
        "activation_contract_bound": all(contract.values()),
        "activation_authorized": (
            scope["hosted_publication_activation_authorized"] is True
            and scope["active_pointer_mutation_authorized"] is True
        ),
        "other_writes_closed": all(
            scope[key] is False
            for key in (
                "hosted_publication_stage_authorized",
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
        "decision_bound": doc["authorization_decision"] == "AUTHORIZE_BOUNDED_COMPOSITE_PRESENTATION_ACTIVATION",
        "next_decision_bound": doc["next_decision"] == "ACTIVATE_AND_CERTIFY_BOUNDED_COMPOSITE_PRESENTATION_RECOVERY",
    }
    checks["status"] = "PASS" if all(checks.values()) else "FAIL"
    return checks


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2, sort_keys=True))
