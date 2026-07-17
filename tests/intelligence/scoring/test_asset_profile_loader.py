from decimal import Decimal

import pytest

from foundation.intelligence.scoring import asset_profile_from_mapping


def minimal_mapping() -> dict:
    return {
        "model_id": "test_model_v1",
        "profile_id": "test_profile_v1",
        "asset_class": "test",
        "version": "1.0.0",
        "normalization_profile_id": "test_normalization_v1",
        "dimension_weights": {"risk": 1.0},
        "minimum_coverage": 0.7,
        "confidence_floor": 0.7,
        "maximum_risk_penalty": 0.2,
        "metrics": [
            {
                "metric_name": "risk_metric",
                "dimension": "risk",
                "strategy": "bounded_range",
                "weight": 1.0,
                "parameters": {"minimum": 0, "maximum": 100},
            }
        ],
    }


def test_asset_profile_from_mapping() -> None:
    profile = asset_profile_from_mapping(minimal_mapping())
    assert profile.asset_class == "test"
    assert profile.metric_rules[0].weight == Decimal("1.0")


def test_loader_rejects_missing_required_field() -> None:
    data = minimal_mapping()
    del data["metrics"]
    with pytest.raises(ValueError):
        asset_profile_from_mapping(data)


def test_loader_rejects_duplicate_metric_names() -> None:
    data = minimal_mapping()
    data["metrics"].append(dict(data["metrics"][0]))
    with pytest.raises(ValueError):
        asset_profile_from_mapping(data)
