from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

AUTH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_final_research_ux_semantic_cleanup_authorization_v1.json"
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
        == "UIP_MTG_FINAL_RESEARCH_UX_SEMANTIC_CLEANUP_AUTHORIZATION_V1"
    )

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_MTG_FINAL_RESEARCH_UX_AND_SEMANTIC_CLEANUP"
    )


def test_i4_is_partial_pass_not_final_acceptance() -> None:
    value = load_auth()["step_14m_i4_acceptance"]

    assert (
        value["status"]
        == "PARTIAL_PASS_FINAL_ACCEPTANCE_WITHHELD"
    )

    assert value["collector_hydration"] == "PASS"
    assert value["precollector_ranked_hydration"] == "PASS"

    assert value["final_visual_acceptance"] == "WITHHELD"
    assert value["hosted_deployment_authorized"] is False


def test_q10_distance_is_real_usd_difference() -> None:
    value = load_auth()["secret_lair_q10_distance_contract"]

    assert (
        value["buy_candidate_below_q10_formula"]
        == "q10_entry_usd - current_price_usd"
    )

    assert value["must_not_format_ratio_as_currency"] is True

    example = value["example"]

    assert example["current_price_usd"] == 63.67
    assert example["q10_entry_usd"] == 64.18
    assert example["correct_display_distance_usd"] == 0.51


def test_q10_semantics_do_not_change() -> None:
    value = load_auth()["semantic_preservation"]

    assert value["secret_lair_q10_is_purchase_gate"] is True
    assert value["secret_lair_q25_q50_remain_diagnostic_only"] is True
    assert value["secret_lair_rank_cannot_override_q10"] is True


def test_encoding_cleanup_is_bounded() -> None:
    value = load_auth()["encoding_cleanup_contract"]

    assert value["visible_question_mark_separator_artifacts_forbidden"] is True

    assert value["preferred_html_separator"] == "&middot;"

    assert (
        value["question_mark_in_legitimate_product_name_must_not_be_removed"]
        is True
    )


def test_ranked_native_products_lead_default_order() -> None:
    value = load_auth()["native_default_ordering_contract"]

    assert (
        value["preferred_default_priority"][0]
        == "ranked_and_forecast_available"
    )

    assert value["within_ranked_group"] == "ascending native rank"

    assert value["blocked_products_may_not_be_hidden"] is True


def test_precollector_rank_one_priority_is_explicit() -> None:
    value = load_auth()["precollector_ordering_requirement"]

    assert (
        value[
            "dominaria_rank_1_should_sort_before_unranked_forecast_gap_products"
        ]
        is True
    )

    assert (
        value["ranked_forecastable_products_should_lead_default_view"]
        is True
    )


def test_card_cleanup_keeps_investment_information_primary() -> None:
    value = load_auth()["native_card_visual_cleanup"]

    assert "current market" in value["investment_fields_primary"]
    assert "1Y modeled target" in value["investment_fields_primary"]
    assert "expected 1Y return" in value["investment_fields_primary"]

    assert value["authority_yes_no_triplet_may_be_compacted"] is True
    assert value["open_research_action_must_remain_visible"] is True
    assert value["true_missing_state_must_remain_explicit"] is True


def test_authority_contradictions_are_not_silently_rewritten() -> None:
    value = load_auth()["authority_contradiction_presentation"]

    assert value["source_evidence_must_not_be_rewritten"] is True
    assert value["silent_reconciliation_forbidden"] is True
    assert value["synthetic_evidence_forbidden"] is True


def test_backend_model_execution_and_deploy_remain_forbidden() -> None:
    value = load_auth()["explicitly_forbidden"]

    assert value["postgres_write"] is True
    assert value["new_backend_endpoint"] is True
    assert value["mtg_source_repository_change"] is True
    assert value["mtg_model_change"] is True
    assert value["ranking_algorithm_change"] is True
    assert value["forecast_algorithm_change"] is True
    assert value["universal_mtg_rank"] is True
    assert value["cross_domain_rank"] is True
    assert value["automatic_purchase_execution"] is True
    assert value["hosted_deployment"] is True
