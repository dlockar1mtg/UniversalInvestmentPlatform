import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "terminal_final_action_display_pr_authorization.json"


def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    expected_files = [
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "tests/delivery/test_rec_ui_1.py",
    ]
    expected_open = {
        "pull_request_creation_authorized",
        "pull_request_review_authorized",
        "pull_request_check_inspection_authorized",
    }
    scope = payload["authorization_scope"]
    result = {
        "authorization_id_bound": payload.get("authorization_id") == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-PR-AUTHORIZATION-1",
        "deployment_head_bound": payload.get("source_deployment_head") == "23a0719c8bf6bc26ca7cc8c24b48c3ef581b8c18",
        "main_base_bound": payload.get("main_base_head") == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd",
        "database_sha_bound": payload.get("source_database_sha256") == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "compare_bound": payload.get("deployment_compare") == {"status": "ahead", "ahead_by": 1, "behind_by": 0, "total_commits": 1},
        "pr_base_head_bound": payload.get("authorized_pr", {}).get("base") == "main" and payload.get("authorized_pr", {}).get("head") == "deploy/metals-final-action-display-fix",
        "changed_files_exact": payload.get("authorized_pr", {}).get("required_changed_files") == expected_files,
        "commit_count_bound": payload.get("authorized_pr", {}).get("required_commit_count") == 1,
        "open_scope_exact": {k for k, v in scope.items() if v is True} == expected_open,
        "merge_closed": scope.get("main_merge_authorized") is False,
        "render_closed": scope.get("render_deployment_authorized") is False,
        "branch_mutation_closed": scope.get("deployment_branch_mutation_authorized") is False,
        "all_required_behavior_true": all(payload.get("required_pr_behavior", {}).values()),
        "decision_bound": payload.get("authorization_decision") == "AUTHORIZE_BOUNDED_METALS_FINAL_ACTION_DISPLAY_PR_CREATION",
        "next_decision_bound": payload.get("next_decision") == "CREATE_AND_CERTIFY_BOUNDED_METALS_FINAL_ACTION_DISPLAY_PR",
    }
    result["status"] = "PASS" if all(result.values()) else "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
