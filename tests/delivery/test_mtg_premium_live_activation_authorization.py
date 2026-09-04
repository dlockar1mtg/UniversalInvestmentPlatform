from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_live_activation_authorization_v1.json"
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
        == "UIP_MTG_PREMIUM_LIVE_PRESENTATION_ACTIVATION_AUTHORIZATION_V1"
    )

    assert value["authorization_version"] == "1.0.0"

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_LIVE_PRESENTATION_ACTIVATION_EXECUTION"
    )


def test_exact_uip_and_mtg_authorities() -> None:
    value = auth()

    assert (
        value["governing_uip_checkpoint"]["required_parent_head"]
        == "05ab096c4ce3974b00a7e7684c8240cc2449b99d"
    )

    assert (
        value["certified_mtg_authority"]["head"]
        == "6b610b208549bec4be2c0ec7f7f3c2f69b154302"
    )

    assert (
        value["certified_mtg_authority"]["premium_sidecar_sha256"]
        == "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333"
    )

    assert value["certified_mtg_authority"]["premium_row_count"] == 787


def test_exact_staged_publication_is_bound() -> None:
    staged = auth()["certified_staged_publication"]

    assert (
        staged["publication_id"]
        == "mtg-premium-stage-rehearsal-ac8adb415f03"
    )

    assert (
        staged["required_status_before_activation"]
        == "STAGED"
    )

    assert (
        staged["content_fingerprint"]
        == "4a67d16878f0cdb5077b98aa13bd44276f1a993ce2a2b045f52a1ebefe633154"
    )

    assert staged["record_count"] == 13264
    assert staged["mtg_premium_research_record_count"] == 787
    assert staged["mtg_premium_unique_asset_id_count"] == 787


def test_pre_activation_validation_is_strict() -> None:
    pre = auth()["required_pre_activation_validation"]

    required_true = (
        "capture_current_active_publication_immediately_before_activation",
        "require_exactly_one_active_pointer",
        "require_current_active_status_active",
        "require_staged_publication_exists",
        "require_staged_publication_status_staged",
        "require_staged_fingerprint_exact_match",
        "require_staged_record_count_13264",
        "require_787_premium_records",
        "require_787_unique_premium_asset_ids",
        "require_lossless_premium_payload_readback",
        "require_q10_semantics_present",
        "require_three_year_scenario_semantics_present",
        "require_five_year_scenario_semantics_present",
        "require_automatic_execution_surface_absent",
    )

    for key in required_true:
        assert pre[key] is True


def test_only_exact_activate_call_is_authorized() -> None:
    behavior = auth()["authorized_activation_behavior"]

    assert (
        behavior["postgres_repository_class"]
        == "PostgresPresentationRepository"
    )

    assert behavior["activation_method"] == "activate"

    assert (
        behavior["activate_exact_certified_staged_publication_once"]
        is True
    )


def test_post_activation_must_reconcile_exactly() -> None:
    post = auth()["required_post_activation_validation"]

    for key in (
        "target_publication_must_be_active",
        "target_publication_must_be_active_pointer",
        "target_fingerprint_must_remain_exact",
        "target_record_count_must_remain_13264",
        "premium_record_count_must_remain_787",
        "premium_unique_asset_count_must_remain_787",
        "premium_payload_readback_must_remain_lossless",
        "previous_active_publication_must_remain_present",
        "previous_active_publication_must_be_superseded",
        "exactly_one_active_pointer_required",
        "exactly_one_active_publication_required",
    ):
        assert post[key] is True


def test_no_automatic_retry_or_fallback() -> None:
    recovery = auth()["failure_and_recovery_controls"]

    assert recovery["do_not_activate_if_any_precheck_fails"] is True

    assert (
        recovery["automatic_second_activation_attempt_authorized"]
        is False
    )

    assert (
        recovery["automatic_fallback_activation_authorized"]
        is False
    )

    assert (
        recovery["manual_recovery_requires_separate_governed_decision"]
        is True
    )


def test_mtg_semantics_remain_native() -> None:
    semantic = auth()["semantic_constraints"]

    assert semantic["one_year_direct_certified_semantics_preserved"] is True
    assert semantic["q10_is_governed_purchase_threshold"] is True

    assert semantic["q25_may_replace_q10"] is False
    assert semantic["q50_may_replace_q10"] is False

    assert semantic["three_year_values_are_scenarios"] is True
    assert semantic["five_year_values_are_scenarios"] is True

    assert (
        semantic["three_year_values_are_direct_certified_forecasts"]
        is False
    )

    assert (
        semantic["five_year_values_are_direct_certified_forecasts"]
        is False
    )

    assert semantic["three_year_values_may_trigger_purchase"] is False
    assert semantic["five_year_values_may_trigger_purchase"] is False
    assert semantic["rank_may_override_purchase_threshold"] is False

    assert (
        semantic["automatic_purchase_execution_authorized"]
        is False
    )


def test_sensitive_expansions_remain_forbidden() -> None:
    forbidden = auth()["explicitly_forbidden"]

    for key in (
        "rebuild_staged_publication",
        "modify_staged_payloads",
        "modify_analytical_database",
        "modify_mtg_source_repository",
        "modify_mtg_premium_sidecar",
        "model_execution",
        "model_retraining",
        "read_api_code_change",
        "frontend_code_change",
        "collector_lane_expansion",
        "precollector_lane_expansion",
        "partial_secret_lair_population_expansion",
        "automatic_purchase_execution",
    ):
        assert forbidden[key] is True


def test_api_and_frontend_are_not_yet_authorized() -> None:
    scope = auth()["activation_scope"]

    assert (
        scope["postgres_activation_execution_authorized_next"]
        is True
    )

    assert (
        scope["read_api_validation_after_activation_authorized"]
        is False
    )

    assert scope["read_api_code_change_authorized"] is False
    assert scope["frontend_change_authorized"] is False

    assert (
        scope["next_gate_after_successful_activation"]
        == "CONSIDER_BOUNDED_MTG_PREMIUM_READ_API_VALIDATION_AUTHORIZATION"
    )
