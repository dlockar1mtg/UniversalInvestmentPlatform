from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "terminal_final_action_display_merge_readiness_copy_correction_authorization.json"

doc = json.loads(PATH.read_text(encoding="utf-8"))

expected_files = {
    "foundation/production/dashboard_assets/recommendation_ui.js",
    "tests/delivery/test_rec_ui_1.py",
}

open_scope = {
    key
    for key, value in doc["authorization_scope"].items()
    if value is True
}

expected_open = {
    "deployment_branch_ui_copy_correction_authorized",
    "deployment_branch_test_correction_authorized",
    "local_test_execution_authorized",
    "pull_request_update_by_existing_head_commit_authorized",
}

result = {
    "status": "PASS",
    "authorization_id_bound": doc["authorization_id"] == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-MERGE-READINESS-COPY-CORRECTION-AUTHORIZATION-1",
    "source_pr_bound": doc["source_pull_request_number"] == 61 and doc["source_pull_request_head_sha"] == "00943fc7c67afe002ad4de0eda859162467aa46b",
    "main_base_bound": doc["source_main_base_sha"] == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd",
    "database_sha_bound": doc["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
    "review_requires_copy_correction": doc["review_finding"]["merge_blocked_until_corrected"] is True,
    "authorized_files_exact": set(doc["authorized_files"]) == expected_files,
    "required_behavior_all_true": all(doc["required_correction_behavior"].values()),
    "open_scope_exact": open_scope == expected_open,
    "merge_closed": doc["authorization_scope"]["main_merge_authorized"] is False,
    "render_closed": doc["authorization_scope"]["render_deployment_authorized"] is False,
    "decision_bound": doc["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_ACTION_DISPLAY_MERGE_READINESS_COPY_CORRECTION",
    "next_decision_bound": doc["next_decision"] == "IMPLEMENT_AND_CERTIFY_BOUNDED_METALS_FINAL_ACTION_DISPLAY_MERGE_READINESS_COPY_CORRECTION",
}

if not all(value is True for key, value in result.items() if key != "status"):
    result["status"] = "FAIL"

print(json.dumps(result, indent=2, sort_keys=True))

if result["status"] != "PASS":
    raise SystemExit(1)
