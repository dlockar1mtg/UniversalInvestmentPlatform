from datetime import date

import pytest

from foundation.intelligence.scoring import (
    ScoringModelStatus,
    model_from_mapping,
)


def test_model_from_mapping_builds_definition() -> None:
    definition = model_from_mapping(
        {
            "model_id": "crypto_core_v1",
            "asset_class": "crypto",
            "version": "1.0.0",
            "scoring_profile_id": "crypto_profile_v1",
            "normalization_profile_id": "crypto_normalization_v1",
            "status": "active",
            "effective_from": "2026-07-17",
        }
    )
    assert definition.status is ScoringModelStatus.ACTIVE
    assert definition.effective_from == date(2026, 7, 17)


def test_model_from_mapping_rejects_missing_fields() -> None:
    with pytest.raises(ValueError):
        model_from_mapping({"model_id": "incomplete"})


def test_model_from_mapping_rejects_invalid_date() -> None:
    with pytest.raises(ValueError):
        model_from_mapping(
            {
                "model_id": "crypto_core_v1",
                "asset_class": "crypto",
                "version": "1.0.0",
                "scoring_profile_id": "crypto_profile_v1",
                "normalization_profile_id": "crypto_normalization_v1",
                "status": "active",
                "effective_from": "07/17/2026",
            }
        )
