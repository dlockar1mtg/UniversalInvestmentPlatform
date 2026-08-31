from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config" / "metals" / "premium_research_ui_v4_push_pr_authorization.json"


def main() -> None:
    data = json.loads(AUTH.read_text(encoding="utf-8"))
    scope = data["authorization_scope"]
    cert = data["certification"]
    result = {
        "status": "PASS",
        "authorization_id_bound": data["authorization_id"] == "METALS-PREMIUM-RESEARCH-UI-V4-PUSH-PR-AUTHORIZATION-1",
        "production_base_bound": data["production_base"] == "348f2a94c4bea371bde47dac880dc1d91fe7fa07",
        "local_head_bound": data["local_reconciliation_head"] == "1d453a38e8ca63e4b76e2d3e391106c5c4eec26e",
        "two_file_boundary_bound": len(data["committed_files"]) == 2 and cert["exact_two_file_boundary"] is True,
        "semantic_contract_bound": all(cert[key] is True for key in (
            "final_action_first_preserved",
            "premium_metals_ui_preserved",
            "crypto_semantics_preserved",
            "mtg_native_semantics_preserved",
            "dom_ownership_safeguard_preserved",
        )),
        "tests_bound": int(cert["rec_ui_tests_passed"]) == 16,
        "push_authorized": scope["deployment_branch_push_authorized"] is True,
        "pr_authorized": scope["pull_request_creation_authorized"] is True,
        "merge_closed": scope["merge_authorized"] is False,
        "other_writes_closed": all(scope[key] is False for key in (
            "additional_code_change_authorized",
            "hosted_presentation_mutation_authorized",
            "analytical_database_write_authorized",
            "model_refresh_authorized",
            "forecast_refresh_authorized",
            "recommendation_recompute_authorized",
            "manual_render_deployment_authorized",
        )),
        "decision_bound": data["authorization_decision"] == "AUTHORIZE_EXPLICIT_TWO_FILE_PRODUCTION_RECONCILIATION_V4_PUSH_AND_PR",
        "next_decision_bound": data["next_decision"] == "PUSH_AND_CREATE_CERTIFIED_METALS_PREMIUM_RESEARCH_UI_PR",
    }
    if not all(value is True for key, value in result.items() if key != "status"):
        result["status"] = "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
