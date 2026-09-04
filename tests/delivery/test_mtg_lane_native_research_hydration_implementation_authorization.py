from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_lane_native_research_hydration_implementation_authorization_v1.json"
)


def auth() -> dict:
    return json.loads(PATH.read_text(encoding="utf-8"))


def test_identity_and_status() -> None:
    value = auth()

    assert (
        value["authorization_id"]
        == "UIP_MTG_LANE_NATIVE_RESEARCH_HYDRATION_IMPLEMENTATION_AUTHORIZATION_V1"
    )

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_PRESENTATION_PROJECTION_AND_WIRING_IMPLEMENTATION"
    )


def test_four_lane_native_record_types_are_exact() -> None:
    data = auth()["certified_datasets"]

    assert (
        data["collector_product"]["record_type"]
        == "mtg_collector_research"
    )

    assert (
        data["collector_horizon"]["record_type"]
        == "mtg_collector_forecast_horizon"
    )

    assert (
        data["precollector_product"]["record_type"]
        == "mtg_precollector_research"
    )

    assert (
        data["precollector_scenario"]["record_type"]
        == "mtg_precollector_scenario_horizon"
    )


def test_asset_identity_rules_are_lane_native() -> None:
    data = auth()["certified_datasets"]

    assert (
        data["collector_product"]["asset_id_rule"]
        == "COLLECTOR_V1|{canonical_product_id}"
    )

    assert (
        data["collector_horizon"]["asset_id_rule"]
        == "COLLECTOR_V1|{canonical_product_id}"
    )

    assert (
        data["precollector_product"]["asset_id_rule"]
        == "PRE_COLLECTOR_V1|{canonical_product_id}"
    )

    assert (
        data["precollector_scenario"]["asset_id_rule"]
        == "PRE_COLLECTOR_V1|{canonical_product_id}"
    )


def test_population_contract_is_exact() -> None:
    data = auth()["certified_datasets"]

    assert data["collector_product"]["row_count"] == 50
    assert data["collector_horizon"]["row_count"] == 294

    assert data["precollector_product"]["row_count"] == 131
    assert data["precollector_scenario"]["row_count"] == 190


def test_generic_asset_detail_requires_no_new_endpoint() -> None:
    architecture = auth()["architecture"]

    assert architecture["use_existing_presentation_records_table"] is True
    assert architecture["use_existing_generic_asset_detail_endpoint"] is True

    assert (
        architecture["generic_asset_detail_endpoint"]
        == "/v1/presentation/assets/{domain_id}/{asset_id}"
    )

    assert architecture["create_new_http_endpoint"] is False
    assert architecture["modify_read_api"] is False
    assert architecture["modify_http_service"] is False


def test_secret_lair_specialized_projection_remains_separate() -> None:
    architecture = auth()["architecture"]

    assert (
        architecture["modify_specialized_mtg_premium_research_method"]
        is False
    )

    assert (
        architecture[
            "specialized_mtg_premium_research_remains_secret_lair_specific"
        ]
        is True
    )


def test_runtime_scope_is_exactly_four_files() -> None:
    value = auth()

    assert value["authorized_runtime_files"] == [
        "foundation/presentation/mtg_lane_native_research_projection.py",
        "foundation/presentation/publication_model.py",
        "tests/delivery/test_mtg_lane_native_research_projection.py",
        "tests/delivery/test_mtg_lane_native_research_publication_wiring.py",
    ]


def test_sidecar_wiring_is_explicit_and_fail_closed() -> None:
    wiring = auth()["required_publication_wiring"]

    assert wiring["external_paths_must_be_explicit"] is True
    assert wiring["filesystem_discovery_authorized"] is False
    assert wiring["implicit_repository_search_authorized"] is False
    assert wiring["copy_sidecars_into_uip_authorized"] is False

    assert (
        wiring["present_invalid_sidecar_behavior"]
        == "FAIL_CLOSED"
    )


def test_semantics_remain_lane_native() -> None:
    guards = set(auth()["semantic_guardrails"])

    for required in {
        "COMMON_23_FIELD_NATIVE_AUTHORITY_REMAINS_AUTHORITATIVE",
        "SIDECARS_SUPPLEMENT_BUT_DO_NOT_OVERRIDE_NATIVE_AUTHORITY",
        "LOTR_CURRENT_PRICE_ONLY_ASSET_REMAINS_UNRANKED",
        "3Y_AND_5Y_PRECOLLECTOR_VALUES_REMAIN_SCENARIOS_NOT_DIRECT_FORECASTS",
        "MISSING_VALUES_REMAIN_MISSING",
        "NO_SECRET_LAIR_Q10_POLICY_REUSE",
        "NO_CRYPTO_BEAR_BASE_BULL_MAPPING",
        "NO_CROSS_LANE_SCORE",
        "NO_UNIVERSAL_MTG_RANK",
        "NO_AUTOMATIC_PURCHASE_EXECUTION",
    }:
        assert required in guards


def test_downstream_boundaries_remain_closed() -> None:
    boundary = auth()["authorization_boundary"]

    assert boundary["runtime_projection_implementation_authorized"] is True
    assert boundary["local_non_active_publication_validation_authorized"] is True

    for key, value in boundary.items():
        if key in {
            "runtime_projection_implementation_authorized",
            "local_non_active_publication_validation_authorized",
        }:
            continue

        assert value is False


def test_next_gate_is_projection_implementation() -> None:
    assert (
        auth()["next_gate"]
        == "IMPLEMENT_AND_CERTIFY_BOUNDED_MTG_LANE_NATIVE_RESEARCH_PRESENTATION_PROJECTION"
    )