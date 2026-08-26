from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH = ROOT / "config" / "metals" / "tactical_policy_v3_csp_visual_acceptance_recovery_authorization.json"


def main() -> None:
    document = json.loads(AUTH.read_text(encoding="utf-8"))

    expected_files = [
        "foundation/production/dashboard_assets/recommendation_visual.css",
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
    ]

    checks = {
        "authorization_id": document.get("authorization_id")
        == "METALS-TACTICAL-POLICY-V3-CSP-VISUAL-ACCEPTANCE-RECOVERY-AUTHORIZATION-1",
        "visual_acceptance_failed": document.get("source_visual_acceptance_result") == "FAIL",
        "source_head_bound": document.get("source_governed_head")
        == "2cc7fc1a0fd4f1394daf81d1631b010560e0927b",
        "r3_publication_bound": document.get("source_active_publication_id")
        == "metals-v3-decision-utility-r3-20260826",
        "r3_fingerprint_bound": document.get("source_active_publication_fingerprint")
        == "e5f0bce3eb0181983e990e3de5795867dc53bf41c0d038b0d7302e722434b3ee",
        "three_runtime_files_only": document.get("authorized_runtime_files") == expected_files,
        "required_behavior_all_true": all(document.get("required_recovery_behavior", {}).values()),
        "data_invariants_all_true": all(document.get("data_and_semantic_invariants", {}).values()),
        "recovery_authorized": document.get("authorization_boundary", {}).get("csp_visual_recovery_authorized") is True,
        "hosted_write_not_authorized": document.get("authorization_boundary", {}).get("hosted_publication_write_authorized") is False,
        "database_write_not_authorized": document.get("authorization_boundary", {}).get("analytical_database_write_authorized") is False,
        "main_deploy_not_authorized": document.get("authorization_boundary", {}).get("main_deployment_authorized") is False,
        "pr_not_authorized": document.get("authorization_boundary", {}).get("pull_request_authorized") is False,
        "decision": document.get("authorization_decision")
        == "AUTHORIZE_BOUNDED_CSP_COMPATIBLE_METALS_VISUAL_ACCEPTANCE_RECOVERY",
        "next_decision": document.get("next_decision")
        == "IMPLEMENT_AND_CERTIFY_CSP_COMPATIBLE_METALS_VISUAL_ACCEPTANCE_RECOVERY",
    }

    failed = [name for name, passed in checks.items() if not passed]
    result = {
        "status": "PASS" if not failed else "FAIL",
        "read_only": True,
        **checks,
        "failed_checks": failed,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
