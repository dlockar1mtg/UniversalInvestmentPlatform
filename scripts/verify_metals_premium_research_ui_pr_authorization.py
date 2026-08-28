from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config" / "metals" / "premium_research_ui_pr_authorization.json"

EXPECTED_FILES = {
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "tests/delivery/test_rec_ui_1.py",
}


def main() -> None:
    data = json.loads(AUTH.read_text(encoding="utf-8"))
    contract = data["implementation_contract"]
    scope = data["authorization_scope"]

    result = {
        "authorization_id_bound": data.get("authorization_id") == "METALS-PREMIUM-RESEARCH-UI-PR-AUTHORIZATION-1",
        "source_head_bound": data.get("source_governed_head") == "b4c13cf3c2bac22f23bfd0934d22a3e820eaaade",
        "implementation_head_bound": data.get("implementation_head") == "8581dbbc1a9545afa72cf1c622831e7fab052686",
        "main_head_bound": data.get("expected_main_head") == "348f2a94c4bea371bde47dac880dc1d91fe7fa07",
        "database_sha_bound": data.get("source_database_sha256") == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "implementation_shape_bound": int(contract.get("commit_count", -1)) == 1 and set(contract.get("changed_files", [])) == EXPECTED_FILES,
        "semantic_contract_bound": all(bool(contract.get(key)) for key in (
            "premium_metals_overview_cards_bound",
            "premium_metals_detail_bound",
            "final_action_remains_primary",
            "native_recommendation_remains_supporting",
            "tactical_context_remains_supporting",
            "bil_remains_reference_control",
            "missing_forecast_authority_remains_explicit",
            "crypto_contract_preserved",
            "mtg_contract_preserved",
        )) and contract.get("metals_forecast_horizons_months") == [3, 6, 12, 24],
        "pr_authorized": scope.get("pull_request_creation_authorized") is True and scope.get("pull_request_review_authorized") is True,
        "merge_closed": scope.get("merge_authorized") is False,
        "other_writes_closed": all(scope.get(key) is False for key in (
            "repository_additional_code_change_authorized",
            "hosted_presentation_mutation_authorized",
            "analytical_database_write_authorized",
            "model_refresh_authorized",
            "forecast_refresh_authorized",
            "recommendation_recompute_authorized",
            "manual_render_deployment_authorized",
        )),
        "decision_bound": data.get("authorization_decision") == "AUTHORIZE_METALS_PREMIUM_RESEARCH_UI_PULL_REQUEST",
        "next_decision_bound": data.get("next_decision") == "CREATE_AND_CERTIFY_METALS_PREMIUM_RESEARCH_UI_PULL_REQUEST",
    }
    result["status"] = "PASS" if all(result.values()) else "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
