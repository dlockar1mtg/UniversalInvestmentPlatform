from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

CONTRACT_PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_research_contract_v1.json"
)


def _contract() -> dict:
    return json.loads(
        CONTRACT_PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_mtg_premium_contract_exists_and_is_versioned() -> None:
    contract = _contract()

    assert (
        contract["contract_id"]
        == "UIP_MTG_PREMIUM_RESEARCH_PRESENTATION_V1"
    )
    assert contract["contract_version"] == "1.0.0"
    assert contract["domain_id"] == "mtg"


def test_contract_preserves_domain_native_semantics() -> None:
    contract = _contract()
    principles = contract["design_principles"]

    assert principles["cross_domain_rank_created"] is False
    assert principles["universal_mtg_rank_created"] is False
    assert principles["automatic_purchase_execution_authorized"] is False
    assert principles["native_purchase_semantics_preserved"] is True
    assert principles["missing_authority_remains_missing"] is True
    assert principles["source_values_may_not_be_synthesized"] is True
    assert (
        principles["scenario_may_not_be_relabelled_as_direct_forecast"]
        is True
    )


def test_collector_core_authority_uses_canonical_identity() -> None:
    contract = _contract()
    collector = contract["lanes"]["COLLECTOR_V1"]

    assert collector["primary_identity_key"] == "canonical_product_id"

    assert (
        collector["forecast_authority"]["unique_products"]
        == 49
    )
    assert (
        collector["purchase_authority"]["unique_products"]
        == 49
    )
    assert (
        collector["purchase_authority"]["join_key"]
        == "canonical_product_id"
    )


def test_collector_ranking_is_fail_closed_until_identity_bridge() -> None:
    contract = _contract()
    ranking = (
        contract["lanes"]["COLLECTOR_V1"]
        ["ranking_authority"]
    )

    assert ranking["state"] == "IDENTITY_BRIDGE_REQUIRED"
    assert ranking["name_join_authorized"] is False
    assert ranking["implicit_tcgplayer_join_authorized"] is False
    assert ranking["presentation_promotion_authorized"] is False


def test_precollector_validation_source_is_not_silently_promoted() -> None:
    contract = _contract()
    lane = contract["lanes"]["PRE_COLLECTOR"]

    assert lane["presentation_state"] == "CERTIFICATION_BRIDGE_REQUIRED"
    assert lane["guarded_scenario_source"]["unique_products"] == 119
    assert (
        lane["certified_structured_outputs_found_under_permanence_tree"]
        == 0
    )
    assert lane["presentation_promotion_authorized"] is False


def test_secret_lair_population_is_explicitly_partial() -> None:
    contract = _contract()
    lane = contract["lanes"]["SECRET_LAIR_V1_1"]

    assert lane["scenario_population"] == 993
    assert lane["full_research_population"] == 787
    assert lane["partial_research_population"] == 206

    policy = lane["partial_population_policy"]

    assert policy["synthetic_rank_allowed"] is False
    assert policy["synthetic_purchase_recommendation_allowed"] is False


def test_secret_lair_long_horizon_values_remain_scenarios() -> None:
    contract = _contract()
    semantics = (
        contract["lanes"]["SECRET_LAIR_V1_1"]
        ["research_semantics"]
    )

    assert (
        semantics["three_year"]
        == "SCENARIO_DISTRIBUTION_NOT_DIRECTLY_VALIDATED"
    )
    assert (
        semantics["five_year"]
        == "SCENARIO_DISTRIBUTION_NOT_DIRECTLY_VALIDATED"
    )
    assert (
        semantics["three_or_five_year_scenario_may_trigger_buy"]
        is False
    )


def test_secret_lair_q10_entry_policy_is_preserved() -> None:
    contract = _contract()
    semantics = (
        contract["lanes"]["SECRET_LAIR_V1_1"]
        ["research_semantics"]
    )

    assert semantics["q10_entry_policy_preserved"] is True
    assert semantics["q25_or_q50_may_be_used_as_buy_threshold"] is False
    assert semantics["rank_may_override_purchase_policy"] is False


def test_ui_requires_visual_not_semantic_crypto_parity() -> None:
    contract = _contract()
    ui = contract["ui_contract"]

    assert ui["crypto_visual_quality_parity_required"] is True
    assert ui["crypto_semantic_parity_required"] is False

    assert ui["detail_sections"] == [
        "LONG_TERM_OUTLOOK",
        "CURRENT_VALUATION",
        "ENTRY_CONTEXT",
        "FORECAST_OR_SCENARIO_PATH",
        "WHY_THIS_PRODUCT",
        "COMPARABLE_EVIDENCE",
        "RISK_ASSESSMENT",
        "NATIVE_RECOMMENDATION",
    ]


def test_contract_does_not_authorize_data_or_frontend_promotion_yet() -> None:
    contract = _contract()
    authorization = contract["authorization"]

    assert authorization["contract_creation_authorized"] is True
    assert (
        authorization["presentation_projection_implementation_authorized_next"]
        is True
    )

    assert authorization["source_copy_or_ingestion_authorized"] is False
    assert authorization["database_schema_change_authorized"] is False
    assert authorization["precollector_validation_promotion_authorized"] is False
    assert authorization["collector_ranking_identity_bridge_authorized"] is False
    assert authorization["frontend_premium_mtg_detail_authorized"] is False
    assert authorization["automatic_purchase_execution_authorized"] is False
