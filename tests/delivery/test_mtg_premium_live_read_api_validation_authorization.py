from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_live_read_api_validation_authorization_v1.json"
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
        == "UIP_MTG_PREMIUM_LIVE_READ_API_VALIDATION_AUTHORIZATION_V1"
    )

    assert value["authorization_version"] == "1.0.0"

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_READ_ONLY_ACTIVE_PUBLICATION_API_VALIDATION"
    )


def test_exact_read_api_checkpoint_is_bound() -> None:
    api = auth()["certified_read_api_implementation"]

    assert (
        api["implementation_checkpoint"]
        == "a5b3f3c58bd545b17845607024d6ff18b0133b81"
    )

    assert (
        api["repository_method"]
        == "mtg_premium_research"
    )

    assert (
        api["endpoint"]
        == "/v1/presentation/mtg-research/{asset_id}"
    )

    assert api["premium_response_field"] == "premium_research"


def test_exact_active_publication_is_bound() -> None:
    live = auth()["certified_active_publication"]

    assert (
        live["publication_id"]
        == "mtg-premium-stage-rehearsal-ac8adb415f03"
    )

    assert live["publication_status"] == "ACTIVE"

    assert (
        live["content_fingerprint"]
        == "4a67d16878f0cdb5077b98aa13bd44276f1a993ce2a2b045f52a1ebefe633154"
    )

    assert live["record_count"] == 13264
    assert live["mtg_premium_research_record_count"] == 787
    assert live["mtg_premium_unique_asset_id_count"] == 787


def test_validation_is_server_enforced_read_only() -> None:
    mode = auth()["authorized_validation_mode"]

    assert mode["postgres_connection_authorized"] is True

    assert (
        mode["postgres_default_transaction_read_only_required"]
        is True
    )

    assert mode["postgres_select_only_required"] is True
    assert mode["postgres_write_authorized"] is False

    assert (
        mode["presentation_activation_authorized"]
        is False
    )

    assert (
        mode["active_pointer_mutation_authorized"]
        is False
    )


def test_asset_selection_is_deterministic_and_certified() -> None:
    selection = auth()["authorized_test_asset_selection"]

    assert selection["selection_source"] == "CERTIFIED_PREMIUM_SIDECAR"

    assert (
        selection["selection_rule"]
        == (
            "LEXICOGRAPHICALLY_FIRST_MTG_ASSET_ID_AFTER_EXACT_"
            "SIDECAR_SHA_AND_COUNT_VALIDATION"
        )
    )

    assert (
        selection["selected_asset_must_exist_in_live_premium_population"]
        is True
    )


def test_repository_projection_must_be_lossless() -> None:
    required = auth()["required_repository_validation"]

    assert required["call_mtg_premium_research_for_selected_live_asset"] is True

    assert required["require_premium_research_record_count_one"] is True

    assert (
        required["require_premium_payload_exactly_equals_certified_sidecar_row"]
        is True
    )

    assert required["require_q10_fields_preserved"] is True

    assert (
        required["require_three_year_scenario_field_names_preserved"]
        is True
    )

    assert (
        required["require_five_year_scenario_field_names_preserved"]
        is True
    )


def test_existing_http_route_must_project_same_live_payload() -> None:
    required = auth()["required_http_route_validation"]

    assert required["install_existing_routes_in_local_fastapi_application"] is True

    assert required["use_same_live_read_only_repository"] is True

    assert required["use_ephemeral_in_memory_test_credential"] is True

    assert required["request_existing_mtg_research_endpoint"] is True

    assert required["require_http_200"] is True

    assert (
        required["require_response_premium_payload_exactly_equals_certified_sidecar_row"]
        is True
    )


def test_missing_premium_authority_must_remain_missing() -> None:
    required = auth()["required_missing_authority_validation"]

    assert (
        required["select_one_live_mtg_asset_without_mtg_premium_research_record"]
        is True
    )

    assert required["require_asset_still_resolves"] is True
    assert required["require_premium_research_is_null"] is True

    assert (
        required["require_premium_research_record_count_zero"]
        is True
    )

    assert required["synthesize_missing_premium_authority"] is False


def test_lane_native_semantics_remain_locked() -> None:
    semantic = auth()["semantic_constraints"]

    assert semantic["q10_is_governed_purchase_threshold"] is True

    assert semantic["q25_may_replace_q10"] is False
    assert semantic["q50_may_replace_q10"] is False

    assert semantic["three_year_values_are_scenarios"] is True
    assert semantic["five_year_values_are_scenarios"] is True

    assert semantic["three_year_values_may_trigger_purchase"] is False
    assert semantic["five_year_values_may_trigger_purchase"] is False

    assert semantic["cross_domain_rank_may_be_created"] is False
    assert semantic["universal_mtg_rank_may_be_created"] is False

    assert (
        semantic["automatic_purchase_execution_authorized"]
        is False
    )


def test_mutating_and_frontend_surfaces_remain_forbidden() -> None:
    forbidden = auth()["explicitly_forbidden"]

    for key in (
        "postgres_insert",
        "postgres_update",
        "postgres_delete",
        "postgres_schema_change",
        "presentation_stage",
        "presentation_activate",
        "active_pointer_mutation",
        "analytical_database_change",
        "mtg_source_repository_change",
        "premium_sidecar_change",
        "read_api_code_change",
        "frontend_change",
        "model_execution",
        "model_retraining",
        "collector_lane_expansion",
        "precollector_lane_expansion",
        "partial_secret_lair_population_expansion",
        "automatic_purchase_execution",
    ):
        assert forbidden[key] is True


def test_frontend_remains_separate_gate() -> None:
    gate = auth()["next_gate_after_successful_validation"]

    assert gate["live_validation_evidence_must_be_certified"] is True

    assert (
        gate["frontend_change_authorized_by_this_document"]
        is False
    )

    assert (
        gate["hosted_deployment_change_authorized_by_this_document"]
        is False
    )

    assert (
        gate["next_gate"]
        == "CONSIDER_BOUNDED_MTG_PREMIUM_FRONTEND_INTEGRATION_AUTHORIZATION"
    )
