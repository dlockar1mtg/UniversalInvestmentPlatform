from __future__ import annotations

import json
from pathlib import Path

from scripts.verify_metals_composite_presentation_activation_authorization import verify

ROOT = Path(__file__).resolve().parents[2]
AUTH_PATH = ROOT / "config" / "metals" / "composite_presentation_activation_authorization.json"


def load_auth() -> dict:
    return json.loads(AUTH_PATH.read_text(encoding="utf-8"))


def test_activation_candidate_is_exactly_bound() -> None:
    doc = load_auth()
    candidate = doc["candidate"]
    assert candidate["publication_id"] == "metals-mtg-composite-recovery-r1-20260828"
    assert candidate["publication_status"] == "STAGED"
    assert candidate["record_count"] == 13264
    assert candidate["content_fingerprint"] == "67352221b51e7479fe9e154e12dd718a9cf392c794d2320461203fe980bfc009"
    assert candidate["metals_final_action_match_count"] == 12
    assert candidate["mtg_premium_record_count"] == 787


def test_activation_scope_is_bounded() -> None:
    scope = load_auth()["authorization_scope"]
    assert scope["hosted_publication_activation_authorized"] is True
    assert scope["active_pointer_mutation_authorized"] is True
    assert scope["hosted_publication_stage_authorized"] is False
    assert scope["repository_code_change_authorized"] is False
    assert scope["analytical_database_write_authorized"] is False
    assert scope["model_refresh_authorized"] is False
    assert scope["forecast_refresh_authorized"] is False
    assert scope["recommendation_recompute_authorized"] is False
    assert scope["mtg_premium_recompute_authorized"] is False
    assert scope["manual_render_deployment_authorized"] is False
    assert scope["allocation_or_execution_authorized"] is False


def test_activation_authorization_verifier_passes() -> None:
    result = verify()
    assert result["status"] == "PASS"
    for key, value in result.items():
        if key != "status":
            assert value is True, key
