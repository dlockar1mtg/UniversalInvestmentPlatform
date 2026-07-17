"""Tests for Phase 4.3.4 scenario-tree generation."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.forecasting.models import (
    ForecastDirection,
    ForecastHorizon,
    ForecastMethod,
    ForecastProvenance,
    UniversalForecast,
)
from foundation.intelligence.forecasting.probability import (
    DistributionFamily,
    ScenarioBranchTemplate,
    ScenarioDirection,
    ScenarioStageDefinition,
    ScenarioTreeForecastService,
    ScenarioTreeGenerationEngine,
    ScenarioTreeProfile,
    ScenarioTreeRequest,
    ScenarioTreeStatus,
)


def stages() -> tuple[ScenarioStageDefinition, ...]:
    return (
        ScenarioStageDefinition(
            stage_number=1,
            label="Macro regime",
            branches=(
                ScenarioBranchTemplate(
                    name="contraction",
                    probability=0.25,
                    return_multiplier=0.90,
                    direction=ScenarioDirection.DOWNSIDE,
                ),
                ScenarioBranchTemplate(
                    name="baseline",
                    probability=0.50,
                    return_multiplier=1.05,
                    direction=ScenarioDirection.NEUTRAL,
                ),
                ScenarioBranchTemplate(
                    name="expansion",
                    probability=0.25,
                    return_multiplier=1.15,
                    direction=ScenarioDirection.UPSIDE,
                ),
            ),
        ),
        ScenarioStageDefinition(
            stage_number=2,
            label="Asset response",
            branches=(
                ScenarioBranchTemplate(
                    name="weak",
                    probability=0.30,
                    return_multiplier=0.95,
                    direction=ScenarioDirection.DOWNSIDE,
                ),
                ScenarioBranchTemplate(
                    name="normal",
                    probability=0.50,
                    return_multiplier=1.00,
                    direction=ScenarioDirection.NEUTRAL,
                ),
                ScenarioBranchTemplate(
                    name="strong",
                    probability=0.20,
                    return_multiplier=1.10,
                    direction=ScenarioDirection.UPSIDE,
                ),
            ),
        ),
    )


def request(
    *,
    profile: ScenarioTreeProfile | None = None,
) -> ScenarioTreeRequest:
    return ScenarioTreeRequest(
        asset_id="TEST",
        asset_class="equity",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100.0,
        currency="USD",
        model_name="scenario-model",
        model_version="1.0.0",
        stages=stages(),
        profile=profile or ScenarioTreeProfile(
            target_value=115.0
        ),
    )


def forecast() -> UniversalForecast:
    return UniversalForecast(
        forecast_id="forecast-001",
        asset_id="TEST",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100.0,
        point_forecast=108.0,
        currency="USD",
        provenance=ForecastProvenance(
            model_name="scenario-model",
            model_version="1.0.0",
            method=ForecastMethod.ENSEMBLE,
            generated_at=datetime(
                2026, 7, 17, 18, 0, tzinfo=timezone.utc
            ),
        ),
        direction=ForecastDirection.UP,
        confidence_score=0.80,
        expected_return=0.08,
    )


def test_stage_probabilities_must_sum_to_one() -> None:
    with pytest.raises(ValueError, match="must sum to 1.0"):
        ScenarioStageDefinition(
            stage_number=1,
            label="Invalid",
            branches=(
                ScenarioBranchTemplate(
                    name="a",
                    probability=0.30,
                    return_multiplier=1.0,
                    direction=ScenarioDirection.NEUTRAL,
                ),
                ScenarioBranchTemplate(
                    name="b",
                    probability=0.30,
                    return_multiplier=1.0,
                    direction=ScenarioDirection.NEUTRAL,
                ),
            ),
        )


def test_branch_probability_must_be_positive() -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        ScenarioBranchTemplate(
            name="invalid",
            probability=0.0,
            return_multiplier=1.0,
            direction=ScenarioDirection.NEUTRAL,
        )


def test_request_requires_ordered_stages() -> None:
    with pytest.raises(ValueError, match="must be ordered"):
        ScenarioTreeRequest(
            asset_id="TEST",
            asset_class="equity",
            as_of_date=date(2026, 7, 17),
            target_date=date(2027, 7, 17),
            horizon=ForecastHorizon.ONE_YEAR,
            reference_value=100.0,
            currency="USD",
            model_name="model",
            model_version="1.0.0",
            stages=tuple(reversed(stages())),
        )


def test_tree_generates_cartesian_terminal_paths() -> None:
    result = ScenarioTreeGenerationEngine().generate(request())

    assert len(result.terminal_outcomes) == 9
    assert result.diagnostics.terminal_path_count == 9


def test_terminal_probabilities_sum_to_one() -> None:
    result = ScenarioTreeGenerationEngine().generate(request())

    assert sum(
        item.probability for item in result.terminal_outcomes
    ) == pytest.approx(1.0)


def test_terminal_values_apply_multipliers() -> None:
    result = ScenarioTreeGenerationEngine().generate(request())

    path = next(
        item
        for item in result.terminal_outcomes
        if item.path == ("expansion", "strong")
    )
    assert path.terminal_value == pytest.approx(126.5)
    assert path.total_return == pytest.approx(0.265)


def test_internal_nodes_are_generated() -> None:
    result = ScenarioTreeGenerationEngine().generate(request())

    assert any(item.node_id == "root" for item in result.nodes)
    assert any(
        item.stage_number == 1 and not item.terminal
        for item in result.nodes
    )
    assert any(item.terminal for item in result.nodes)


def test_internal_nodes_can_be_disabled() -> None:
    result = ScenarioTreeGenerationEngine().generate(
        request(
            profile=ScenarioTreeProfile(
                include_internal_nodes=False
            )
        )
    )

    assert all(item.terminal for item in result.nodes)
    assert all(item.node_id != "root" for item in result.nodes)


def test_probability_threshold_prunes_paths() -> None:
    result = ScenarioTreeGenerationEngine().generate(
        request(
            profile=ScenarioTreeProfile(
                minimum_path_probability=0.10
            )
        )
    )

    assert result.diagnostics.status is ScenarioTreeStatus.PRUNED
    assert result.diagnostics.pruned_path_count > 0
    assert all(
        item.probability >= 0.10
        for item in result.terminal_outcomes
    )


def test_maximum_terminal_path_limit_is_applied() -> None:
    result = ScenarioTreeGenerationEngine().generate(
        request(
            profile=ScenarioTreeProfile(
                maximum_terminal_paths=4
            )
        )
    )

    assert len(result.terminal_outcomes) == 4
    assert result.diagnostics.pruned_path_count == 5


def test_pruned_paths_are_renormalized() -> None:
    result = ScenarioTreeGenerationEngine().generate(
        request(
            profile=ScenarioTreeProfile(
                maximum_terminal_paths=4,
                renormalize_after_pruning=True,
            )
        )
    )

    assert sum(
        item.probability for item in result.terminal_outcomes
    ) == pytest.approx(1.0)
    assert result.diagnostics.renormalization_factor > 1.0


def test_pruning_every_path_is_rejected() -> None:
    with pytest.raises(ValueError, match="removed every terminal path"):
        ScenarioTreeGenerationEngine().generate(
            request(
                profile=ScenarioTreeProfile(
                    minimum_path_probability=0.90
                )
            )
        )


def test_distribution_family_is_scenario_tree() -> None:
    result = ScenarioTreeGenerationEngine().generate(request())

    assert result.distribution.family is DistributionFamily.SCENARIO_TREE


def test_distribution_expected_value_matches_paths() -> None:
    result = ScenarioTreeGenerationEngine().generate(request())

    expected = sum(
        item.probability * item.terminal_value
        for item in result.terminal_outcomes
    )
    assert result.distribution.statistics.mean == pytest.approx(
        expected
    )


def test_distribution_percentiles_are_ordered() -> None:
    result = ScenarioTreeGenerationEngine().generate(request())

    values = [
        item.value for item in result.distribution.percentiles
    ]
    assert values == sorted(values)


def test_distribution_probability_metrics_are_bounded() -> None:
    distribution = ScenarioTreeGenerationEngine().generate(
        request()
    ).distribution

    assert 0.0 <= distribution.probability_above_reference <= 1.0
    assert 0.0 <= distribution.probability_below_reference <= 1.0
    assert 0.0 <= distribution.probability_above_target <= 1.0


def test_tail_risk_is_consistent() -> None:
    risk = ScenarioTreeGenerationEngine().generate(
        request()
    ).distribution.tail_risk[0]

    assert risk.expected_shortfall <= risk.value_at_risk + 1e-12
    assert risk.confidence_level == 0.95


def test_generation_is_deterministic() -> None:
    engine = ScenarioTreeGenerationEngine()

    first = engine.generate(request())
    second = engine.generate(request())

    assert first.terminal_outcomes == second.terminal_outcomes
    assert (
        first.distribution.statistics.mean
        == second.distribution.statistics.mean
    )


def test_service_builds_tree_from_universal_forecast() -> None:
    result = ScenarioTreeForecastService().generate_for_forecast(
        forecast(),
        asset_class="equity",
        stages=stages(),
        profile=ScenarioTreeProfile(target_value=115.0),
    )

    assert result.distribution.asset_id == "TEST"
    assert result.distribution.metadata["source_forecast_id"] == (
        "forecast-001"
    )
