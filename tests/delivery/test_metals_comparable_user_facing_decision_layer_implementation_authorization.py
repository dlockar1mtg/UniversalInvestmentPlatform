from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "comparable_user_facing_decision_layer_implementation_authorization.json"


def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_identity_and_source_bindings():
    data = load()
    assert data["authorization_id"] == "METALS-COMPARABLE-USER-FACING-DECISION-LAYER-IMPLEMENTATION-AUTHORIZATION-1"
    assert data["source_design_id"] == "METALS-COMPARABLE-USER-FACING-DECISION-LAYER-DESIGN-1"
    assert data["source_design_head"] == "3aac888df4f7e92a3d7fa11992b4ccda87644526"
    assert data["source_semantic_audit_id"] == "METALS-DECISION-SEMANTICS-AUDIT-EXECUTION-1"


def test_database_and_hosted_r4_bindings():
    data = load()
    assert data["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert data["active_hosted_publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
    assert data["active_hosted_publication_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
    assert data["active_hosted_record_count"] == 12477


def test_primary_status_partition_exact():
    data = load()["certified_primary_status_partition"]
    assert set(data["HOLD"]) == {
        "metals:commodity:gold",
        "metals:commodity:uranium",
        "metals:vehicle:COPX",
        "metals:vehicle:CPER",
        "metals:vehicle:URA",
    }
    assert set(data["DECISION_CONFLICT"]) == {
        "metals:vehicle:GLD",
        "metals:vehicle:IAU",
        "metals:vehicle:PPLT",
        "metals:vehicle:SGOL",
        "metals:vehicle:SIVR",
        "metals:vehicle:SLV",
    }
    assert set(data["REFERENCE_CONTROL"]) == {"metals:vehicle:BIL"}


def test_runtime_scope_exact():
    data = load()
    assert set(data["authorized_runtime_files"]) == {
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
        "foundation/production/dashboard_assets/recommendation_visual.css",
    }


def test_required_behavior_all_true():
    data = load()
    assert data["required_implementation_behavior"]
    assert all(data["required_implementation_behavior"].values())


def test_semantic_guardrails_all_true():
    data = load()
    assert data["semantic_guardrails"]
    assert all(data["semantic_guardrails"].values())


def test_only_runtime_implementation_is_authorized():
    boundary = load()["authorization_boundary"]
    assert boundary["runtime_implementation_authorized"] is True
    for key, value in boundary.items():
        if key == "runtime_implementation_authorized":
            continue
        assert value is False, key


def test_decision_and_next_step():
    data = load()
    assert data["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_COMPARABLE_USER_FACING_DECISION_LAYER_IMPLEMENTATION"
    assert data["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_COMPARABLE_USER_FACING_DECISION_LAYER"
