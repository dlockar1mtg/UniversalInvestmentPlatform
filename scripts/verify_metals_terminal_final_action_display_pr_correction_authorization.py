from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "terminal_final_action_display_pr_correction_authorization.json"


def main() -> int:
    doc = json.loads(PATH.read_text(encoding="utf-8"))

    required_files = {
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

    checks = {
        "authorization_id_bound": doc.get("authorization_id") == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-PR-CORRECTION-AUTHORIZATION-1",
        "source_pr_bound": doc.get("source_pull_request_number") == 61 and doc.get("source_pull_request_head_sha") == "23a0719c8bf6bc26ca7cc8c24b48c3ef581b8c18",
        "main_base_bound": doc.get("source_main_base_sha") == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd",
        "database_sha_bound": doc.get("source_database_sha256") == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "review_requires_correction": doc["review_finding"].get("merge_blocked_until_corrected") is True,
        "authorized_files_exact": set(doc.get("authorized_files", [])) == required_files,
        "required_behavior_all_true": all(doc["required_correction_behavior"].values()),
        "open_scope_exact": open_scope == expected_open,
        "merge_closed": doc["authorization_scope"].get("main_merge_authorized") is False,
        "render_closed": doc["authorization_scope"].get("render_deployment_authorized") is False,
        "required_proof_all_true": all(doc["required_post_correction_proof"].values()),
        "decision_bound": doc.get("authorization_decision") == "AUTHORIZE_BOUNDED_METALS_FINAL_ACTION_DISPLAY_PR_LABEL_CORRECTION",
        "next_decision_bound": doc.get("next_decision") == "IMPLEMENT_AND_CERTIFY_BOUNDED_METALS_FINAL_ACTION_DISPLAY_PR_LABEL_CORRECTION",
    }

    status = "PASS" if all(checks.values()) else "FAIL"
    print(json.dumps({"status": status, **checks}, indent=2, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
