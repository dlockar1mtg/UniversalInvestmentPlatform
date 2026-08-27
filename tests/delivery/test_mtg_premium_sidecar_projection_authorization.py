from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_sidecar_projection_authorization_v1.json"
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
        == "UIP_MTG_PREMIUM_SIDECAR_PROJECTION_AUTHORIZATION_V1"
    )

    assert value["authorization_version"] == "1.0.0"

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_ACCEPTANCE_AND_PROJECTION_IMPLEMENTATION"
    )


def test_exact_mtg_commit_is_bound() -> None:
    source = auth()["certified_mtg_source_checkpoint"]

    assert (
        source["head"]
        == "6b610b208549bec4be2c0ec7f7f3c2f69b154302"
    )

    assert (
        source["parent_head"]
        == "f7dea3e2611f27de4ff6541da3b1d6a60dc6d695"
    )

    assert source["commit_scope_file_count"] == 4


def test_exact_sidecar_authority_is_bound() -> None:
    sidecar = auth()["certified_premium_sidecar"]

    assert (
        sidecar["sha256"]
        == "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333"
    )

    assert sidecar["row_count"] == 787
    assert sidecar["field_count"] == 36

    assert (
        sidecar["unique_secret_lair_id_count"]
        == 787
    )

    assert (
        sidecar["unique_mtg_asset_id_count"]
        == 787
    )

    assert (
        sidecar["identity_rule"]
        == "SECRET_LAIR_V1_1|{secret_lair_id}"
    )


def test_existing_native_authority_remains_frozen() -> None:
    native = auth()["existing_native_authority"]

    assert native["required_field_count"] == 23
    assert native["mutation_authorized"] is False
    assert native["replacement_authorized"] is False


def test_projection_uses_separate_record_type() -> None:
    projection = auth()["authorized_projection"]

    assert (
        projection["presentation_record_type"]
        == "mtg_premium_research"
    )

    assert (
        projection["storage_surface"]
        == "presentation_records.payload_json"
    )

    assert projection["one_record_per_sidecar_row"] is True
    assert projection["expected_initial_record_count"] == 787

    assert (
        projection["record_asset_id_field"]
        == "mtg_asset_id"
    )

    assert (
        projection["analytical_table_schema_change_required"]
        is False
    )

    assert (
        projection[
            "generic_forecast_record_replacement_authorized"
        ]
        is False
    )

    assert (
        projection[
            "generic_risk_record_replacement_authorized"
        ]
        is False
    )

    assert (
        projection[
            "native_authority_replacement_authorized"
        ]
        is False
    )


def test_semantics_remain_lane_native() -> None:
    semantics = auth()["semantic_contract"]

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


def test_only_bounded_code_implementation_is_authorized() -> None:
    scope = auth()["implementation_scope"]

    assert (
        scope[
            "bounded_uip_sidecar_acceptance_code_authorized"
        ]
        is True
    )

    assert (
        scope[
            "bounded_presentation_projection_code_authorized"
        ]
        is True
    )

    assert (
        scope["bounded_projection_tests_authorized"]
        is True
    )

    for key in (
        "copy_sidecar_into_certified_uip_delivery_package_authorized",
        "analytical_database_schema_change_authorized",
        "analytical_database_ingestion_authorized",
        "hosted_postgres_write_authorized",
        "live_publication_activation_authorized",
        "frontend_change_authorized",
        "collector_premium_projection_authorized",
        "precollector_premium_projection_authorized",
        "secret_lair_partial_206_promotion_authorized",
        "model_execution_authorized",
        "model_retraining_authorized",
        "automatic_purchase_execution_authorized",
    ):
        assert scope[key] is False


def test_fail_closed_controls_are_required() -> None:
    controls = auth()["required_implementation_controls"]

    for key in (
        "fail_if_mtg_head_differs",
        "fail_if_sidecar_sha256_differs",
        "fail_if_sidecar_row_count_differs",
        "fail_if_sidecar_field_count_differs",
        "fail_if_duplicate_mtg_asset_id_exists",
        "fail_if_duplicate_secret_lair_id_exists",
        "fail_if_existing_23_field_interface_changes",
        "fail_if_projection_recalculates_values",
        "fail_if_projection_synthesizes_missing_values",
        "fail_if_3y_or_5y_is_labeled_direct_forecast",
        "fail_if_q25_or_q50_replaces_q10_policy",
        "fail_if_automatic_execution_is_enabled",
    ):
        assert controls[key] is True


def test_next_gate_is_bounded_projection_implementation() -> None:
    assert (
        auth()["next_gate"]
        == (
            "IMPLEMENT_BOUNDED_UIP_PREMIUM_SIDECAR_"
            "ACCEPTANCE_AND_PRESENTATION_PROJECTION"
        )
    )
