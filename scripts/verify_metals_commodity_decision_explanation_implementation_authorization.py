from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "config" / "metals" / "commodity_decision_explanation_implementation_authorization.json"
DESIGN_PATH = ROOT / "config" / "metals" / "commodity_decision_explanation_design.json"

EXPECTED_FILES = [
    "foundation/presentation/metals_tactical_projection.py",
    "config/presentation/dash_read_1_metals_tactical_extension.json",
    "foundation/production/dashboard_assets/metals_tactical_ui.js",
]


def main() -> None:
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))

    boundary = auth["authorization_boundary"]
    required = auth["required_implementation_behavior"]
    guards = auth["semantic_guardrails"]

    result = {
        "status": "PASS",
        "read_only": True,
        "authorization_id": auth["authorization_id"],
        "source_design_bound": auth["source_design_id"] == design["design_id"],
        "source_head_bound": auth["source_design_head"] == "327e72e4eb9ac7abff9d636bdaf3489b428abef3",
        "database_sha_bound": auth["source_database_sha256"] == design["source_database_sha256"],
        "record_type_bound": auth["authorized_record_type"] == design["new_record_type"],
        "runtime_file_scope_exact": sorted(auth["authorized_runtime_files"]) == sorted(EXPECTED_FILES),
        "gold_implementation_authorized": bool(boundary["runtime_implementation_authorized"]),
        "required_behavior_all_true": all(value is True for value in required.values()),
        "semantic_guardrails_all_true": all(value is True for value in guards.values()),
        "uranium_derivation_blocked": required["uranium_derived_rationale_remains_unavailable"] and required["uranium_forecast_regime_risk_context_remains_unavailable"] and required["ura_urnm_evidence_not_inherited_by_uranium"],
        "native_fields_not_mutated": guards["do_not_populate_recommendations_current_rationale"] and guards["do_not_populate_recommendations_current_risk_summary"] and guards["do_not_populate_risk_metrics_current"],
        "hosted_write_not_authorized": boundary["hosted_publication_write_authorized"] is False,
        "database_write_not_authorized": boundary["analytical_database_write_authorized"] is False,
        "main_deploy_not_authorized": boundary["main_deployment_authorized"] is False,
        "pr_not_authorized": boundary["pr_creation_authorized"] is False,
        "downstream_boundaries_closed": all(
            value is False
            for key, value in boundary.items()
            if key != "runtime_implementation_authorized"
        ),
        "next_decision": auth["next_decision"],
    }

    if not all(
        value is True
        for key, value in result.items()
        if key not in {"status", "read_only", "authorization_id", "next_decision"}
    ):
        result["status"] = "FAIL"

    print(json.dumps(result, indent=2, sort_keys=True))

    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
