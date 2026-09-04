from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_live_read_api_validation_read_only_recovery_v1.json"
)


def recovery() -> dict:
    return json.loads(
        PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_identity_and_status() -> None:
    value = recovery()

    assert (
        value["recovery_authorization_id"]
        == "UIP_MTG_PREMIUM_LIVE_READ_API_VALIDATION_READ_ONLY_RECOVERY_V1"
    )

    assert value["recovery_version"] == "1.0.0"

    assert (
        value["status"]
        == "AUTHORIZED_FOR_SERVER_ENFORCED_TRANSACTION_READ_ONLY_RETRY"
    )


def test_failure_occurred_before_live_validation() -> None:
    failed = recovery()["failed_execution"]

    assert failed["step"] == "STEP_14L_D"

    assert (
        failed["failure_class"]
        == "NEON_POOLED_CONNECTION_STARTUP_PARAMETER_UNSUPPORTED"
    )

    assert failed["failed_before_successful_postgres_connection"] is True
    assert failed["failed_before_live_database_select"] is True
    assert failed["failed_before_repository_live_projection"] is True
    assert failed["failed_before_fastapi_live_route_validation"] is True


def test_failure_performed_no_mutation() -> None:
    failed = recovery()["failed_execution"]

    assert failed["postgres_write_attempted"] is False
    assert failed["presentation_activation_attempted"] is False
    assert failed["active_pointer_mutation_attempted"] is False


def test_startup_parameter_mechanism_is_retired() -> None:
    constraint = recovery()["observed_connection_constraint"]

    assert constraint["provider"] == "NEON"
    assert constraint["connection_mode"] == "POOLED"

    assert (
        constraint["unsupported_startup_parameter"]
        == "default_transaction_read_only"
    )

    assert (
        constraint["startup_options_read_only_mechanism_authorized"]
        is False
    )


def test_transaction_read_only_is_required() -> None:
    mechanism = recovery()[
        "authorized_replacement_read_only_mechanism"
    ]

    assert (
        mechanism[
            "connect_using_existing_pooled_dsn_without_startup_options"
        ]
        is True
    )

    assert (
        mechanism[
            "execute_set_transaction_read_only_immediately_after_connection"
        ]
        is True
    )

    assert (
        mechanism[
            "set_transaction_read_only_must_precede_application_selects"
        ]
        is True
    )

    assert (
        mechanism[
            "verify_show_transaction_read_only_equals_on"
        ]
        is True
    )

    assert (
        mechanism[
            "server_enforced_transaction_read_only_required"
        ]
        is True
    )


def test_read_only_must_apply_to_every_repository_connection() -> None:
    mechanism = recovery()[
        "authorized_replacement_read_only_mechanism"
    ]

    behavior = recovery()[
        "required_connection_factory_behavior"
    ]

    assert (
        mechanism[
            "apply_to_every_connection_created_by_repository_or_route"
        ]
        is True
    )

    assert (
        behavior[
            "connection_factory_must_return_connection_with_current_transaction_read_only"
        ]
        is True
    )

    assert (
        behavior[
            "connection_factory_may_not_execute_application_data_select_before_read_only_is_enabled"
        ]
        is True
    )

    assert behavior["repository_from_dsn_method_must_not_be_used"] is True


def test_default_transaction_setting_is_not_required() -> None:
    mechanism = recovery()[
        "authorized_replacement_read_only_mechanism"
    ]

    assert (
        mechanism[
            "default_transaction_read_only_equals_on_not_required"
        ]
        is True
    )


def test_original_semantic_and_population_checks_remain_required() -> None:
    original = recovery()[
        "all_original_validation_requirements_preserved"
    ]

    for key in (
        "exact_active_publication_validation",
        "exact_active_fingerprint_validation",
        "active_record_count_13264",
        "live_premium_record_count_787",
        "live_premium_unique_asset_id_count_787",
        "deterministic_premium_asset_selection",
        "repository_lossless_payload_validation",
        "fastapi_lossless_payload_validation",
        "missing_premium_authority_remains_missing",
        "q10_semantics_preserved",
        "one_year_certified_semantics_preserved",
        "three_year_values_remain_scenarios",
        "five_year_values_remain_scenarios",
        "universal_mtg_rank_not_created",
        "cross_domain_rank_not_created",
        "automatic_purchase_execution_not_authorized",
    ):
        assert original[key] is True


def test_mutating_surfaces_remain_forbidden() -> None:
    forbidden = recovery()["explicitly_forbidden"]

    for key in (
        "postgres_insert",
        "postgres_update",
        "postgres_delete",
        "postgres_schema_change",
        "presentation_stage",
        "presentation_activate",
        "active_pointer_mutation",
        "read_api_code_change",
        "frontend_change",
        "analytical_database_change",
        "mtg_source_change",
        "premium_sidecar_change",
        "model_execution",
        "model_retraining",
        "automatic_purchase_execution",
    ):
        assert forbidden[key] is True


def test_retry_scope_is_bounded() -> None:
    scope = recovery()["retry_scope"]

    assert scope["step_14l_d_retry_authorized"] is True

    assert (
        scope["retry_must_use_transaction_read_only_mechanism"]
        is True
    )

    assert scope["hosted_external_api_request_authorized"] is False
    assert scope["frontend_integration_authorized"] is False
