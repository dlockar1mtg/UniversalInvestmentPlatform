from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_staged_persistence_rehearsal_authorization_v1.json"
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
        == "UIP_MTG_PREMIUM_STAGED_PERSISTENCE_REHEARSAL_AUTHORIZATION_V1"
    )

    assert value["authorization_version"] == "1.0.0"

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_NON_ACTIVE_PRESENTATION_PERSISTENCE_REHEARSAL"
    )


def test_exact_governed_authorities_are_bound() -> None:
    value = auth()

    assert (
        value["governing_uip_checkpoint"]["required_parent_head"]
        == "e1931c807ef4ab86250eff953465cdb4700f23e5"
    )

    source = value["certified_mtg_authority"]

    assert (
        source["head"]
        == "6b610b208549bec4be2c0ec7f7f3c2f69b154302"
    )

    assert (
        source["sidecar_sha256"]
        == "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333"
    )

    assert source["premium_record_count"] == 787
    assert source["premium_record_type"] == "mtg_premium_research"


def test_publication_must_remain_staged() -> None:
    value = auth()

    wiring = value["certified_publication_wiring"]

    assert wiring["publication_status"] == "STAGED"
    assert wiring["premium_records_appended"] == 787
    assert wiring["non_premium_records_preserved"] is True

    behavior = value["authorized_rehearsal_behavior"]

    assert (
        behavior["rehearsal_publication_must_remain_staged"]
        is True
    )


def test_staging_and_activation_are_separate() -> None:
    store = auth()["presentation_store"]

    assert store["staging_method"] == "stage"
    assert store["staged_validation_method"] == "validate_staged"
    assert store["activation_method"] == "activate"

    assert (
        store["active_pointer_table"]
        == "presentation_active_publication"
    )


def test_only_non_active_persistence_is_authorized() -> None:
    behavior = auth()["authorized_rehearsal_behavior"]

    assert (
        behavior[
            "connect_to_explicit_presentation_postgres_authorized"
        ]
        is True
    )

    assert (
        behavior["create_one_new_staged_publication_authorized"]
        is True
    )

    assert (
        behavior["persist_presentation_records_authorized"]
        is True
    )

    assert (
        behavior["validate_staged_publication_authorized"]
        is True
    )

    assert (
        behavior["read_back_staged_records_authorized"]
        is True
    )


def test_active_pointer_mutation_is_forbidden() -> None:
    forbidden = auth()["explicitly_forbidden"]

    for key in (
        "activate_rehearsal_publication",
        "call_activate_method",
        "update_active_publication_pointer",
        "supersede_current_active_publication",
        "live_publication_activation",
    ):
        assert forbidden[key] is True


def test_other_sensitive_surfaces_remain_forbidden() -> None:
    forbidden = auth()["explicitly_forbidden"]

    for key in (
        "modify_analytical_database",
        "modify_analytical_schema",
        "modify_mtg_source_repository",
        "modify_mtg_sidecar",
        "read_api_change",
        "frontend_change",
        "model_execution",
        "model_retraining",
        "automatic_purchase_execution",
    ):
        assert forbidden[key] is True


def test_rehearsal_must_prove_787_lossless_records() -> None:
    behavior = auth()["authorized_rehearsal_behavior"]

    assert (
        behavior["require_787_mtg_premium_research_records"]
        is True
    )

    assert (
        behavior["require_787_unique_premium_asset_ids"]
        is True
    )

    assert behavior["require_lossless_premium_payloads"] is True


def test_active_pointer_must_be_identical_before_after() -> None:
    behavior = auth()["authorized_rehearsal_behavior"]

    assert (
        behavior["capture_active_publication_before_rehearsal"]
        is True
    )

    assert (
        behavior["capture_active_publication_after_rehearsal"]
        is True
    )

    assert behavior["require_active_pointer_unchanged"] is True


def test_cleanup_does_not_activate_or_delete() -> None:
    cleanup = auth()["rehearsal_cleanup_policy"]

    assert cleanup["automatic_activation_after_success"] is False

    assert (
        cleanup[
            "rehearsal_publication_may_remain_staged_for_inspection"
        ]
        is True
    )

    assert cleanup["deletion_authorized_in_this_contract"] is False


def test_next_gate() -> None:
    assert (
        auth()["next_gate"]
        == (
            "IMPLEMENT_AND_EXECUTE_BOUNDED_NON_ACTIVE_MTG_PREMIUM_"
            "PRESENTATION_PERSISTENCE_REHEARSAL"
        )
    )
