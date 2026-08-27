from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / "config/metals/terminal_final_action_display_deployment_package_review.json"
    document = json.loads(path.read_text(encoding="utf-8"))

    result = {
        "status": "PASS",
        "review_id_bound": document.get("review_id") == "METALS-TERMINAL-FINAL-ACTION-DISPLAY-DEPLOYMENT-PACKAGE-REVIEW-1",
        "source_implementation_bound": document.get("source_implementation_head") == "3c85d3d74d45b4b027bfff6d22d57fb326594d38",
        "main_base_bound": document.get("main_base_head") == "32668f5bcb73fc6b6f00c5b562e5f5433e6bf9cd",
        "divergence_bound": document.get("research_to_main_compare") == {
            "status": "diverged",
            "research_ahead_by": 442,
            "research_behind_by": 2,
            "whole_research_branch_merge_safe": False,
            "direct_research_branch_pr_safe": False,
        },
        "strategy_bound": document.get("deployment_strategy") == "RECONSTRUCT_EXACT_DISPLAY_SEMANTIC_FIX_ON_FRESH_BRANCH_FROM_CURRENT_MAIN",
        "deployment_files_exact": set(document.get("deployment_package_files", [])) == {
            "foundation/production/dashboard_assets/recommendation_ui.js",
            "tests/delivery/test_rec_ui_1.py",
        },
        "whole_branch_merge_closed": document.get("package_constraints", {}).get("whole_research_branch_merge_authorized") is False,
        "direct_pr_closed": document.get("package_constraints", {}).get("direct_research_branch_pr_authorized") is False,
        "cherry_pick_closed": document.get("package_constraints", {}).get("cherry_pick_entire_implementation_commit_authorized") is False,
        "fresh_main_branch_required": document.get("package_constraints", {}).get("fresh_main_based_deployment_branch_required") is True,
        "local_certification_required": document.get("package_constraints", {}).get("local_regression_certification_required_before_pr") is True,
        "pr_closed": document.get("package_constraints", {}).get("pull_request_authorized") is False,
        "main_merge_closed": document.get("package_constraints", {}).get("main_merge_authorized") is False,
        "render_deploy_closed": document.get("package_constraints", {}).get("render_deployment_authorized") is False,
        "decision_bound": document.get("review_decision") == "BOUNDED_MAIN_BASED_DEPLOYMENT_PACKAGE_REQUIRED_BEFORE_PR_AUTHORIZATION",
        "next_decision_bound": document.get("next_decision") == "CONSTRUCT_AND_CERTIFY_BOUNDED_METALS_TERMINAL_FINAL_ACTION_DISPLAY_DEPLOYMENT_PACKAGE",
    }

    for key, value in result.items():
        if key != "status" and value is not True:
            result["status"] = "FAIL"

    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
