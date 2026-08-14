from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

EVIDENCE = (
    ROOT
    / "docs"
    / "project_control"
    / "generated"
    / "crypto_a1_integration"
    / "crypto_a1_integration_certification.json"
)


def _load_evidence() -> dict:
    return json.loads(
        EVIDENCE.read_text(encoding="utf-8-sig")
    )


def test_crypto_a1_certification_status_and_counts() -> None:
    evidence = _load_evidence()

    assert (
        evidence["certification_status"]
        == "UIP_CRYPTO_A1_INTEGRATION_CERTIFICATION_PASS"
    )

    counts = evidence["observed_package_counts"]

    assert counts == {
        "asset_master": 6,
        "forecasts": 132,
        "platform_status": 1,
        "portfolio_positions": 0,
        "recommendations": 6,
        "risk_metrics": 6,
        "imported_total": 151,
    }

    assert (
        evidence["crypto_source"]["package_population_is_permanent"]
        is False
    )


def test_crypto_a1_semantic_preservation() -> None:
    evidence = _load_evidence()

    semantic = evidence["semantic_certification"]

    assert semantic["current_package_integrity_pass"] is True
    assert semantic["manifest_sha256_validation_pass"] is True
    assert semantic["adapter_version_preserved"] is True
    assert semantic["contract_version_preserved"] is True
    assert semantic["canonical_crypto_asset_ids_preserved"] is True
    assert semantic["native_recommendation_labels_preserved"] is True
    assert semantic["wait_normalized_to_watch"] is True
    assert semantic["avoid_normalized_to_sell"] is True
    assert semantic["missing_holdings_preserved_as_absent"] is True
    assert semantic["holdings_synthesized"] is False
    assert semantic["lineage_complete"] is True
    assert semantic["duplicate_replay_rejected"] is True
    assert semantic["source_database_read_only"] is True
    assert semantic["crypto_model_changed"] is False
    assert semantic["cross_asset_ranking_created"] is False
    assert semantic["automatic_purchase_execution_created"] is False


def test_crypto_a1_native_recommendation_mapping() -> None:
    evidence = _load_evidence()

    mapping = {
        item["asset"]: (
            item["native"],
            item["universal"],
        )
        for item in evidence["recommendation_evidence"]
    }

    assert mapping == {
        "crypto:avalanche": ("WAIT", "watch"),
        "crypto:bitcoin": ("WAIT", "watch"),
        "crypto:chainlink": ("WAIT", "watch"),
        "crypto:ethereum": ("WAIT", "watch"),
        "crypto:solana": ("WAIT", "watch"),
        "crypto:xrp": ("AVOID", "sell"),
    }


def test_crypto_a1_rehearsal_boundary() -> None:
    evidence = _load_evidence()

    rehearsal = evidence["rehearsal"]

    assert (
        rehearsal["status"]
        == "UIP_CRYPTO_A1_FINAL_REHEARSAL_PASS"
    )

    assert rehearsal["disposable_import"] is True
    assert rehearsal["production_uip_database_modified"] is False
    assert rehearsal["crypto_database_modified"] is False
    assert rehearsal["repository_files_modified_during_rehearsal"] is False
    assert rehearsal["data_collection_performed"] is False
    assert rehearsal["model_execution_performed"] is False

    assert (
        evidence["next_authorized_milestone"]
        == "UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_INTERFACE"
    )
