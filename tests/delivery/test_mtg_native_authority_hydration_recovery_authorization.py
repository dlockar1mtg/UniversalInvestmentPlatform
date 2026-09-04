from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

AUTH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_native_authority_hydration_recovery_authorization_v1.json"
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
        == "UIP_MTG_NATIVE_AUTHORITY_HYDRATION_RECOVERY_AUTHORIZATION_V1"
    )

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_MTG_NATIVE_AUTHORITY_HYDRATION_AND_CRYPTO_QUALITY_RESEARCH_RECOVERY"
    )


def test_visual_acceptance_is_rejected() -> None:
    value = load_auth()["step_14m_g_visual_acceptance"]

    assert value["status"] == "REJECTED"
    assert value["collector_data_fidelity"] == "REJECTED"
    assert value["collector_visual_quality"] == "REJECTED"

    assert (
        value["precollector_visual_quality"]
        == "REJECTED"
    )

    assert value["hosted_deployment_authorized"] is False


def test_edge_of_eternities_contradiction_is_recorded() -> None:
    value = load_auth()["proven_collector_contradiction"]

    observed = value["generic_asset_detail_observed_state"]

    assert observed["current_price_usd"] == 717.61
    assert observed["current_price_authority_available"] is True

    assert observed["forecast_horizon_months"] == 12
    assert observed["point_forecast"] == 1205.893871

    assert (
        observed["expected_return"]
        == 0.6804306949457226
    )

    assert observed["forecast_authority_available"] is True


def test_generic_detail_has_precedence_when_richer() -> None:
    value = load_auth()["root_cause_boundary"]

    assert value["generic_asset_detail_read_success_proven"] is True

    assert (
        value[
            "detail_payload_must_not_be_ignored_when_it_contains_stronger_certified_authority"
        ]
        is True
    )


def test_required_hydrated_investment_fields() -> None:
    value = load_auth()["required_hydrated_fields"]

    assert value["current_price_usd"] is True
    assert value["forecast_1y_price_usd_from_point_forecast"] is True
    assert value["forecast_1y_return_from_expected_return"] is True
    assert value["forecast_horizon_months"] is True

    assert value["native_rank"] is True
    assert value["native_purchase_status"] is True
    assert value["evidence_state"] is True
    assert value["actionability_state"] is True


def test_missing_is_evaluated_after_normalization() -> None:
    value = load_auth()["required_missing_semantics"]

    assert value["missing_remains_missing"] is True

    assert (
        value["missing_must_be_evaluated_after_detail_normalization"]
        is True
    )

    assert (
        value["catalog_missing_must_not_override_observed_certified_detail"]
        is True
    )

    assert value["zero_must_not_be_substituted_for_missing"] is True


def test_collector_primary_research_must_use_hydrated_authority() -> None:
    value = load_auth()["collector_requirements"]

    assert value["hydrate_visible_research_detail"] is True
    assert value["promote_current_price_when_observed"] is True
    assert value["promote_1y_target_when_observed"] is True
    assert value["promote_1y_expected_return_when_observed"] is True

    assert (
        value["raw_records_must_not_contradict_primary_research_surface"]
        is True
    )


def test_precollector_ranked_and_blocked_states_remain_distinct() -> None:
    value = load_auth()["precollector_requirements"]

    assert (
        value[
            "ranked_forecastable_products_must_attempt_generic_detail_hydration"
        ]
        is True
    )

    assert (
        value[
            "blocked_products_must_remain_blocked_if_generic_detail_confirms_no_authority"
        ]
        is True
    )

    assert (
        value[
            "ranked_products_must_be_visually_distinguishable_from_blocked_products"
        ]
        is True
    )


def test_crypto_quality_research_hierarchy_is_required() -> None:
    value = load_auth()["crypto_quality_visual_requirements"]

    assert value["primary_research_hierarchy_required"] is True

    assert value["current_price_primary_metric_when_available"] is True
    assert value["one_year_target_primary_metric_when_available"] is True
    assert value["one_year_return_primary_metric_when_available"] is True

    assert (
        value["raw_record_dump_is_secondary_provenance_not_primary_research"]
        is True
    )

    assert (
        value[
            "collector_and_precollector_must_feel_like_investment_research_not_database_debug_views"
        ]
        is True
    )


def test_backend_and_deployment_remain_forbidden() -> None:
    value = load_auth()["explicitly_forbidden"]

    assert value["postgres_write"] is True
    assert value["new_backend_endpoint"] is True
    assert value["mtg_source_repository_change"] is True
    assert value["mtg_model_change"] is True
    assert value["universal_mtg_rank"] is True
    assert value["cross_domain_rank"] is True
    assert value["automatic_purchase_execution"] is True
    assert value["hosted_deployment"] is True
