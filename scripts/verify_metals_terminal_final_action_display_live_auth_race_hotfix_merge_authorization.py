import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config/metals/terminal_final_action_display_live_auth_race_hotfix_merge_authorization.json"
DB = Path(r"C:\Users\DevonLockard\InvestmentPlatform\data\universal\universal_investment.duckdb")
EXPECTED_DB = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
EXPECTED_FILES = sorted([
    "foundation/production/dashboard_assets/dashboard.js",
    "tests/delivery/test_rec_ui_1.py",
])

a = json.loads(AUTH.read_text(encoding="utf-8"))
scope = a["authorization_scope"]
contract = a["merge_contract"]
state = a["source_pr_state"]
behavior = a["certified_behavior"]

result = {
    "authorization_id_bound": a["authorization_id"] == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-LIVE-AUTH-RACE-HOTFIX-MERGE-AUTHORIZATION-1",
    "source_pr_bound": a["source_pull_request_number"] == 62 and a["source_pull_request_base"] == "main" and a["source_pull_request_head"] == "hotfix/metals-recommendations-auth-race" and a["source_pull_request_head_sha"] == "47366660dd7e426c0dbed4ec262fdc8ac5736a39",
    "main_base_bound": a["source_main_base_sha"] == "d43993ca49f9494517374ae08d745706f65aac25",
    "database_sha_bound": a["source_database_sha256"] == EXPECTED_DB,
    "changed_files_exact": sorted(a["required_changed_files"]) == EXPECTED_FILES,
    "pr_state_bound": state == {"open": True, "commit_count": 1, "changed_file_count": 2, "universal_investment_platform_ci_success": True, "container_delivery_success": True},
    "certified_behavior_all_true": len(behavior) == 7 and all(v is True for v in behavior.values()),
    "merge_authorized": scope["pull_request_merge_authorized"] is True and scope["main_merge_authorized"] is True,
    "manual_render_closed": scope["manual_render_deployment_authorized"] is False,
    "branch_mutation_closed": scope["hotfix_branch_mutation_authorized"] is False and scope["additional_code_change_authorized"] is False,
    "writes_closed": all(scope[k] is False for k in ["hosted_database_write_authorized", "analytical_database_write_authorized", "read_api_change_authorized", "recommendation_recompute_authorized", "forecast_refresh_authorized", "model_refresh_authorized", "allocation_or_execution_authorized"]),
    "merge_contract_bound": contract["pull_request_number"] == 62 and contract["required_expected_head_sha"] == "47366660dd7e426c0dbed4ec262fdc8ac5736a39" and contract["required_base_branch"] == "main" and contract["required_head_branch"] == "hotfix/metals-recommendations-auth-race" and contract["required_changed_file_count"] == 2 and contract["required_commit_count"] == 1 and all(contract[k] is True for k in ["merge_only_if_pr_still_open", "merge_only_if_mergeable", "merge_only_if_ci_green", "merge_only_if_container_delivery_green", "merge_only_if_main_base_unchanged", "merge_only_if_head_unchanged"]),
    "decision_bound": a["authorization_decision"] == "AUTHORIZE_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX_MAIN_MERGE",
    "next_decision_bound": a["next_decision"] == "MERGE_AND_CERTIFY_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX_PR_62",
}

if DB.exists():
    result["database_file_sha_matches"] = hashlib.sha256(DB.read_bytes()).hexdigest() == EXPECTED_DB
else:
    result["database_file_sha_matches"] = False

result["status"] = "PASS" if all(result.values()) else "FAIL"
print(json.dumps(result, indent=2, sort_keys=True))
