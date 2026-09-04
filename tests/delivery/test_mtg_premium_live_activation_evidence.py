from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

EVIDENCE_PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_live_activation_evidence_v1.json"
)


def evidence() -> dict:
    return json.loads(
        EVIDENCE_PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_identity_and_certification() -> None:
    value = evidence()

    assert (
        value["evidence_id"]
        == "UIP_MTG_PREMIUM_LIVE_PRESENTATION_ACTIVATION_EVIDENCE_V1"
    )

    assert value["evidence_version"] == "1.0.0"
    assert value["certification_state"] == "PASS"
    assert value["execution_step"] == "STEP_14K_A"


def test_exact_authorities() -> None:
    source = evidence()["certified_sources"]

    assert (
        source["uip_head"]
        == "9bc82954e29f73ce5b8605a8ccfc50cffa5b5603"
    )

    assert (
        source["mtg_head"]
        == "6b610b208549bec4be2c0ec7f7f3c2f69b154302"
    )

    assert (
        source["analytical_database_sha256"]
        == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    )

    assert (
        source["premium_sidecar_sha256"]
        == "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333"
    )

    assert source["premium_sidecar_row_count"] == 787


def test_pre_activation_target_was_exact() -> None:
    pre = evidence()["pre_activation_certification"]

    assert pre["validation_state"] == "PASS"

    assert (
        pre["target_publication_id"]
        == "mtg-premium-stage-rehearsal-ac8adb415f03"
    )

    assert pre["target_status"] == "STAGED"

    assert (
        pre["target_content_fingerprint"]
        == "4a67d16878f0cdb5077b98aa13bd44276f1a993ce2a2b045f52a1ebefe633154"
    )

    assert pre["target_record_count"] == 13264
    assert pre["premium_record_count"] == 787
    assert pre["premium_payload_readback"] == "LOSSLESS"
    assert pre["store_validate_staged"] == "PASS"


def test_native_asset_counts_remained_exact() -> None:
    counts = evidence()[
        "pre_activation_certification"
    ]["asset_counts"]

    assert counts == {
        "crypto": 6,
        "metals": 16,
        "mtg": 968,
    }


def test_exactly_one_activation_call_occurred() -> None:
    execution = evidence()["activation_execution"]

    assert (
        execution["activation_method"]
        == "PostgresPresentationRepository.activate"
    )

    assert execution["activation_call_count"] == 1
    assert execution["activation_call_completed"] is True

    assert (
        execution["automatic_second_activation_performed"]
        is False
    )

    assert (
        execution["automatic_fallback_activation_performed"]
        is False
    )


def test_target_is_now_exact_active_publication() -> None:
    active = evidence()[
        "active_publication_after_activation"
    ]

    assert (
        active["publication_id"]
        == "mtg-premium-stage-rehearsal-ac8adb415f03"
    )

    assert active["publication_status"] == "ACTIVE"

    assert (
        active["content_fingerprint"]
        == "4a67d16878f0cdb5077b98aa13bd44276f1a993ce2a2b045f52a1ebefe633154"
    )

    assert active["record_count"] == 13264

    assert (
        active["source_database_sha256"]
        == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    )


def test_previous_active_is_preserved_superseded() -> None:
    previous = evidence()[
        "previous_publication_after_activation"
    ]

    assert (
        previous["publication_id"]
        == "metals-final-decision-presentation-r1-20260827"
    )

    assert previous["publication_status"] == "SUPERSEDED"
    assert previous["record_count"] == 12477
    assert previous["preserved"] is True


def test_post_activation_population_is_exact() -> None:
    post = evidence()["post_activation_certification"]

    assert post["target_active_pointer"] == "PASS"
    assert post["target_status_active"] == "PASS"

    assert (
        post["target_fingerprint_preserved"]
        == "PASS"
    )

    assert (
        post["target_record_count_preserved"]
        == "PASS"
    )

    assert post["premium_record_count"] == 787
    assert post["premium_unique_asset_id_count"] == 787

    assert (
        post["premium_payload_readback"]
        == "LOSSLESS"
    )

    assert post["active_pointer_count"] == 1
    assert post["active_publication_count"] == 1


def test_native_semantics_remain_preserved() -> None:
    semantic = evidence()["semantic_certification"]

    assert (
        semantic[
            "one_year_direct_certified_semantics_preserved"
        ]
        is True
    )

    assert (
        semantic["q10_governed_threshold_preserved"]
        is True
    )

    assert (
        semantic["three_year_values_remain_scenarios"]
        is True
    )

    assert (
        semantic["five_year_values_remain_scenarios"]
        is True
    )

    assert (
        semantic["three_year_values_are_purchase_trigger"]
        is False
    )

    assert (
        semantic["five_year_values_are_purchase_trigger"]
        is False
    )

    assert (
        semantic[
            "rank_can_override_purchase_threshold"
        ]
        is False
    )


def test_execution_surfaces_are_absent() -> None:
    semantic = evidence()["semantic_certification"]

    assert (
        semantic[
            "automatic_purchase_execution_surface_present"
        ]
        is False
    )

    assert (
        semantic[
            "execution_ready_purchase_surface_present"
        ]
        is False
    )


def test_activation_changed_no_source_or_ui_code() -> None:
    value = evidence()["immutability_results"]

    assert value["analytical_database_modified"] is False
    assert value["mtg_source_modified"] is False
    assert value["mtg_premium_sidecar_modified"] is False

    assert (
        value["uip_repository_modified_by_activation"]
        is False
    )

    assert value["read_api_code_changed"] is False
    assert value["frontend_changed"] is False
    assert value["model_execution_performed"] is False


def test_next_gate_is_read_api_validation_consideration() -> None:
    conclusion = evidence()["certified_conclusion"]

    assert conclusion["premium_presentation_is_live"] is True

    assert (
        conclusion["active_publication_record_count"]
        == 13264
    )

    assert (
        conclusion[
            "live_mtg_premium_research_record_count"
        ]
        == 787
    )

    assert (
        conclusion["premium_rows_live_and_lossless"]
        is True
    )

    assert (
        conclusion[
            "single_active_publication_preserved"
        ]
        is True
    )

    assert (
        conclusion[
            "read_api_validation_authorized_by_this_evidence"
        ]
        is False
    )

    assert (
        conclusion["read_api_code_change_authorized"]
        is False
    )

    assert (
        conclusion["frontend_change_authorized"]
        is False
    )

    assert (
        conclusion["next_gate"]
        == (
            "CONSIDER_BOUNDED_MTG_PREMIUM_"
            "READ_API_VALIDATION_AUTHORIZATION"
        )
    )
