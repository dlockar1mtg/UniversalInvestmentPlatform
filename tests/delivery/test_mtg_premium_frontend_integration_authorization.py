from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_frontend_integration_authorization_v1.json"
)


def auth() -> dict:
    return json.loads(
        PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_identity_and_status() -> None:
    value = auth()

    assert (
        value["authorization_id"]
        == "UIP_MTG_PREMIUM_FRONTEND_INTEGRATION_AUTHORIZATION_V1"
    )

    assert value["authorization_version"] == "1.0.0"

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_MTG_PREMIUM_RESEARCH_FRONTEND_IMPLEMENTATION"
    )


def test_exact_backend_authority_is_bound() -> None:
    backend = auth()["certified_backend_authority"]

    assert (
        backend["evidence_id"]
        == "UIP_MTG_PREMIUM_LIVE_READ_API_VALIDATION_EVIDENCE_V1"
    )

    assert (
        backend["active_publication_id"]
        == "mtg-premium-stage-rehearsal-ac8adb415f03"
    )

    assert backend["active_record_count"] == 13264
    assert backend["live_premium_record_count"] == 787
    assert backend["live_premium_unique_asset_id_count"] == 787

    assert (
        backend["endpoint"]
        == "/v1/presentation/mtg-research/{asset_id}"
    )

    assert backend["premium_response_field"] == "premium_research"
    assert backend["premium_payload_state"] == "LOSSLESS"


def test_frontend_baseline_is_cleanly_bound() -> None:
    baseline = auth()["observed_frontend_baseline"]

    assert (
        baseline["file"]
        == "foundation/production/dashboard_assets/recommendation_ui.js"
    )

    assert baseline["mtg_domain_exists"] is True

    assert (
        baseline["premium_mtg_endpoint_currently_consumed"]
        is False
    )

    assert (
        baseline["premium_research_payload_currently_consumed"]
        is False
    )

    assert (
        baseline["dedicated_premium_mtg_detail_currently_present"]
        is False
    )


def test_implementation_scope_is_bounded() -> None:
    scope = auth()["authorized_implementation_scope"]

    assert scope["frontend_source_change_authorized"] is True

    assert (
        scope["allowed_frontend_file"]
        == "foundation/production/dashboard_assets/recommendation_ui.js"
    )

    assert scope["allow_on_demand_mtg_research_endpoint_call"] is True
    assert scope["allow_dedicated_mtg_research_cards"] is True
    assert scope["allow_dedicated_mtg_research_detail"] is True

    assert scope["new_backend_endpoint_authorized"] is False
    assert scope["read_api_change_authorized"] is False
    assert scope["database_change_authorized"] is False


def test_secret_lair_premium_fields_are_authorized() -> None:
    required = auth()["required_secret_lair_presentation"]

    for key in (
        "display_current_market_price_where_available",
        "display_certified_one_year_point_forecast_where_available",
        "display_certified_one_year_return_where_available",
        "display_q10_break_even_entry_price_where_available",
        "display_current_margin_to_q10_where_available",
        "display_current_price_vs_q10_state_where_available",
        "display_one_year_loss_probability_where_available",
        "display_one_year_positive_return_probability_where_available",
        "display_one_year_q10_q50_q90_range_where_available",
        "display_three_year_scenario_distribution_where_available",
        "display_five_year_scenario_distribution_where_available",
        "display_evidence_support_where_available",
    ):
        assert required[key] is True


def test_q10_and_scenario_semantics_are_locked() -> None:
    semantic = auth()["semantic_constraints"]

    assert semantic["one_year_point_forecast_is_certified_forecast"] is True
    assert semantic["q10_is_governed_purchase_threshold"] is True

    assert semantic["q25_may_replace_q10"] is False
    assert semantic["q50_may_replace_q10"] is False

    assert semantic["three_year_values_are_scenarios"] is True
    assert semantic["five_year_values_are_scenarios"] is True

    assert (
        semantic[
            "three_year_values_must_not_be_presented_as_direct_certified_forecasts"
        ]
        is True
    )

    assert (
        semantic[
            "five_year_values_must_not_be_presented_as_direct_certified_forecasts"
        ]
        is True
    )

    assert semantic["three_year_values_may_trigger_purchase"] is False
    assert semantic["five_year_values_may_trigger_purchase"] is False


def test_rank_and_execution_creation_remain_forbidden() -> None:
    semantic = auth()["semantic_constraints"]

    assert semantic["cross_domain_rank_may_be_created"] is False
    assert semantic["universal_mtg_rank_may_be_created"] is False

    assert (
        semantic["automatic_purchase_execution_authorized"]
        is False
    )

    assert (
        semantic["native_rank_may_override_q10_purchase_policy"]
        is False
    )


def test_missing_and_other_lanes_remain_fail_closed() -> None:
    lanes = auth()["lane_boundaries"]
    semantic = auth()["semantic_constraints"]

    assert semantic["missing_premium_authority_must_remain_missing"] is True

    assert lanes["secret_lair_premium_surface_authorized"] is True

    assert (
        lanes["collector_ranking_identity_bridge_must_remain_fail_closed"]
        is True
    )

    assert (
        lanes["precollector_certification_bridge_must_remain_fail_closed"]
        is True
    )

    assert (
        lanes["premium_fields_must_not_be_synthesized_for_nonpremium_assets"]
        is True
    )


def test_backend_database_and_deployment_remain_frozen() -> None:
    forbidden = auth()["explicitly_forbidden"]

    for key in (
        "postgres_write",
        "presentation_stage",
        "presentation_activate",
        "active_pointer_mutation",
        "analytical_database_change",
        "mtg_source_repository_change",
        "premium_sidecar_change",
        "read_api_change",
        "model_execution",
        "model_retraining",
        "universal_investment_score",
        "cross_domain_rank",
        "universal_mtg_rank",
        "automatic_purchase_execution",
        "hosted_deployment",
    ):
        assert forbidden[key] is True


def test_local_acceptance_is_next_gate() -> None:
    gate = auth()["next_gate_after_successful_implementation"]

    assert gate["frontend_local_acceptance_required"] is True

    assert (
        gate["hosted_deployment_authorized_by_this_document"]
        is False
    )

    assert (
        gate["next_gate"]
        == "CONSIDER_BOUNDED_MTG_PREMIUM_LOCAL_FRONTEND_ACCEPTANCE"
    )
