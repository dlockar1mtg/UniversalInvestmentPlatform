from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config/metals/commodity_decision_explanation_hosted_refresh_authorization.json"


def load_auth() -> dict:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def test_authorization_identity_and_source_binding() -> None:
    payload = load_auth()
    assert payload["authorization_id"] == "METALS-COMMODITY-DECISION-EXPLANATION-HOSTED-REFRESH-AUTHORIZATION-1"
    assert payload["source_implementation_head"] == "5d11c2a8d1e660165a5c172c054fee39feb3c2a0"
    assert payload["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"


def test_active_r3_is_bound_before_refresh() -> None:
    payload = load_auth()["active_hosted_publication_before_refresh"]
    assert payload["publication_id"] == "metals-v3-decision-utility-r3-20260826"
    assert payload["content_fingerprint"] == "e5f0bce3eb0181983e990e3de5795867dc53bf41c0d038b0d7302e722434b3ee"
    assert payload["record_count"] == 12475
    assert payload["commodity_explanation_record_count"] == 0


def test_target_r4_is_exactly_bounded() -> None:
    payload = load_auth()["authorized_hosted_publication_after_refresh"]
    assert payload["publication_id"] == "metals-v3-commodity-explanation-r4-20260826"
    assert payload["record_count"] == 12477
    assert payload["commodity_explanation_record_count"] == 2
    assert payload["gold_explanation_state"] == "AVAILABLE"
    assert payload["gold_risk_context_level"] == "ELEVATED"
    assert payload["uranium_explanation_state"] == "UNAVAILABLE"


def test_refresh_behavior_is_fully_required() -> None:
    payload = load_auth()["required_refresh_behavior"]
    assert payload
    assert all(value is True for value in payload.values())


def test_semantic_guardrails_are_fully_enabled() -> None:
    payload = load_auth()["semantic_guardrails"]
    assert payload
    assert all(value is True for value in payload.values())
    assert payload["do_not_rerun_after_success"] is True


def test_only_hosted_publication_write_is_authorized() -> None:
    boundary = load_auth()["authorization_boundary"]
    assert boundary["hosted_publication_write_authorized"] is True
    for key, value in boundary.items():
        if key == "hosted_publication_write_authorized":
            continue
        assert value is False, key


def test_authorization_decision_and_next_step() -> None:
    payload = load_auth()
    assert payload["authorization_decision"] == "AUTHORIZE_ONE_BOUNDED_METALS_COMMODITY_EXPLANATION_HOSTED_PRESENTATION_REFRESH"
    assert payload["next_decision"] == "EXECUTE_AND_CERTIFY_METALS_COMMODITY_EXPLANATION_HOSTED_PRESENTATION_REFRESH"
