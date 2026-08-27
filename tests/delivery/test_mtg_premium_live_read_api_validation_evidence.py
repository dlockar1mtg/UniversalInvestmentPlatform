from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

PATH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_premium_live_read_api_validation_evidence_v1.json"
)


def evidence() -> dict:
    return json.loads(
        PATH.read_text(
            encoding="utf-8-sig"
        )
    )


def test_identity_and_pass_state() -> None:
    value = evidence()

    assert (
        value["evidence_id"]
        == "UIP_MTG_PREMIUM_LIVE_READ_API_VALIDATION_EVIDENCE_V1"
    )

    assert value["evidence_version"] == "1.0.0"
    assert value["certification_state"] == "PASS"
    assert value["execution_step"] == "STEP_14L_D_R"


def test_exact_governed_heads_and_sources() -> None:
    value = evidence()["governing_authorities"]

    assert (
        value["uip_execution_head"]
        == "f244105455ee605717ce6a9d65e27186a62f9a36"
    )

    assert (
        value["mtg_head"]
        == "6b610b208549bec4be2c0ec7f7f3c2f69b154302"
    )

    assert (
        value["analytical_database_sha256"]
        == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    )

    assert (
        value["premium_sidecar_sha256"]
        == "296ccbb9ba96812b99dacd771f1ad311496b4997fa0ac7103e68a1d4aaa03333"
    )


def test_exact_active_publication() -> None:
    active = evidence()[
        "active_publication_validation"
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
    assert active["mtg_premium_research_record_count"] == 787
    assert active["mtg_premium_unique_asset_id_count"] == 787


def test_server_read_only_enforcement() -> None:
    ro = evidence()["read_only_enforcement"]

    assert ro["connection_type"] == "NEON_POOLED"
    assert ro["mechanism"] == "SET_TRANSACTION_READ_ONLY"

    assert (
        ro["read_only_enabled_before_application_select"]
        is True
    )

    assert (
        ro["transaction_read_only_verified_before_live_validation"]
        is True
    )

    assert (
        ro["transaction_read_only_verified_after_live_validation"]
        is True
    )

    assert ro["server_enforced_transaction_read_only"] is True


def test_deterministic_assets_are_recorded() -> None:
    assets = evidence()[
        "deterministic_validation_assets"
    ]

    assert (
        assets["premium_asset_id"]
        == "SECRET_LAIR_V1_1|SL-00DFD5FAF7A6FF"
    )

    assert (
        assets["missing_premium_authority_asset_id"]
        == "COLLECTOR_V1|MTG-CANON-TCGPLAYER-208279"
    )


def test_repository_projection_is_lossless() -> None:
    result = evidence()["repository_validation"]

    assert result["premium_asset_resolved"] is True
    assert result["premium_record_count"] == 1

    assert (
        result["premium_payload_readback"]
        == "LOSSLESS"
    )

    assert (
        result["missing_premium_asset_resolved"]
        is True
    )

    assert result["missing_premium_payload"] is None
    assert result["missing_premium_record_count"] == 0

    assert (
        result["missing_authority_was_synthesized"]
        is False
    )


def test_existing_fastapi_route_is_live_and_lossless() -> None:
    route = evidence()["fastapi_route_validation"]

    assert (
        route["endpoint"]
        == "/v1/presentation/mtg-research/{asset_id}"
    )

    assert route["http_status"] == 200

    assert (
        route["premium_payload_readback"]
        == "LOSSLESS"
    )

    assert route["premium_record_count"] == 1

    assert (
        route["hosted_external_api_request_performed"]
        is False
    )


def test_mtg_semantics_are_preserved() -> None:
    semantic = evidence()["semantic_certification"]

    assert (
        semantic["one_year_certified_semantics_preserved"]
        is True
    )

    assert (
        semantic["q10_governed_purchase_threshold_preserved"]
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

    assert semantic["three_year_direct_forecast_created"] is False
    assert semantic["five_year_direct_forecast_created"] is False

    assert semantic["cross_domain_rank_created"] is False
    assert semantic["universal_mtg_rank_created"] is False

    assert (
        semantic["automatic_purchase_execution_authorized"]
        is False
    )


def test_validation_mutated_nothing() -> None:
    immutable = evidence()["immutability_certification"]

    for key in (
        "postgres_write_attempted",
        "presentation_activation_attempted",
        "active_pointer_mutation_attempted",
        "analytical_database_modified",
        "mtg_source_modified",
        "premium_sidecar_modified",
        "uip_repository_modified_by_validation",
        "read_api_code_changed",
        "frontend_changed",
    ):
        assert immutable[key] is False


def test_end_to_end_chain_is_certified() -> None:
    conclusion = evidence()["certified_conclusion"]

    for key in (
        "live_end_to_end_premium_read_path_proven",
        "certified_source_to_active_postgres_proven",
        "active_postgres_to_repository_projection_proven",
        "repository_to_existing_fastapi_route_proven",
        "premium_payload_lossless_end_to_end",
        "missing_premium_authority_remains_missing_end_to_end",
    ):
        assert conclusion[key] is True

    assert (
        conclusion[
            "frontend_integration_authorized_by_this_evidence"
        ]
        is False
    )

    assert (
        conclusion["next_gate"]
        == "CONSIDER_BOUNDED_MTG_PREMIUM_FRONTEND_INTEGRATION_AUTHORIZATION"
    )
