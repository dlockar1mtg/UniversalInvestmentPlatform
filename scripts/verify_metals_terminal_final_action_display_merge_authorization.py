from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config" / "metals" / "terminal_final_action_display_merge_authorization.json"
DB = Path(r"C:\Users\DevonLockard\InvestmentPlatform\data\universal\universal_investment.duckdb")

EXPECTED_ID = "METALS-TERMINAL-FINAL-ACTION-DISPLAY-MERGE-AUTHORIZATION-1"
EXPECTED_HEAD = "29a428de098977661421d9350436f1ffa6596d62"
EXPECTED_MAIN = "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd"
EXPECTED_DB = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_FILES = sorted([
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "tests/delivery/test_rec_ui_1.py",
])

auth = json.loads(AUTH.read_text(encoding="utf-8"))
results = {
    "authorization_id_bound": auth.get("authorization_id") == EXPECTED_ID,
    "source_pr_bound": auth.get("source_pull_request_number") == 61 and auth.get("source_pull_request_head_sha") == EXPECTED_HEAD,
    "main_base_bound": auth.get("source_main_base_sha") == EXPECTED_MAIN,
    "database_sha_bound": auth.get("source_database_sha256") == EXPECTED_DB,
    "changed_files_exact": sorted(auth.get("required_changed_files", [])) == EXPECTED_FILES,
    "pr_state_bound": auth.get("source_pr_state") == {
        "open": True,
        "mergeable": True,
        "commit_count": 3,
        "changed_file_count": 2,
        "universal_investment_platform_ci_success": True,
        "container_delivery_success": True,
    },
    "merge_authorized": auth.get("authorization_scope", {}).get("main_merge_authorized") is True and auth.get("authorization_scope", {}).get("pull_request_merge_authorized") is True,
    "manual_render_closed": auth.get("authorization_scope", {}).get("manual_render_deployment_authorized") is False,
    "branch_mutation_closed": auth.get("authorization_scope", {}).get("deployment_branch_mutation_authorized") is False,
    "writes_closed": all(auth.get("authorization_scope", {}).get(key) is False for key in [
        "hosted_database_write_authorized",
        "analytical_database_write_authorized",
        "read_api_change_authorized",
        "recommendation_recompute_authorized",
        "forecast_refresh_authorized",
        "model_refresh_authorized",
        "allocation_or_execution_authorized",
    ]),
    "merge_contract_bound": auth.get("merge_contract", {}).get("required_expected_head_sha") == EXPECTED_HEAD and auth.get("merge_contract", {}).get("required_base_branch") == "main" and auth.get("merge_contract", {}).get("required_head_branch") == "deploy/metals-final-action-display-fix" and auth.get("merge_contract", {}).get("required_changed_file_count") == 2 and auth.get("merge_contract", {}).get("required_commit_count") == 3,
    "decision_bound": auth.get("authorization_decision") == "AUTHORIZE_BOUNDED_METALS_FINAL_ACTION_DISPLAY_MAIN_MERGE",
    "next_decision_bound": auth.get("next_decision") == "MERGE_AND_CERTIFY_BOUNDED_METALS_FINAL_ACTION_DISPLAY_PR_61",
}

if DB.exists():
    results["database_file_sha_matches"] = hashlib.sha256(DB.read_bytes()).hexdigest() == EXPECTED_DB
else:
    results["database_file_sha_matches"] = False

results["status"] = "PASS" if all(results.values()) else "FAIL"
print(json.dumps(results, indent=2, sort_keys=True))
raise SystemExit(0 if results["status"] == "PASS" else 1)
