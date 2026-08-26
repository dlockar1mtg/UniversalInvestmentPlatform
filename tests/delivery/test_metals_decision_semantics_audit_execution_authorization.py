from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "decision_semantics_audit_execution_authorization.json"


def load_authorization() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_authorization_identity_and_source_binding() -> None:
    data = load_authorization()
    assert data["authorization_id"] == "METALS-DECISION-SEMANTICS-AUDIT-EXECUTION-AUTHORIZATION-1"
    assert data["source_design_id"] == "METALS-DECISION-SEMANTICS-AUDIT-DESIGN-1"
    assert data["source_design_head"] == "753aafc44d5c41861ab6f357a728101bbc9faab7"


def test_all_twelve_assets_are_in_scope() -> None:
    data = load_authorization()
    assert len(data["required_asset_scope"]) == 12
    assert "metals:commodity:gold" in data["required_asset_scope"]
    assert "metals:commodity:uranium" in data["required_asset_scope"]
    assert "metals:vehicle:SLV" in data["required_asset_scope"]
    assert "metals:vehicle:BIL" in data["required_asset_scope"]


def test_required_semantic_columns_are_complete() -> None:
    data = load_authorization()
    columns = set(data["required_audit_columns"])
    for required in {
        "native_recommendation",
        "governed_uip_normalized_decision",
        "raw_expected_return",
        "adjusted_expected_return",
        "forecast_conflict_state",
        "risk_authority_type",
        "tactical_state",
        "primary_status_safe_to_surface",
        "primary_status_blocker_reason",
    }:
        assert required in columns


def test_required_execution_behavior_is_fail_closed() -> None:
    data = load_authorization()
    behavior = data["required_execution_behavior"]
    assert behavior
    assert all(behavior.values())
    assert behavior["unsafe_or_ambiguous_primary_status_must_fail_closed"] is True


def test_only_read_only_audit_execution_is_authorized() -> None:
    data = load_authorization()
    boundary = data["authorization_boundary"]
    assert boundary["read_only_audit_execution_authorized"] is True
    for key, value in boundary.items():
        if key == "read_only_audit_execution_authorized":
            continue
        assert value is False, key


def test_authorization_decision_and_next_decision() -> None:
    data = load_authorization()
    assert data["authorization_decision"] == "AUTHORIZE_READ_ONLY_METALS_DECISION_SEMANTICS_AUDIT"
    assert data["next_decision"] == "EXECUTE_AND_CERTIFY_READ_ONLY_METALS_DECISION_SEMANTICS_AUDIT"
