from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config" / "metals" / "r4_presentation_hierarchy_recovery_implementation_authorization.json"


def load_auth() -> dict:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def test_authorization_identity_and_source_binding() -> None:
    auth = load_auth()
    assert auth["authorization_id"] == "METALS-r4-PRESENTATION-HIERARCHY-RECOVERY-IMPLEMENTATION-AUTHORIZATION-1"
    assert auth["source_design_id"] == "METALS-r4-PRESENTATION-HIERARCHY-RECOVERY-DESIGN-1"
    assert auth["source_design_head"] == "b5ba7586a341dd75f5f335c28cf4fd75fc2f597d"
    assert auth["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_active_r4_binding() -> None:
    active = load_auth()["active_hosted_publication"]
    assert active["publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
    assert active["content_fingerprint"] == "aa6d2fa0cd575cedaceb8c2a10dd10c19b15c31e59dce35cec7a0199ed69b5d5"
    assert active["record_count"] == 12477


def test_runtime_file_scope_is_exact() -> None:
    files = sorted(load_auth()["authorized_runtime_files"])
    assert files == sorted([
        "foundation/production/dashboard_assets/recommendation_ui.js",
        "foundation/production/dashboard_assets/metals_tactical_ui.js",
        "foundation/production/dashboard_assets/recommendation_visual.css",
    ])


def test_required_behavior_is_all_true() -> None:
    behavior = load_auth()["required_implementation_behavior"]
    assert behavior
    assert all(value is True for value in behavior.values())


def test_semantic_guardrails_are_all_true() -> None:
    guardrails = load_auth()["semantic_guardrails"]
    assert guardrails
    assert all(value is True for value in guardrails.values())


def test_only_runtime_implementation_is_authorized() -> None:
    boundary = load_auth()["authorization_boundary"]
    assert boundary["runtime_implementation_authorized"] is True
    assert boundary["hosted_publication_write_authorized"] is False
    assert boundary["analytical_database_write_authorized"] is False
    assert boundary["forecast_refresh_authorized"] is False
    assert boundary["model_refresh_authorized"] is False
    assert boundary["csp_cleanup_authorized"] is False
    assert boundary["pr_authorized"] is False
    assert boundary["main_deployment_authorized"] is False


def test_decision_and_next_decision_are_bound() -> None:
    auth = load_auth()
    assert auth["authorization_decision"] == "AUTHORIZE_BOUNDED_METALS_r4_PRESENTATION_HIERARCHY_RECOVERY_IMPLEMENTATION"
    assert auth["next_decision"] == "IMPLEMENT_AND_CERTIFY_METALS_r4_PRESENTATION_HIERARCHY_RECOVERY"
