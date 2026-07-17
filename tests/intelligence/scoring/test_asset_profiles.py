from decimal import Decimal
from pathlib import Path

from foundation.intelligence.scoring import (
    AssetProfileScoringService,
    DataAvailability,
    MetricObservation,
    ScoreDimension,
    load_asset_profiles,
)


PROFILE_DIR = Path("config/intelligence/scoring/profiles")


def test_all_initial_asset_profiles_load() -> None:
    profiles = load_asset_profiles(PROFILE_DIR)
    assert set(profiles) == {"crypto", "etf", "metals", "mtg", "housing", "cash"}


def test_all_dimension_weights_total_one() -> None:
    for profile in load_asset_profiles(PROFILE_DIR).values():
        assert sum(
            profile.scoring_profile.dimension_weights.values(),
            Decimal("0"),
        ) == Decimal("1.00")


def test_all_metric_rule_names_are_unique() -> None:
    for profile in load_asset_profiles(PROFILE_DIR).values():
        names = [rule.metric_name for rule in profile.metric_rules]
        assert len(names) == len(set(names))


def test_crypto_profile_builds_score_components() -> None:
    profile = load_asset_profiles(PROFILE_DIR)["crypto"]
    observations = {
        rule.metric_name: MetricObservation(
            value=50 if rule.strategy == "bounded_range" else Decimal("0.10"),
            confidence=Decimal("0.9"),
            source="fixture",
        )
        for rule in profile.metric_rules
    }
    components = AssetProfileScoringService().build_components(
        profile,
        observations,
    )
    assert len(components) == len(profile.metric_rules)
    assert all(component.availability is DataAvailability.AVAILABLE for component in components)


def test_missing_observation_becomes_unavailable() -> None:
    profile = load_asset_profiles(PROFILE_DIR)["cash"]
    components = AssetProfileScoringService().build_components(profile, {})
    assert all(
        component.availability is DataAvailability.UNAVAILABLE
        for component in components
    )


def test_risk_dimension_exists_for_every_profile() -> None:
    for profile in load_asset_profiles(PROFILE_DIR).values():
        assert ScoreDimension.RISK in profile.scoring_profile.dimension_weights
