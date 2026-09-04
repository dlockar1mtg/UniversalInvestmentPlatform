from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

EVIDENCE_PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_staged_persistence_rehearsal_evidence_v1.json"
)


def evidence() -> dict:
    return json.loads(
        EVIDENCE_PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_certification_identity() -> None:
    value = evidence()

    assert (
        value["evidence_id"]
        == "UIP_MTG_PREMIUM_STAGED_PERSISTENCE_REHEARSAL_EVIDENCE_V1"
    )

    assert value["evidence_version"] == "1.0.0"
    assert value["certification_state"] == "PASS"
    assert value["rehearsal_step"] == "STEP_14J_B3"


def test_exact_governed_authorities() -> None:
    source = evidence()["certified_sources"]

    assert (
        source["uip_head"]
        == "ac8adb415f03a6c13deb7ad704efa32df5a4ee2d"
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


def test_publication_reconciles_exactly() -> None:
    value = evidence()[
        "publication_build_reconciliation"
    ]

    assert value["baseline_record_count"] == 12477
    assert value["premium_publication_record_count"] == 13264
    assert value["premium_record_count"] == 787

    assert (
        value["premium_publication_record_count"]
        - value["baseline_record_count"]
        == 787
    )

    assert value["reconciles_as_baseline_plus_premium"] is True


def test_staged_publication_identity() -> None:
    staged = evidence()["staged_publication"]

    assert (
        staged["publication_id"]
        == "mtg-premium-stage-rehearsal-ac8adb415f03"
    )

    assert staged["publication_status"] == "STAGED"

    assert (
        staged["content_fingerprint"]
        == "4a67d16878f0cdb5077b98aa13bd44276f1a993ce2a2b045f52a1ebefe633154"
    )

    assert staged["record_count"] == 13264

    assert (
        staged["mtg_premium_research_record_count"]
        == 787
    )

    assert (
        staged["mtg_premium_unique_asset_id_count"]
        == 787
    )


def test_certified_native_asset_counts_are_preserved() -> None:
    counts = evidence()[
        "staged_publication"
    ]["certified_asset_counts"]

    assert counts == {
        "crypto": 6,
        "metals": 16,
        "mtg": 968,
    }


def test_postgres_persistence_passed_losslessly() -> None:
    result = evidence()["persistence_results"]

    assert result["postgres_stage_call"] == "PASS"
    assert result["store_validate_staged"] == "PASS"

    assert (
        result["premium_payload_readback"]
        == "LOSSLESS"
    )

    assert (
        result["premium_identity_uniqueness"]
        == "PASS"
    )

    assert (
        result["rehearsal_publication_remained_staged"]
        is True
    )


def test_active_publication_was_preserved() -> None:
    active = evidence()[
        "active_publication_during_rehearsal"
    ]

    assert (
        active["publication_id"]
        == "metals-final-decision-presentation-r1-20260827"
    )

    assert active["publication_status"] == "ACTIVE"
    assert active["record_count"] == 12477

    assert (
        active["source_database_sha256"]
        == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    )

    assert (
        active["identical_before_and_after_rehearsal"]
        is True
    )

    assert active["active_pointer_changed"] is False
    assert active["active_metadata_changed"] is False


def test_mtg_semantics_survived_persistence() -> None:
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
        semantic["three_year_scenario_is_purchase_trigger"]
        is False
    )

    assert (
        semantic["five_year_scenario_is_purchase_trigger"]
        is False
    )

    assert (
        semantic[
            "rank_can_override_governed_purchase_threshold"
        ]
        is False
    )


def test_execution_surfaces_remain_absent() -> None:
    semantic = evidence()["semantic_certification"]

    assert (
        semantic["automatic_execution_surface_present"]
        is False
    )

    assert (
        semantic[
            "execution_ready_purchase_surface_present"
        ]
        is False
    )


def test_rehearsal_changed_no_source_or_ui_surface() -> None:
    value = evidence()["immutability_results"]

    assert value["analytical_database_modified"] is False
    assert value["mtg_source_modified"] is False

    assert (
        value["uip_repository_modified_by_rehearsal"]
        is False
    )

    assert value["read_api_changed"] is False
    assert value["frontend_changed"] is False


def test_activation_did_not_occur() -> None:
    state = evidence()["activation_state"]

    assert state["activate_method_called"] is False
    assert state["live_activation_performed"] is False
    assert state["rehearsal_publication_is_active"] is False


def test_next_gate_is_activation_consideration_only() -> None:
    conclusion = evidence()["certified_conclusion"]

    assert (
        conclusion["staged_postgresql_persistence_proven"]
        is True
    )

    assert (
        conclusion[
            "787_premium_rows_survive_persistence_losslessly"
        ]
        is True
    )

    assert (
        conclusion[
            "active_publication_preserved_during_rehearsal"
        ]
        is True
    )

    assert (
        conclusion[
            "live_activation_authorized_by_this_evidence"
        ]
        is False
    )

    assert (
        conclusion["next_gate"]
        == (
            "CONSIDER_BOUNDED_MTG_PREMIUM_"
            "LIVE_PRESENTATION_ACTIVATION_AUTHORIZATION"
        )
    )
