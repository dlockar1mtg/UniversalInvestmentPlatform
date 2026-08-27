from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

AUTH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_native_lane_deep_research_authorization_v1.json"
)


def load_auth() -> dict:
    return json.loads(
        AUTH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_identity_and_status() -> None:
    value = load_auth()

    assert (
        value["authorization_id"]
        == "UIP_MTG_NATIVE_LANE_DEEP_RESEARCH_AUTHORIZATION_V1"
    )

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_MTG_COLLECTOR_PRECOLLECTOR_DEEP_RESEARCH_IMPLEMENTATION"
    )


def test_visual_acceptance_gap_is_exact() -> None:
    finding = load_auth()["visual_acceptance_findings"]

    assert finding["secret_lair_deep_research_exists"] is True
    assert finding["secret_lair_deep_research_preserve"] is True

    assert finding["collector_deep_research_missing"] is True
    assert finding["precollector_deep_research_missing"] is True


def test_generic_asset_detail_is_first_authority() -> None:
    value = load_auth()["existing_frontend_authority_to_reuse"]

    assert (
        value["generic_asset_detail_reader"]
        == "readAssetDetail(item)"
    )

    assert (
        value["generic_asset_detail_endpoint"]
        == "/v1/presentation/assets/{domain_id}/{asset_id}"
    )

    assert (
        value["new_backend_endpoint_required_by_authorization"]
        is False
    )


def test_collector_gets_real_native_detail() -> None:
    value = load_auth()["collector_requirements"]

    assert value["all_collector_cards_may_open_research_detail"] is True

    assert value["native_rank_visible_when_present"] is True
    assert value["current_price_authority_visible_when_present"] is True
    assert value["forecast_records_visible_when_present"] is True
    assert value["risk_records_visible_when_present"] is True

    assert (
        value["secret_lair_premium_fields_must_not_be_synthesized"]
        is True
    )


def test_precollector_gets_real_native_detail() -> None:
    value = load_auth()["precollector_requirements"]

    assert (
        value["all_precollector_cards_may_open_research_detail"]
        is True
    )

    assert (
        value[
            "ranked_forecastable_products_must_be_visually_distinguishable_from_blocked_products"
        ]
        is True
    )

    assert value["current_price_authority_visible_when_present"] is True
    assert value["forecast_records_visible_when_present"] is True
    assert value["risk_records_visible_when_present"] is True

    assert value["missing_current_price_authority_must_be_explained"] is True
    assert value["forecast_gap_must_be_explained"] is True


def test_missing_stays_missing() -> None:
    value = load_auth()["required_shared_native_lane_behavior"]

    assert value["missing_values_must_remain_missing"] is True
    assert value["missing_values_must_not_be_converted_to_zero"] is True
    assert value["missing_values_must_not_be_inferred_from_secret_lair"] is True


def test_native_lane_interaction_is_required() -> None:
    value = load_auth()["interaction_requirements"]

    assert value["explicit_open_research_button"] is True

    assert value["button_must_work_for_collector"] is True
    assert value["button_must_work_for_precollector"] is True

    assert (
        value[
            "button_must_not_route_collector_to_secret_lair_premium_renderer"
        ]
        is True
    )

    assert (
        value[
            "button_must_not_route_precollector_to_secret_lair_premium_renderer"
        ]
        is True
    )


def test_rank_semantics_remain_native() -> None:
    value = load_auth()["semantic_constraints"]

    assert value["collector_native_rank_is_not_universal_rank"] is True
    assert value["precollector_native_rank_is_not_universal_rank"] is True

    assert value["universal_mtg_rank_may_be_created"] is False
    assert value["cross_domain_rank_may_be_created"] is False


def test_backend_and_deployment_remain_forbidden() -> None:
    value = load_auth()["explicitly_forbidden"]

    assert value["postgres_write"] is True
    assert value["new_backend_endpoint"] is True

    assert (
        value["read_api_change_without_separate_authorization"]
        is True
    )

    assert value["mtg_source_repository_change"] is True
    assert value["mtg_model_change"] is True

    assert value["automatic_purchase_execution"] is True
    assert value["hosted_deployment"] is True


def test_next_gate_is_implementation() -> None:
    value = load_auth()["next_gate"]

    assert (
        value["authorized_next_step"]
        == "IMPLEMENT_MTG_COLLECTOR_PRECOLLECTOR_DEEP_RESEARCH"
    )

    assert (
        value[
            "generic_asset_detail_authority_must_be_attempted_before_backend_expansion"
        ]
        is True
    )

    assert value["hosted_deployment_authorized"] is False
