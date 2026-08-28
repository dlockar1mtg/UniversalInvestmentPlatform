from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PATH = ROOT / "config" / "metals" / "composite_presentation_recovery_authorization.json"


def load():
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_composite_recovery_boundary_is_exact():
    data = load()
    diff = data["differential_contract"]
    assert diff["changed_preexisting_record_count"] == 12
    assert diff["changed_metals_recommendation_count"] == 12
    assert diff["other_changed_preexisting_record_count"] == 0
    assert diff["active_only_record_count"] == 787
    assert diff["active_only_is_exactly_787_mtg_premium_records"] is True
    assert diff["certified_only_record_count"] == 0
    assert diff["safe_composite_recovery_shape"] is True


def test_recovery_preserves_new_mtg_and_restores_only_metals_recommendations():
    data = load()
    contract = data["recovery_contract"]
    assert contract["candidate_record_count"] == 13264
    assert contract["preserve_current_active_records_except_exact_12_metals_recommendations"] is True
    assert contract["preserve_all_787_mtg_premium_research_records"] is True
    assert contract["replace_exact_12_metals_recommendation_records_from_certified_publication"] is True
    assert contract["expected_metals_final_action_match_count_after_recovery"] == 12


def test_authorization_does_not_open_hosted_write_or_activation():
    scope = load()["authorization_scope"]
    assert scope["read_hosted_presentation_records_authorized"] is True
    assert scope["materialize_local_composite_candidate_authorized"] is True
    assert scope["local_candidate_validation_authorized"] is True
    for key in (
        "hosted_publication_stage_authorized",
        "hosted_publication_activation_authorized",
        "active_pointer_mutation_authorized",
        "repository_code_change_authorized",
        "analytical_database_write_authorized",
        "model_refresh_authorized",
        "forecast_refresh_authorized",
        "recommendation_recompute_authorized",
        "mtg_premium_recompute_authorized",
        "manual_render_deployment_authorized",
        "allocation_or_execution_authorized",
    ):
        assert scope[key] is False
