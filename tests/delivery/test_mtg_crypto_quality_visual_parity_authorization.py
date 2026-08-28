from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

AUTH = (
    ROOT
    / "config"
    / "presentation"
    / "mtg_crypto_quality_visual_parity_authorization_v1.json"
)


def load_auth() -> dict:
    return json.loads(
        AUTH.read_text(encoding="utf-8-sig")
    )


def test_identity_and_status() -> None:
    value = load_auth()

    assert (
        value["authorization_id"]
        == "UIP_MTG_CRYPTO_QUALITY_VISUAL_PARITY_AUTHORIZATION_V1"
    )

    assert (
        value["status"]
        == "AUTHORIZED_FOR_BOUNDED_MTG_CRYPTO_QUALITY_VISUAL_PARITY"
    )


def test_crypto_is_visual_reference_only() -> None:
    value = load_auth()["visual_reference"]

    assert value["domain"] == "crypto"
    assert value["model_semantics_may_not_be_copied"] is True


def test_native_card_remains_mtg_specific() -> None:
    value = load_auth()["card_design_contract"]

    assert "native lane rank" in value["primary_fields"]
    assert "expected 1Y return" in value["primary_fields"]

    assert value["bear_base_bull_may_not_be_synthesized"] is True


def test_visualization_never_synthesizes_missing_models() -> None:
    value = load_auth()["visualization_contract"]

    assert value["synthetic_price_history_forbidden"] is True
    assert value["synthetic_forecast_distribution_forbidden"] is True
    assert value["synthetic_risk_score_forbidden"] is True
    assert value["synthetic_bear_base_bull_forbidden"] is True


def test_asset_lane_authority_promotion_is_observed_only() -> None:
    value = load_auth()["lane_authority_semantic_repair"]

    assert value["observed_asset_lane_authority_may_be_promoted"] is True

    assert (
        value["promotion_requires_actual_observed_asset_field"]
        is True
    )

    assert value["synthetic_lane_authority_forbidden"] is True


def test_precollector_tier_and_evidence_are_distinct() -> None:
    value = load_auth()["precollector_semantic_separation"]

    assert value["native_purchase_status_preserved"] is True
    assert value["evidence_state_preserved"] is True

    assert (
        value["tier_and_evidence_must_not_be_presented_as_same_concept"]
        is True
    )

    assert (
        value["recommended_visual_labels"]["evidence_state"]
        == "Ranking evidence state"
    )


def test_missing_authority_stays_missing() -> None:
    value = load_auth()["missing_authority_contract"]

    assert value["missing_current_price_remains_missing"] is True
    assert value["missing_forecast_remains_missing"] is True
    assert value["missing_risk_remains_missing"] is True
    assert value["missing_rank_remains_missing"] is True
    assert value["fake_zero_forbidden"] is True


def test_secret_lair_is_not_redesigned() -> None:
    value = load_auth()["secret_lair_contract"]

    assert value["existing_design_preserved"] is True
    assert value["q10_purchase_policy_unchanged"] is True

    assert (
        value["this_authorization_does_not_redesign_secret_lair"]
        is True
    )


def test_governance_boundaries_remain() -> None:
    value = load_auth()["governance_preservation"]

    assert value["collector_rank_remains_lane_native"] is True
    assert value["precollector_rank_remains_lane_native"] is True

    assert value["universal_mtg_rank_forbidden"] is True
    assert value["cross_domain_rank_forbidden"] is True

    assert (
        value["recommendation_does_not_authorize_execution"]
        is True
    )


def test_backend_model_and_deployment_are_forbidden() -> None:
    value = load_auth()["explicitly_forbidden"]

    assert value["database_write"] is True
    assert value["backend_endpoint_change"] is True

    assert value["ranking_algorithm_change"] is True
    assert value["forecast_algorithm_change"] is True
    assert value["risk_algorithm_change"] is True

    assert value["model_retraining"] is True

    assert value["hosted_deployment"] is True