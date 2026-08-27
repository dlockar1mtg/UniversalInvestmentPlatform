from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config" / "metals" / "terminal_final_action_display_fix_authorization.json"


def main() -> int:
    document = json.loads(PATH.read_text(encoding="utf-8"))

    expected_open = {
        "recommendation_ui_js_change_authorized",
        "rec_ui_test_change_authorized",
        "new_targeted_display_test_authorized",
        "local_test_execution_authorized",
    }

    open_scope = {
        key
        for key, value in document["authorization_scope"].items()
        if value is True
    }

    expected_files = {
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "tests/delivery/test_rec_ui_1.py",
        "tests/delivery/test_metals_terminal_final_action_display_fix.py",
    }

    required_behavior = document["required_fix_behavior"]
    required_proof = document["required_post_fix_proof"]

    result = {
        "authorization_id_bound": document.get("authorization_id") == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-FIX-AUTHORIZATION-1",
        "source_head_bound": document.get("source_governed_head") == "a7564d58b83e75edadaf1be004594b856168b816",
        "activation_bound": document.get("source_activation_execution_id") == "METALS-FINAL-DECISION-PRESENTATION-ACTIVATION-1",
        "active_publication_bound": document.get("source_active_publication_id") == "metals-final-decision-presentation-r1-20260827" and document.get("source_active_publication_fingerprint") == "9de5edb450542be85dd68f3b0dd539dc520ef1f92b9de1b743672d7a6b1e289d" and document.get("source_active_publication_record_count") == 12477,
        "database_sha_bound": document.get("source_database_sha256") == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f",
        "final_action_counts_bound": document.get("certified_live_final_action_counts") == {"HOLD": 5, "WATCH": 6, "REFERENCE_CONTROL": 1},
        "mismatch_count_bound": document.get("certified_terminal_semantic_mismatch_count") == 9 and document.get("certified_terminal_semantic_match_count") == 3,
        "authorized_files_exact": set(document.get("authorized_files", [])) == expected_files,
        "open_scope_exact": open_scope == expected_open,
        "all_required_behavior_true": len(required_behavior) == 15 and all(value is True for value in required_behavior.values()),
        "all_required_post_fix_proof_true": len(required_proof) == 10 and all(value is True for value in required_proof.values()),
        "hosted_write_closed": document["authorization_scope"].get("hosted_database_write_authorized") is False and document["authorization_scope"].get("active_publication_mutation_authorized") is False,
        "analytical_change_closed": document["authorization_scope"].get("analytical_database_write_authorized") is False and document["authorization_scope"].get("recommendation_recompute_authorized") is False and document["authorization_scope"].get("forecast_refresh_authorized") is False and document["authorization_scope"].get("model_refresh_authorized") is False,
        "read_api_change_closed": document["authorization_scope"].get("read_api_change_authorized") is False,
        "deployment_closed": document["authorization_scope"].get("pr_authorized") is False and document["authorization_scope"].get("main_deploy_authorized") is False,
        "decision_bound": document.get("authorization_decision") == "AUTHORIZE_BOUNDED_METALS_TERMINAL_FINAL_ACTION_DISPLAY_FIX",
        "next_decision_bound": document.get("next_decision") == "IMPLEMENT_AND_CERTIFY_BOUNDED_METALS_TERMINAL_FINAL_ACTION_DISPLAY_FIX",
    }

    result["status"] = "PASS" if all(result.values()) else "FAIL"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
