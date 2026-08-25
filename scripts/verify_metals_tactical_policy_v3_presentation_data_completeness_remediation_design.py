from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "config/metals/tactical_policy_v3_presentation_data_completeness_remediation_design.json"


def main() -> None:
    payload = json.loads(PATH.read_text(encoding="utf-8"))
    assert payload["design_id"] == "METALS-TACTICAL-POLICY-V3-PRESENTATION-DATA-COMPLETENESS-REMEDIATION-DESIGN-1"
    assert payload["source_audit_head"] == "dd6f5df48b5324b0bbfc3e7db7bb35b7642df11c"
    assert payload["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert payload["audit_conclusions"]["tactical_non_reference_opportunities"] == 10
    assert payload["audit_conclusions"]["tactical_metrics_complete_for_all_tactical_rows"] is True
    rejected = payload["explicitly_rejected_false_mappings"]
    assert all(value is False for value in rejected.values())
    strategy = payload["presentation_strategy"]
    assert strategy["bil_remains_reference_control_only"] is True
    assert strategy["missing_fields_remain_explicitly_unavailable"] is True
    assert strategy["ui_must_distinguish_not_applicable_from_missing"] is True
    assert strategy["no_cross_domain_rank"] is True
    assert strategy["no_execution_authority"] is True
    assert all(value is False for value in payload["boundaries"].values())
    assert payload["next_decision"] == "AUTHORIZE_METALS_PRESENTATION_DATA_COMPLETENESS_REMEDIATION_IMPLEMENTATION"
    print(json.dumps({
        "status": "PASS",
        "read_only": True,
        "design_id": payload["design_id"],
        "tactical_non_reference_opportunities": 10,
        "false_semantic_mappings_rejected": True,
        "unresolved_fields_preserved": True,
        "implementation_authorized": False,
        "next_decision": payload["next_decision"],
    }, indent=2))


if __name__ == "__main__":
    main()
