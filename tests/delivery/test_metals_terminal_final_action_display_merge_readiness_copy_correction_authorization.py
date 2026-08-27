from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "terminal_final_action_display_merge_readiness_copy_correction_authorization.json"


def load_doc():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_merge_readiness_copy_correction_authorization_is_exact():
    doc = load_doc()
    assert doc["authorization_id"] == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-MERGE-READINESS-COPY-CORRECTION-AUTHORIZATION-1"
    assert doc["source_pull_request_number"] == 61
    assert doc["source_pull_request_head_sha"] == "00943fc7c67afe002ad4de0eda859162467aa46b"
    assert doc["source_main_base_sha"] == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd"
    assert doc["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert doc["review_finding"]["merge_blocked_until_corrected"] is True
    assert set(doc["authorized_files"]) == {
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "tests/delivery/test_rec_ui_1.py",
    }
    assert all(doc["required_correction_behavior"].values())
    open_scope = {
        key
        for key, value in doc["authorization_scope"].items()
        if value is True
    }
    assert open_scope == {
        "deployment_branch_ui_copy_correction_authorized",
        "deployment_branch_test_correction_authorized",
        "local_test_execution_authorized",
        "pull_request_update_by_existing_head_commit_authorized",
    }
    assert doc["authorization_scope"]["main_merge_authorized"] is False
    assert doc["authorization_scope"]["render_deployment_authorized"] is False
    assert doc["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_FINAL_ACTION_DISPLAY_MERGE_READINESS_COPY_CORRECTION"
    assert doc["next_decision"] == "IMPLEMENT_AND_CERTIFY_BOUNDED_METALS_FINAL_ACTION_DISPLAY_MERGE_READINESS_COPY_CORRECTION"
