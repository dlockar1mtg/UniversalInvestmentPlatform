"""Probabilistic scenario-tree generation engine."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import product
from math import isclose
from typing import Iterable

import numpy as np

from .distribution_enums import (
    DistributionFamily,
    DistributionStatus,
    TailRiskSide,
)
from .distribution_models import (
    DistributionProvenance,
    DistributionStatistics,
    ForecastConfidenceInterval,
    ForecastDistributionResult,
    ForecastPercentile,
    TailRiskMetrics,
)
from .scenario_contracts import (
    ScenarioDirection,
    ScenarioStageDefinition,
    ScenarioTerminalOutcome,
    ScenarioTreeDiagnostics,
    ScenarioTreeNode,
    ScenarioTreeRequest,
    ScenarioTreeResult,
    ScenarioTreeStatus,
)


class ScenarioTreeGenerationEngine:
    """Build, prune, and summarize multi-stage scenario trees."""

    def generate(
        self,
        request: ScenarioTreeRequest,
    ) -> ScenarioTreeResult:
        terminal_records = self._enumerate_terminal_paths(request)
        original_count = len(terminal_records)
        original_mass = sum(item["probability"] for item in terminal_records)

        retained, pruned_count = self._prune_paths(
            terminal_records,
            request,
        )
        retained_mass = sum(item["probability"] for item in retained)

        renormalization_factor = 1.0
        if (
            retained
            and request.profile.renormalize_after_pruning
            and not isclose(retained_mass, 1.0, abs_tol=1e-12)
        ):
            renormalization_factor = 1.0 / retained_mass
            for item in retained:
                item["probability"] *= renormalization_factor
            retained_mass = sum(item["probability"] for item in retained)

        if not retained:
            raise ValueError(
                "Scenario-tree pruning removed every terminal path."
            )

        nodes = self._build_nodes(request, retained)
        outcomes = tuple(
            ScenarioTerminalOutcome(
                node_id=item["terminal_node_id"],
                path=tuple(item["path_names"]),
                probability=float(item["probability"]),
                terminal_value=float(item["terminal_value"]),
                total_return=float(item["total_return"]),
                direction=item["direction"],
            )
            for item in sorted(
                retained,
                key=lambda value: (
                    -value["probability"],
                    value["path_names"],
                ),
            )
        )

        distribution = self._build_distribution(request, outcomes)
        status = (
            ScenarioTreeStatus.PRUNED
            if pruned_count > 0
            else ScenarioTreeStatus.GENERATED
        )
        diagnostics = ScenarioTreeDiagnostics(
            status=status,
            stage_count=len(request.stages),
            node_count=len(nodes),
            terminal_path_count=len(outcomes),
            pruned_path_count=pruned_count,
            original_probability_mass=original_mass,
            retained_probability_mass=retained_mass,
            renormalization_factor=renormalization_factor,
            explanation=(
                (
                    f"Generated {original_count} terminal paths across "
                    f"{len(request.stages)} stages."
                ),
                (
                    f"Retained {len(outcomes)} terminal paths and pruned "
                    f"{pruned_count}."
                ),
                (
                    f"Retained probability mass is "
                    f"{retained_mass:.6f}."
                ),
            ),
            metrics={
                "expected_terminal_value": (
                    distribution.statistics.mean
                ),
                "probability_above_reference": (
                    distribution.probability_above_reference or 0.0
                ),
                "probability_above_target": (
                    distribution.probability_above_target or 0.0
                ),
            },
        )
        return ScenarioTreeResult(
            distribution=distribution,
            nodes=nodes,
            terminal_outcomes=outcomes,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _enumerate_terminal_paths(
        request: ScenarioTreeRequest,
    ) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []

        for combination in product(
            *(stage.branches for stage in request.stages)
        ):
            probability = 1.0
            value = request.reference_value
            path_names: list[str] = []
            directions: list[ScenarioDirection] = []

            for branch in combination:
                probability *= branch.probability
                value *= branch.return_multiplier
                path_names.append(branch.name)
                directions.append(branch.direction)

            total_return = value / request.reference_value - 1.0
            records.append(
                {
                    "branches": combination,
                    "path_names": tuple(path_names),
                    "probability": probability,
                    "terminal_value": value,
                    "total_return": total_return,
                    "direction": (
                        ScenarioTreeGenerationEngine._aggregate_direction(
                            directions,
                            total_return,
                        )
                    ),
                    "terminal_node_id": (
                        "node:"
                        + ":".join(
                            f"{index + 1}-{name}"
                            for index, name in enumerate(path_names)
                        )
                    ),
                }
            )

        return records

    @staticmethod
    def _aggregate_direction(
        directions: Iterable[ScenarioDirection],
        total_return: float,
    ) -> ScenarioDirection:
        if total_return > 1e-12:
            return ScenarioDirection.UPSIDE
        if total_return < -1e-12:
            return ScenarioDirection.DOWNSIDE

        values = tuple(directions)
        upside = values.count(ScenarioDirection.UPSIDE)
        downside = values.count(ScenarioDirection.DOWNSIDE)
        if upside > downside:
            return ScenarioDirection.UPSIDE
        if downside > upside:
            return ScenarioDirection.DOWNSIDE
        return ScenarioDirection.NEUTRAL

    @staticmethod
    def _prune_paths(
        records: list[dict[str, object]],
        request: ScenarioTreeRequest,
    ) -> tuple[list[dict[str, object]], int]:
        retained = [
            dict(item)
            for item in records
            if float(item["probability"])
            >= request.profile.minimum_path_probability
        ]

        if request.profile.maximum_terminal_paths is not None:
            retained = sorted(
                retained,
                key=lambda item: (
                    -float(item["probability"]),
                    tuple(item["path_names"]),
                ),
            )[: request.profile.maximum_terminal_paths]

        return retained, len(records) - len(retained)

    @staticmethod
    def _build_nodes(
        request: ScenarioTreeRequest,
        retained: list[dict[str, object]],
    ) -> tuple[ScenarioTreeNode, ...]:
        nodes: dict[str, ScenarioTreeNode] = {}

        if request.profile.include_internal_nodes:
            nodes["root"] = ScenarioTreeNode(
                node_id="root",
                parent_id=None,
                stage_number=0,
                branch_name="root",
                direction=ScenarioDirection.NEUTRAL,
                conditional_probability=1.0,
                path_probability=1.0,
                value=request.reference_value,
                cumulative_return=0.0,
                terminal=False,
            )

        for record in retained:
            parent_id = "root" if request.profile.include_internal_nodes else None
            probability = 1.0
            value = request.reference_value
            path_parts: list[str] = []
            branches = record["branches"]

            for index, branch in enumerate(branches):
                probability *= branch.probability
                value *= branch.return_multiplier
                path_parts.append(f"{index + 1}-{branch.name}")
                node_id = "node:" + ":".join(path_parts)
                terminal = index == len(branches) - 1

                if (
                    not request.profile.include_internal_nodes
                    and not terminal
                ):
                    continue

                nodes[node_id] = ScenarioTreeNode(
                    node_id=node_id,
                    parent_id=parent_id,
                    stage_number=index + 1,
                    branch_name=branch.name,
                    direction=branch.direction,
                    conditional_probability=branch.probability,
                    path_probability=probability,
                    value=value,
                    cumulative_return=(
                        value / request.reference_value - 1.0
                    ),
                    terminal=terminal,
                    metadata={
                        "stage_label": request.stages[index].label,
                    },
                )
                parent_id = node_id

        return tuple(
            sorted(
                nodes.values(),
                key=lambda item: (
                    item.stage_number,
                    item.node_id,
                ),
            )
        )

    def _build_distribution(
        self,
        request: ScenarioTreeRequest,
        outcomes: tuple[ScenarioTerminalOutcome, ...],
    ) -> ForecastDistributionResult:
        values = np.array(
            [item.terminal_value for item in outcomes],
            dtype=float,
        )
        probabilities = np.array(
            [item.probability for item in outcomes],
            dtype=float,
        )
        probabilities = probabilities / probabilities.sum()

        mean_value = float(np.sum(values * probabilities))
        variance = float(
            np.sum(
                probabilities * (values - mean_value) ** 2
            )
        )
        std = float(np.sqrt(variance))
        percentile_levels = (0.05, 0.25, 0.50, 0.75, 0.95)
        quantiles = {
            level: self._weighted_quantile(
                values,
                probabilities,
                level,
            )
            for level in percentile_levels
        }

        percentiles = tuple(
            ForecastPercentile(
                probability=level,
                value=quantiles[level],
                label=f"p{round(level * 100):02d}",
            )
            for level in percentile_levels
        )
        intervals = (
            ForecastConfidenceInterval(
                lower_probability=0.25,
                upper_probability=0.75,
                lower_value=quantiles[0.25],
                upper_value=quantiles[0.75],
                coverage=0.50,
            ),
            ForecastConfidenceInterval(
                lower_probability=0.05,
                upper_probability=0.95,
                lower_value=quantiles[0.05],
                upper_value=quantiles[0.95],
                coverage=0.90,
            ),
        )

        returns = values / request.reference_value - 1.0
        var_level = 1.0 - request.profile.var_confidence_level
        value_at_risk = self._weighted_quantile(
            returns,
            probabilities,
            var_level,
        )
        tail_mask = returns <= value_at_risk + 1e-12
        tail_probabilities = probabilities[tail_mask]
        expected_shortfall = float(
            np.sum(
                returns[tail_mask] * tail_probabilities
            )
            / tail_probabilities.sum()
        )

        probability_of_loss = float(
            probabilities[returns < 0.0].sum()
        )
        probability_above_reference = float(
            probabilities[values > request.reference_value].sum()
        )
        probability_below_reference = float(
            probabilities[values < request.reference_value].sum()
        )
        target = request.profile.target_value
        probability_above_target = (
            None
            if target is None
            else float(probabilities[values > target].sum())
        )
        target_return = (
            None
            if target is None
            else target / request.reference_value - 1.0
        )
        probability_of_target_shortfall = (
            None
            if target_return is None
            else float(
                probabilities[
                    returns < target_return
                ].sum()
            )
        )

        skewness, kurtosis = self._weighted_shape(
            values,
            probabilities,
            mean_value,
            std,
        )

        return ForecastDistributionResult(
            asset_id=request.asset_id,
            asset_class=request.asset_class,
            as_of_date=request.as_of_date,
            target_date=request.target_date,
            horizon=request.horizon,
            reference_value=request.reference_value,
            currency=request.currency,
            family=DistributionFamily.SCENARIO_TREE,
            statistics=DistributionStatistics(
                mean=mean_value,
                median=quantiles[0.50],
                variance=variance,
                standard_deviation=std,
                minimum=float(values.min()),
                maximum=float(values.max()),
                skewness=skewness,
                excess_kurtosis=kurtosis,
                mode=self._weighted_mode(values, probabilities),
                sample_count=len(values),
            ),
            provenance=DistributionProvenance(
                model_name=request.model_name,
                model_version=request.model_version,
                generated_at=datetime.now(timezone.utc),
                parameters={
                    "stage_count": len(request.stages),
                    "terminal_path_count": len(outcomes),
                    "minimum_path_probability": (
                        request.profile.minimum_path_probability
                    ),
                    "maximum_terminal_paths": (
                        request.profile.maximum_terminal_paths
                    ),
                },
            ),
            status=DistributionStatus.VALIDATED,
            percentiles=percentiles,
            confidence_intervals=intervals,
            tail_risk=(
                TailRiskMetrics(
                    confidence_level=(
                        request.profile.var_confidence_level
                    ),
                    side=TailRiskSide.LOWER,
                    value_at_risk=value_at_risk,
                    expected_shortfall=expected_shortfall,
                    probability_of_loss=probability_of_loss,
                    probability_of_target_shortfall=(
                        probability_of_target_shortfall
                    ),
                    target_return=target_return,
                ),
            ),
            probability_above_reference=probability_above_reference,
            probability_below_reference=probability_below_reference,
            probability_above_target=probability_above_target,
            target_value=target,
            metadata=dict(request.metadata),
        )

    @staticmethod
    def _weighted_quantile(
        values: np.ndarray,
        probabilities: np.ndarray,
        probability: float,
    ) -> float:
        order = np.argsort(values)
        sorted_values = values[order]
        sorted_probabilities = probabilities[order]
        cumulative = np.cumsum(sorted_probabilities)
        index = int(np.searchsorted(cumulative, probability, side="left"))
        index = min(index, len(sorted_values) - 1)
        return float(sorted_values[index])

    @staticmethod
    def _weighted_mode(
        values: np.ndarray,
        probabilities: np.ndarray,
    ) -> float:
        totals: dict[float, float] = {}
        for value, probability in zip(values, probabilities):
            key = float(value)
            totals[key] = totals.get(key, 0.0) + float(probability)
        return max(
            totals.items(),
            key=lambda item: (item[1], -item[0]),
        )[0]

    @staticmethod
    def _weighted_shape(
        values: np.ndarray,
        probabilities: np.ndarray,
        mean_value: float,
        std: float,
    ) -> tuple[float, float]:
        if std <= 1e-15:
            return 0.0, 0.0
        standardized = (values - mean_value) / std
        skewness = float(
            np.sum(probabilities * standardized**3)
        )
        excess_kurtosis = float(
            np.sum(probabilities * standardized**4) - 3.0
        )
        return skewness, excess_kurtosis
