from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

AUTHORIZATION_PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_sidecar_export_authorization_v1.json"
)


def authorization() -> dict:
    return json.loads(
        AUTHORIZATION_PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_identity_and_status() -> None:
    value = authorization()

    assert (
        value["authorization_id"]
        == "UIP_MTG_PREMIUM_SIDECAR_EXPORT_AUTHORIZATION_V1"
    )

    assert value["authorization_version"] == "1.0.0"

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_SOURCE_IMPLEMENTATION"
    )


def test_bound_to_certified_bridge_design() -> None:
    value = authorization()["governing_design"]

    assert (
        value["design_id"]
        == "UIP_MTG_PREMIUM_SIDECAR_BRIDGE_V1"
    )

    assert value["design_version"] == "1.0.0"

    assert (
        value["required_uip_head"]
        == "c58a7b8f433fbedb2e64461e73336148ab2687b5"
    )


def test_bound_to_exact_source_authority() -> None:
    source = authorization()["certified_source_authority"]

    assert (
        source["required_source_branch"]
        == "phase-9.1-mtg-to-uip-export-contract"
    )

    assert (
        source["required_source_head"]
        == "f7dea3e2611f27de4ff6541da3b1d6a60dc6d695"
    )

    assert (
        source["source_path"]
        == "docs/phase_8/secret_lair/secret_lair_v1_purchase_analysis.csv"
    )

    assert (
        source["source_sha256"]
        == "eb5efced959116eb7b174d4aff27c06d321e774eda39b3f8572d958499441cdb"
    )

    assert source["source_row_count"] == 787
    assert source["source_field_count"] == 58
    assert source["unique_identity_count"] == 787

    assert (
        source["automatic_purchase_execution_true_rows"]
        == 0
    )


def test_output_is_separate_sidecar() -> None:
    output = authorization()["authorized_output"]

    assert (
        output["dataset_name"]
        == "mtg_secret_lair_premium_research"
    )

    assert (
        output["filename"]
        == "mtg_secret_lair_premium_research.csv"
    )

    assert output["initial_expected_rows"] == 787

    assert (
        output["uip_asset_id_rule"]
        == "SECRET_LAIR_V1_1|{secret_lair_id}"
    )

    assert output["duplicate_uip_asset_id_allowed"] is False
    assert output["blank_identity_allowed"] is False


def test_semantics_are_preserved() -> None:
    semantics = authorization()["semantic_contract"]

    assert (
        semantics["one_year_semantic"]
        == "CERTIFIED_FORECAST_AND_EMPIRICAL_RISK"
    )

    assert (
        semantics["three_year_semantic"]
        == "SCENARIO_DISTRIBUTION_NOT_DIRECTLY_VALIDATED"
    )

    assert (
        semantics["five_year_semantic"]
        == "SCENARIO_DISTRIBUTION_NOT_DIRECTLY_VALIDATED"
    )

    assert (
        semantics["q10_is_governed_purchase_entry_threshold"]
        is True
    )

    assert semantics["q25_or_q50_may_replace_q10"] is False

    assert (
        semantics[
            "three_or_five_year_scenario_may_trigger_purchase"
        ]
        is False
    )

    assert semantics["rank_may_override_purchase_policy"] is False

    assert (
        semantics["automatic_purchase_execution_authorized"]
        is False
    )


def test_values_are_copy_only() -> None:
    rules = authorization()["copy_rules"]

    assert (
        rules["source_values_must_be_preserved_losslessly"]
        is True
    )

    for key in (
        "recalculation_authorized",
        "forecast_recomputation_authorized",
        "scenario_recomputation_authorized",
        "risk_recomputation_authorized",
        "entry_threshold_recomputation_authorized",
        "missing_value_synthesis_authorized",
        "semantic_relabeling_authorized",
    ):
        assert rules[key] is False


def test_only_bounded_mtg_source_export_is_authorized() -> None:
    scope = authorization()["implementation_scope"]

    assert (
        scope["mtg_source_repository_change_authorized"]
        is True
    )

    assert (
        scope["bounded_sidecar_export_builder_authorized"]
        is True
    )

    assert (
        scope["bounded_sidecar_export_tests_authorized"]
        is True
    )

    for key in (
        "existing_23_field_export_mutation_authorized",
        "collector_premium_export_authorized",
        "precollector_premium_export_authorized",
        "secret_lair_partial_206_promotion_authorized",
        "model_execution_authorized",
        "model_retraining_authorized",
        "database_write_authorized",
        "uip_ingestion_authorized",
        "presentation_projection_write_authorized",
        "hosted_activation_authorized",
        "frontend_change_authorized",
        "automatic_purchase_execution_authorized",
    ):
        assert scope[key] is False


def test_source_implementation_controls_fail_closed() -> None:
    controls = authorization()[
        "required_source_implementation_controls"
    ]

    for key in (
        "fail_if_source_sha256_differs",
        "fail_if_source_row_count_differs_for_initial_build",
        "fail_if_source_identity_count_differs_for_initial_build",
        "fail_if_duplicate_secret_lair_id_exists",
        "fail_if_blank_secret_lair_id_exists",
        "fail_if_automatic_purchase_execution_is_true",
        "fail_if_required_authorized_field_missing",
        "fail_if_output_contains_non_authorized_analytical_field",
        "existing_phase_9_export_must_remain_byte_unchanged",
    ):
        assert controls[key] is True


def test_authorized_research_fields_are_present() -> None:
    fields = set(
        authorization()["authorized_source_fields"]
    )

    required = {
        "current_tcg_market_price_usd",
        "certified_1y_point_forecast_usd",
        "certified_1y_point_return",
        "y1_q10_break_even_entry_price_usd",
        "y1_probability_of_loss",
        "y1_probability_of_positive_return",
        "y1_downside_tail_mean_total_return",
        "y1_upside_tail_mean_total_return",
        "y1_q10_terminal_value_usd",
        "y1_q50_terminal_value_usd",
        "y1_q90_terminal_value_usd",
        "y3_median_total_return_scenario",
        "y3_probability_of_loss_scenario",
        "y3_q10_terminal_value_scenario_usd",
        "y3_q50_terminal_value_scenario_usd",
        "y3_q90_terminal_value_scenario_usd",
        "y5_median_total_return_scenario",
        "y5_probability_of_loss_scenario",
        "y5_q10_terminal_value_scenario_usd",
        "y5_q50_terminal_value_scenario_usd",
        "y5_q90_terminal_value_scenario_usd",
        "own_history_evidence_class",
        "history_span_days",
        "historical_observation_count",
        "exact_structural_comparable_support",
        "exact_structural_comparable_product_count",
        "global_comparable_product_count",
        "exact_structural_comparable_event_count",
        "global_comparable_event_count",
    }

    assert required <= fields


def test_next_gate_is_source_implementation() -> None:
    assert (
        authorization()["next_gate"]
        == "IMPLEMENT_AND_CERTIFY_MTG_SOURCE_PREMIUM_SIDECAR_EXPORT"
    )
