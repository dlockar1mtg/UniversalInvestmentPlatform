from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DESIGN_PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_sidecar_bridge_design_v1.json"
)


def design() -> dict:
    return json.loads(
        DESIGN_PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_design_is_versioned_and_design_only() -> None:
    value = design()

    assert (
        value["design_id"]
        == "UIP_MTG_PREMIUM_SIDECAR_BRIDGE_V1"
    )
    assert value["design_version"] == "1.0.0"

    assert (
        value["status"]
        == "DESIGN_ONLY_NOT_IMPLEMENTATION_AUTHORIZATION"
    )


def test_existing_23_field_native_authority_is_frozen() -> None:
    baseline = design()["governed_baseline"]

    assert (
        baseline["existing_native_authority_interface"]
        == "mtg_native_authority_current"
    )

    assert (
        baseline["existing_native_authority_field_count"]
        == 23
    )

    assert (
        baseline["existing_native_authority_row_count"]
        == 968
    )

    assert (
        baseline["existing_secret_lair_row_count"]
        == 787
    )

    assert (
        baseline["existing_interface_must_remain_unchanged"]
        is True
    )


def test_secret_lair_premium_source_is_bound_by_native_identity() -> None:
    source = design()["source_authority"]

    assert (
        source["source_artifact"]
        == "secret_lair_v1_purchase_analysis.csv"
    )

    assert source["governed_population"] == 787
    assert source["identity_key"] == "secret_lair_id"

    assert (
        source["uip_asset_id_mapping"]
        == "SECRET_LAIR_V1_1|{secret_lair_id}"
    )

    assert (
        source["source_values_must_be_copied_without_recalculation"]
        is True
    )


def test_sidecar_is_separate_from_common_native_authority() -> None:
    sidecar = design()["proposed_delivery_sidecar"]

    assert (
        sidecar["dataset_name"]
        == "mtg_secret_lair_premium_research"
    )

    assert (
        sidecar["filename"]
        == "mtg_secret_lair_premium_research.csv"
    )

    assert sidecar["expected_initial_rows"] == 787
    assert sidecar["dynamic_population"] is True


def test_presentation_uses_separate_json_record_type() -> None:
    projection = design()["presentation_projection"]

    assert (
        projection["new_record_type"]
        == "mtg_premium_research"
    )

    assert projection["domain_id"] == "mtg"

    assert (
        projection["payload_storage"]
        == "presentation_records.payload_json"
    )

    assert (
        projection["analytical_database_schema_change_required"]
        is False
    )

    assert (
        projection["mtg_native_authority_schema_change_required"]
        is False
    )


def test_long_horizon_values_remain_scenarios() -> None:
    semantics = design()["semantic_rules"]

    assert semantics["one_year_is_certified_forecast"] is True

    assert semantics["three_year_is_direct_forecast"] is False
    assert semantics["five_year_is_direct_forecast"] is False

    assert (
        semantics["three_year_semantic"]
        == "SCENARIO_DISTRIBUTION_NOT_DIRECTLY_VALIDATED"
    )

    assert (
        semantics["five_year_semantic"]
        == "SCENARIO_DISTRIBUTION_NOT_DIRECTLY_VALIDATED"
    )


def test_q10_policy_is_preserved() -> None:
    semantics = design()["semantic_rules"]

    assert (
        semantics["q10_is_secret_lair_governed_entry_threshold"]
        is True
    )

    assert (
        semantics["q25_or_q50_may_replace_q10_entry_policy"]
        is False
    )

    assert (
        semantics["three_or_five_year_scenario_may_trigger_buy"]
        is False
    )

    assert (
        semantics["native_rank_may_override_purchase_policy"]
        is False
    )


def test_no_universal_or_execution_semantics_are_created() -> None:
    semantics = design()["semantic_rules"]

    assert semantics["cross_lane_rank_created"] is False
    assert semantics["cross_domain_rank_created"] is False

    assert (
        semantics["universal_purchase_policy_created"]
        is False
    )

    assert (
        semantics["automatic_purchase_execution_authorized"]
        is False
    )


def test_postgres_remains_presentation_copy_only() -> None:
    boundary = design()["publication_boundary"]

    assert (
        boundary[
            "postgres_is_presentation_copy_not_analytical_authority"
        ]
        is True
    )

    assert boundary["source_model_recomputation_in_uip"] is False
    assert boundary["scenario_recomputation_in_uip"] is False
    assert boundary["risk_recomputation_in_uip"] is False
    assert boundary["q10_recalculation_in_uip"] is False

    assert boundary["source_values_preserved_losslessly"] is True
    assert boundary["source_lineage_required"] is True
    assert boundary["source_sha256_required"] is True


def test_design_does_not_authorize_implementation() -> None:
    auth = design()["authorization"]

    assert auth["design_creation_authorized"] is True

    for key in (
        "source_sidecar_implementation_authorized",
        "source_copy_or_ingestion_authorized",
        "uip_import_engine_schema_change_authorized",
        "analytical_database_schema_change_authorized",
        "presentation_projection_write_authorized",
        "hosted_database_activation_authorized",
        "frontend_change_authorized",
        "model_rerun_authorized",
        "automatic_purchase_execution_authorized",
    ):
        assert auth[key] is False


def test_frontend_is_last_after_live_data() -> None:
    sequence = design()["implementation_sequence"]

    assert sequence[-1] == (
        "FRONTEND_IMPLEMENTATION_ONLY_AFTER_DATA_IS_LIVE"
    )

    assert (
        design()["next_gate"]
        == "REVIEW_AND_AUTHORIZE_MTG_SOURCE_PREMIUM_SIDECAR_EXPORT_CONTRACT"
    )
