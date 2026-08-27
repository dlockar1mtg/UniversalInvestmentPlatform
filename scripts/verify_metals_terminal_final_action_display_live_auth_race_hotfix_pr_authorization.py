import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config/metals/terminal_final_action_display_live_auth_race_hotfix_pr_authorization.json"
DB = Path(r"C:\Users\DevonLockard\InvestmentPlatform\data\universal\universal_investment.duckdb")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    data = json.loads(AUTH.read_text(encoding="utf-8"))
    expected_files = [
        "foundation/production/dashboard_assets/dashboard.js",
        "tests/delivery/test_rec_ui_1.py",
    ]
    scope = data["authorization_scope"]

    result = {
        "authorization_id_bound": data["authorization_id"] == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-LIVE-AUTH-RACE-HOTFIX-PR-AUTHORIZATION-1",
        "source_main_bound": data["source_main_head"] == "d43993ca49f9494517374ae08d745706f65aac25",
        "hotfix_head_bound": data["source_hotfix_head"] == "47366660dd7e426c0dbed4ec262fdc8ac5736a39",
        "hotfix_compare_bound": data["hotfix_state"]["ahead_by"] == 1 and data["hotfix_state"]["behind_by"] == 0 and data["hotfix_state"]["commit_count"] == 1,
        "changed_files_exact": sorted(data["authorized_pr"]["required_changed_files"]) == expected_files,
        "local_certification_bound": data["hotfix_state"]["local_rec_ui_tests_passed"] == 14 and data["hotfix_state"]["git_diff_check_passed"] is True,
        "pr_contract_bound": data["authorized_pr"]["base"] == "main" and data["authorized_pr"]["head"] == "hotfix/metals-recommendations-auth-race" and data["authorized_pr"]["required_expected_head_sha"] == "47366660dd7e426c0dbed4ec262fdc8ac5736a39",
        "certified_behavior_all_true": all(data["certified_behavior"].values()),
        "open_scope_exact": sorted(key for key, value in scope.items() if value) == [
            "pull_request_check_inspection_authorized",
            "pull_request_creation_authorized",
            "pull_request_review_authorized",
        ],
        "merge_closed": scope["main_merge_authorized"] is False,
        "manual_render_closed": scope["manual_render_deployment_authorized"] is False,
        "branch_mutation_closed": scope["hotfix_branch_mutation_authorized"] is False and scope["additional_code_change_authorized"] is False,
        "writes_closed": all(scope[key] is False for key in [
            "hosted_database_write_authorized",
            "analytical_database_write_authorized",
            "read_api_change_authorized",
            "recommendation_recompute_authorized",
            "forecast_refresh_authorized",
            "model_refresh_authorized",
            "allocation_or_execution_authorized",
        ]),
        "decision_bound": data["authorization_decision"] == "AUTHORIZE_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX_PULL_REQUEST_CREATION",
        "next_decision_bound": data["next_decision"] == "CREATE_AND_CERTIFY_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX_PULL_REQUEST",
        "database_file_sha_matches": DB.is_file() and sha256_file(DB) == data["source_database_sha256"],
    }
    result["status"] = "PASS" if all(result.values()) else "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
