from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_read_api_projection_repair_authorization_v1.json"
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
        == "UIP_MTG_PREMIUM_READ_API_PROJECTION_REPAIR_AUTHORIZATION_V1"
    )

    assert value["authorization_version"] == "1.0.0"

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_READ_API_PREMIUM_PROJECTION_REPAIR"
    )


def test_exact_live_presentation_is_bound() -> None:
    live = auth()["certified_live_presentation"]

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

    assert (
        live["mtg_premium_research_record_count"]
        == 787
    )

    assert live["premium_payload_state"] == "LOSSLESS"


def test_gap_is_precisely_classified() -> None:
    gap = auth()["observed_read_api_gap"]

    assert gap["generic_asset_detail_reads_all_record_types"] is True

    assert (
        gap["specialized_endpoint"]
        == "/v1/presentation/mtg-research/{asset_id}"
    )

    assert (
        gap["specialized_repository_method"]
        == "PresentationReadRepository.mtg_premium_research"
    )

    assert (
        gap["specialized_method_currently_extracts_mtg_premium_research"]
        is False
    )

    assert (
        gap["gap_classification"]
        == "LIVE_RECORD_TYPE_NOT_PROJECTED_BY_SPECIALIZED_MTG_ENDPOINT"
    )


def test_repair_scope_is_bounded() -> None:
    scope = auth()["authorized_implementation_scope"]

    assert scope["read_api_source_change_authorized"] is True

    assert (
        scope["allowed_file"]
        == "foundation/presentation/read_api.py"
    )

    assert (
        scope["allow_extract_mtg_premium_research_record_type"]
        is True
    )

    assert (
        scope["allow_return_premium_payload_in_existing_mtg_research_response"]
        is True
    )

    assert scope["new_endpoint_required"] is False
    assert scope["existing_endpoint_may_be_extended"] is True


def test_semantics_remain_lane_native() -> None:
    semantic = auth()["required_projection_semantics"]

    assert semantic["premium_payload_must_be_lossless"] is True

    assert (
        semantic["one_year_direct_certified_semantics_preserved"]
        is True
    )

    assert semantic["q10_is_governed_purchase_threshold"] is True

    assert semantic["q25_may_replace_q10"] is False
    assert semantic["q50_may_replace_q10"] is False

    assert semantic["three_year_values_remain_scenarios"] is True
    assert semantic["five_year_values_remain_scenarios"] is True

    assert semantic["three_year_values_may_trigger_purchase"] is False
    assert semantic["five_year_values_may_trigger_purchase"] is False

    assert (
        semantic["native_rank_may_override_purchase_threshold"]
        is False
    )

    assert semantic["cross_domain_rank_may_be_created"] is False
    assert semantic["universal_mtg_rank_may_be_created"] is False

    assert (
        semantic["automatic_purchase_execution_authorized"]
        is False
    )


def test_missing_premium_must_not_be_synthesized() -> None:
    semantic = auth()["required_projection_semantics"]
    behavior = auth()["required_behavior_after_repair"]

    assert (
        semantic["missing_premium_authority_must_remain_missing"]
        is True
    )

    assert (
        behavior[
            "asset_without_premium_record_does_not_receive_synthesized_premium_payload"
        ]
        is True
    )


def test_expected_premium_projection_behavior() -> None:
    behavior = auth()["required_behavior_after_repair"]

    assert (
        behavior[
            "secret_lair_full_asset_with_live_premium_record_returns_premium_research"
        ]
        is True
    )

    assert (
        behavior["premium_record_count_for_full_asset_is_one"]
        is True
    )

    assert (
        behavior["premium_payload_preserves_source_lineage_fields"]
        is True
    )

    assert behavior["premium_payload_preserves_q10_fields"] is True
    assert behavior["premium_payload_preserves_1y_fields"] is True

    assert (
        behavior["premium_payload_preserves_3y_scenario_fields"]
        is True
    )

    assert (
        behavior["premium_payload_preserves_5y_scenario_fields"]
        is True
    )


def test_other_mtg_lanes_remain_frozen() -> None:
    behavior = auth()["required_behavior_after_repair"]

    assert behavior["precollector_remains_blocked"] is True

    assert (
        behavior["collector_identity_bridge_state_remains_unchanged"]
        is True
    )


def test_sensitive_surfaces_are_forbidden() -> None:
    forbidden = auth()["explicitly_forbidden"]

    for key in (
        "postgres_write",
        "presentation_activation",
        "active_pointer_mutation",
        "publication_rebuild",
        "publication_record_mutation",
        "analytical_database_change",
        "mtg_source_repository_change",
        "mtg_sidecar_change",
        "model_execution",
        "model_retraining",
        "frontend_change",
        "collector_lane_expansion",
        "precollector_lane_expansion",
        "partial_secret_lair_population_expansion",
        "automatic_purchase_execution",
    ):
        assert forbidden[key] is True


def test_live_validation_is_still_separate_gate() -> None:
    gate = auth()["next_gate_after_implementation"]

    assert gate["run_unit_and_regression_tests"] is True
    assert gate["commit_and_push_bounded_read_api_repair"] is True

    assert (
        gate["live_read_api_validation_authorized_by_this_document"]
        is False
    )

    assert (
        gate["next_gate"]
        == "CONSIDER_BOUNDED_LIVE_MTG_PREMIUM_READ_API_VALIDATION_AUTHORIZATION"
    )
