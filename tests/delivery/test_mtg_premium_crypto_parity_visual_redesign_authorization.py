from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_crypto_parity_visual_redesign_authorization_v1.json"
)


def auth() -> dict:
    return json.loads(
        PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_identity_status_and_rejection() -> None:
    value = auth()

    assert (
        value["authorization_id"]
        == "UIP_MTG_PREMIUM_CRYPTO_PARITY_VISUAL_REDESIGN_AUTHORIZATION_V1"
    )

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_MTG_CRYPTO_PARITY_VISUAL_REDESIGN"
    )

    rejected = value["visual_acceptance_result"]

    assert rejected["status"] == "REJECTED"
    assert rejected["backend_failure"] is False
    assert rejected["api_failure"] is False

    assert rejected["visual_hierarchy_failure"] is True
    assert rejected["information_architecture_failure"] is True


def test_certified_backend_is_preserved() -> None:
    backend = auth()["certified_authority_to_preserve"]

    assert backend["live_premium_record_count"] == 787

    assert (
        backend["premium_endpoint"]
        == "/v1/presentation/mtg-research/{asset_id}"
    )

    assert backend["premium_payload_state"] == "LOSSLESS"


def test_crypto_parity_is_visual_not_semantic_copy() -> None:
    target = auth()["design_objective"]

    assert target["target_quality"] == "CRYPTO_RESEARCH_PRESENTATION_PARITY"

    assert target["copy_crypto_domain_semantics"] is False

    assert target["reuse_crypto_visual_language"] is True

    assert target["preserve_mtg_native_semantics"] is True


def test_three_mtg_lanes_are_required() -> None:
    architecture = auth()["required_mtg_information_architecture"]

    assert architecture["explicit_lane_navigation_required"] is True

    assert architecture["required_lane_tabs"] == [
        "SECRET_LAIR",
        "COLLECTOR",
        "PRE_COLLECTOR",
    ]

    assert (
        architecture[
            "secret_lair_premium_view_must_not_be_interleaved_with_collector_records"
        ]
        is True
    )

    assert (
        architecture[
            "secret_lair_premium_view_must_not_be_interleaved_with_precollector_records"
        ]
        is True
    )


def test_secret_lair_cards_are_investment_first() -> None:
    card = auth()["required_secret_lair_card"]

    for key in (
        "product_name",
        "native_purchase_status",
        "current_market_price",
        "q10_governed_entry_price",
        "current_distance_to_q10",
        "certified_one_year_return",
        "one_year_risk_context",
        "three_year_scenario_context",
        "five_year_scenario_context",
        "evidence_strength",
        "open_research_action",
        "card_must_be_visually_scannable",
    ):
        assert card[key] is True


def test_detail_requires_crypto_quality_research_structure() -> None:
    detail = auth()["required_secret_lair_detail"]

    for key in (
        "crypto_quality_research_hero",
        "current_price_vs_governed_entry_visualization",
        "certified_one_year_forecast_panel",
        "one_year_distribution_visualization",
        "one_year_loss_probability",
        "one_year_positive_return_probability",
        "three_year_scenario_panel",
        "five_year_scenario_panel",
        "evidence_and_comparable_support_panel",
        "native_recommendation_context",
        "method_and_governance_secondary_not_primary",
    ):
        assert detail[key] is True


def test_collector_and_precollector_do_not_receive_fake_premium_data() -> None:
    collector = auth()["collector_lane_requirements"]
    precollector = auth()["precollector_lane_requirements"]

    assert collector["collector_certified_core_remains_available"] is True

    assert (
        collector[
            "collector_premium_secret_lair_fields_must_not_be_synthesized"
        ]
        is True
    )

    assert (
        collector[
            "collector_ranking_identity_bridge_remains_fail_closed"
        ]
        is True
    )

    assert (
        precollector[
            "precollector_certification_bridge_remains_fail_closed"
        ]
        is True
    )

    assert (
        precollector[
            "precollector_premium_secret_lair_fields_must_not_be_synthesized"
        ]
        is True
    )


def test_visual_system_moves_toward_existing_crypto_quality() -> None:
    visual = auth()["visual_requirements"]

    assert visual["use_external_recommendation_visual_css"] is True

    assert (
        visual[
            "large_inline_dynamic_style_system_should_be_removed_or_materially_reduced"
        ]
        is True
    )

    assert (
        visual[
            "reuse_existing_rec_asset_card_language_where_appropriate"
        ]
        is True
    )

    assert (
        visual[
            "reuse_existing_rec_detail_language_where_appropriate"
        ]
        is True
    )

    assert (
        visual[
            "investment_metrics_must_be_more_prominent_than_governance_prose"
        ]
        is True
    )


def test_q10_scenario_rank_and_execution_semantics_remain_locked() -> None:
    semantic = auth()["semantic_constraints"]

    assert semantic["q10_is_governed_purchase_threshold"] is True

    assert semantic["q25_may_replace_q10"] is False
    assert semantic["q50_may_replace_q10"] is False

    assert semantic["three_year_values_are_scenarios"] is True
    assert semantic["five_year_values_are_scenarios"] is True

    assert semantic["three_year_values_may_trigger_purchase"] is False
    assert semantic["five_year_values_may_trigger_purchase"] is False

    assert semantic["universal_mtg_rank_may_be_created"] is False
    assert semantic["cross_domain_rank_may_be_created"] is False

    assert (
        semantic["automatic_purchase_execution_authorized"]
        is False
    )


def test_backend_and_deployment_remain_forbidden() -> None:
    forbidden = auth()["explicitly_forbidden"]

    for key in (
        "postgres_write",
        "presentation_stage",
        "presentation_activate",
        "active_pointer_mutation",
        "read_api_change",
        "new_backend_endpoint",
        "analytical_database_change",
        "mtg_source_repository_change",
        "premium_sidecar_change",
        "model_execution",
        "model_retraining",
        "universal_mtg_rank",
        "cross_domain_rank",
        "automatic_purchase_execution",
        "hosted_deployment",
    ):
        assert forbidden[key] is True
