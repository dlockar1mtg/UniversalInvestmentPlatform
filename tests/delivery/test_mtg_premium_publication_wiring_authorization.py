from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_publication_wiring_authorization_v1.json"
)


def authorization() -> dict:
    return json.loads(
        PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_identity_and_status() -> None:
    value = authorization()

    assert (
        value["authorization_id"]
        == "UIP_MTG_PREMIUM_PUBLICATION_WIRING_AUTHORIZATION_V1"
    )

    assert value["authorization_version"] == "1.0.0"

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_STAGED_PUBLICATION_WIRING_IMPLEMENTATION"
    )


def test_exact_certified_authorities_are_bound() -> None:
    value = authorization()

    source = value["certified_mtg_authority"]

    assert (
        source["head"]
        == "6b610b208549bec4be2c0ec7f7f3c2f69b154302"
    )

    assert (
        source["sidecar_sha256"]
        == "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333"
    )

    assert source["sidecar_row_count"] == 787
    assert source["sidecar_field_count"] == 36

    projector = value["certified_projector"]

    assert (
        projector["module"]
        == "foundation.presentation.mtg_premium_projection"
    )

    assert (
        projector["builder"]
        == "build_mtg_premium_records"
    )

    assert (
        projector["record_type"]
        == "mtg_premium_research"
    )

    assert projector["expected_record_count"] == 787


def test_external_path_must_be_explicit() -> None:
    wiring = authorization()["authorized_wiring_behavior"]

    assert (
        wiring["external_path_environment_variable"]
        == "UIP_MTG_PREMIUM_SIDECAR_PATH"
    )

    assert wiring["filesystem_discovery_authorized"] is False

    assert (
        wiring["implicit_repository_search_authorized"]
        is False
    )

    assert (
        wiring["sidecar_copy_into_uip_authorized"]
        is False
    )

    assert (
        wiring["environment_variable_absent_behavior"]
        == "PRESERVE_EXISTING_PUBLICATION_WITHOUT_PREMIUM_RECORDS"
    )

    assert (
        wiring["environment_variable_present_behavior"]
        == "VALIDATE_EXACT_CERTIFIED_SIDECAR_AND_PROJECT"
    )

    assert (
        wiring["invalid_present_path_behavior"]
        == "FAIL_CLOSED"
    )


def test_only_staged_publication_append_is_authorized() -> None:
    wiring = authorization()["authorized_wiring_behavior"]

    assert (
        wiring[
            "premium_records_may_be_appended_to_staged_publication"
        ]
        is True
    )

    assert (
        wiring["publication_status_must_remain_staged"]
        is True
    )

    assert (
        wiring["existing_mtg_native_records_must_remain_present"]
        is True
    )

    assert (
        wiring["existing_mtg_native_records_mutable"]
        is False
    )

    assert wiring["generic_forecast_records_mutable"] is False
    assert wiring["generic_risk_records_mutable"] is False
    assert wiring["native_authority_records_mutable"] is False


def test_semantics_remain_lane_native() -> None:
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


def test_only_wiring_code_and_tests_are_authorized() -> None:
    scope = authorization()["implementation_scope"]

    assert (
        scope[
            "modify_publication_model_for_bounded_wiring_authorized"
        ]
        is True
    )

    assert (
        scope[
            "add_bounded_publication_wiring_tests_authorized"
        ]
        is True
    )

    forbidden = (
        "copy_sidecar_into_uip_repository_authorized",
        "copy_sidecar_into_delivery_package_authorized",
        "analytical_database_ingestion_authorized",
        "analytical_database_schema_change_authorized",
        "presentation_postgres_write_authorized",
        "live_publication_activation_authorized",
        "read_api_change_authorized",
        "frontend_change_authorized",
        "collector_premium_wiring_authorized",
        "precollector_premium_wiring_authorized",
        "secret_lair_partial_206_promotion_authorized",
        "model_execution_authorized",
        "model_retraining_authorized",
        "automatic_purchase_execution_authorized",
    )

    for key in forbidden:
        assert scope[key] is False


def test_implementation_controls_fail_closed() -> None:
    controls = authorization()[
        "required_implementation_controls"
    ]

    required = (
        "fail_if_existing_native_mtg_projection_changes",
        "fail_if_external_path_is_present_but_invalid",
        "fail_if_sidecar_sha256_differs",
        "fail_if_sidecar_schema_differs",
        "fail_if_sidecar_population_differs",
        "fail_if_projected_record_count_differs",
        "fail_if_projected_record_type_differs",
        "fail_if_projected_payload_differs_from_certified_sidecar",
        "prove_no_premium_records_when_environment_variable_absent",
        "prove_787_premium_records_when_environment_variable_present",
        "prove_existing_publication_record_counts_are_preserved_plus_787",
        "prove_publication_status_remains_staged",
        "prove_no_database_mutation",
        "prove_no_sidecar_copy",
        "prove_no_live_activation",
        "prove_no_frontend_change",
    )

    for key in required:
        assert controls[key] is True


def test_next_gate_is_bounded_wiring_implementation() -> None:
    assert (
        authorization()["next_gate"]
        == (
            "IMPLEMENT_AND_CERTIFY_BOUNDED_MTG_PREMIUM_"
            "STAGED_PUBLICATION_WIRING"
        )
    )
