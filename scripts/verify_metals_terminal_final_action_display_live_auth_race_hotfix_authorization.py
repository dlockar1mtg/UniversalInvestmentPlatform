import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config/metals/terminal_final_action_display_live_auth_race_hotfix_authorization.json"
DB = Path(r"C:\Users\DevonLockard\InvestmentPlatform\data\universal\universal_investment.duckdb")
EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"

obj = json.loads(AUTH.read_text(encoding="utf-8"))
checks = {
    "authorization_id_bound": obj.get("authorization_id") == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-LIVE-AUTH-RACE-HOTFIX-AUTHORIZATION-1",
    "source_main_bound": obj.get("source_main_head") == "d43993ca49f9494517374ae08d745706f65aac25",
    "failure_bound": obj.get("live_failure", {}).get("message") == "Cannot set properties of null (setting 'innerHTML')",
    "diagnosis_bound": all(obj.get("diagnosis", {}).get(k) is True for k in [
        "recommendation_ui_replaces_recommendations_inner_html",
        "dashboard_render_domain_cards_unconditionally_writes_removed_summary_node",
        "stale_recommendations_hash_and_existing_session_key_can_trigger_concurrent_loads",
        "failure_can_clear_valid_session_key_and_return_user_to_auth",
    ]) and obj.get("diagnosis", {}).get("metals_final_action_data_or_policy_defect") is False,
    "authorized_files_exact": sorted(obj.get("authorized_files", [])) == sorted([
        "foundation/production/dashboard_assets/dashboard.js",
        "tests/delivery/test_rec_ui_1.py",
    ]),
    "required_behavior_all_true": all(v is True for v in obj.get("required_hotfix_behavior", {}).values()),
    "merge_closed": obj.get("authorization_scope", {}).get("main_merge_authorized") is False,
    "manual_render_closed": obj.get("authorization_scope", {}).get("manual_render_deployment_authorized") is False,
    "writes_closed": all(obj.get("authorization_scope", {}).get(k) is False for k in [
        "hosted_database_write_authorized",
        "analytical_database_write_authorized",
        "read_api_change_authorized",
        "recommendation_recompute_authorized",
        "forecast_refresh_authorized",
        "model_refresh_authorized",
        "allocation_or_execution_authorized",
    ]),
    "decision_bound": obj.get("authorization_decision") == "AUTHORIZE_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX_IMPLEMENTATION",
    "next_decision_bound": obj.get("next_decision") == "IMPLEMENT_AND_CERTIFY_BOUNDED_LIVE_RECOMMENDATIONS_AUTH_RACE_HOTFIX",
}
if DB.exists():
    checks["database_file_sha_matches"] = hashlib.sha256(DB.read_bytes()).hexdigest() == EXPECTED_DB_SHA
else:
    checks["database_file_sha_matches"] = False
checks["status"] = "PASS" if all(checks.values()) else "FAIL"
print(json.dumps(checks, indent=2, sort_keys=True))
raise SystemExit(0 if checks["status"] == "PASS" else 1)
