"""Forecast performance aggregation and ranking engine."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from math import sqrt

from .forecast_validation_contracts import ForecastValidationRecord
from .performance_contracts import (
    ForecastPerformanceMetrics,
    ForecastPerformanceRankingEntry,
    ForecastPerformanceReport,
    PerformanceAnalyticsProfile,
    PerformanceGrade,
    PerformanceGrouping,
)


class ForecastPerformanceAnalyticsEngine:
    """Aggregate validation records into model-performance scorecards."""

    def analyze(
        self,
        records: Iterable[ForecastValidationRecord],
        *,
        grouping: PerformanceGrouping = PerformanceGrouping.OVERALL,
        profile: PerformanceAnalyticsProfile | None = None,
        evaluation_date: date | None = None,
    ) -> ForecastPerformanceReport:
        config = profile or PerformanceAnalyticsProfile()
        items = tuple(records)
        if not items:
            raise ValueError(
                "At least one forecast validation record is required."
            )

        effective_date = evaluation_date or max(
            item.outcome.observation_date for item in items
        )
        filtered = self._apply_window(
            items,
            rolling_window_days=config.rolling_window_days,
            evaluation_date=effective_date,
        )
        if not filtered:
            raise ValueError(
                "No records remain after applying the rolling window."
            )

        grouped = self._group_records(filtered, grouping)
        scorecards = tuple(
            self._aggregate(
                group_key=group_key,
                grouping=grouping,
                records=group_records,
                profile=config,
            )
            for group_key, group_records in sorted(grouped.items())
        )
        rankings = self._rank(scorecards)

        return ForecastPerformanceReport(
            generated_for=grouping,
            scorecards=scorecards,
            rankings=rankings,
            explanation=(
                (
                    f"Analyzed {len(filtered)} validation records "
                    f"across {len(scorecards)} {grouping.value} groups."
                ),
                (
                    f"Top eligible group is "
                    f"{self._top_group(rankings)}."
                ),
            ),
        )

    @staticmethod
    def _apply_window(
        records: tuple[ForecastValidationRecord, ...],
        *,
        rolling_window_days: int | None,
        evaluation_date: date,
    ) -> tuple[ForecastValidationRecord, ...]:
        if rolling_window_days is None:
            return records

        cutoff = evaluation_date - timedelta(days=rolling_window_days)
        return tuple(
            item
            for item in records
            if cutoff <= item.outcome.observation_date <= evaluation_date
        )

    @staticmethod
    def _group_records(
        records: tuple[ForecastValidationRecord, ...],
        grouping: PerformanceGrouping,
    ) -> dict[str, tuple[ForecastValidationRecord, ...]]:
        groups: dict[str, list[ForecastValidationRecord]] = defaultdict(list)

        for item in records:
            if grouping is PerformanceGrouping.OVERALL:
                key = "overall"
            elif grouping is PerformanceGrouping.MODEL:
                key = (
                    f"{item.forecast.provenance.model_name}:"
                    f"{item.forecast.provenance.model_version}"
                )
            elif grouping is PerformanceGrouping.ASSET:
                key = item.forecast.asset_id
            elif grouping is PerformanceGrouping.HORIZON:
                key = item.forecast.horizon.value
            else:
                raise ValueError(f"Unsupported grouping: {grouping}")
            groups[key].append(item)

        return {
            key: tuple(value)
            for key, value in groups.items()
        }

    def _aggregate(
        self,
        *,
        group_key: str,
        grouping: PerformanceGrouping,
        records: tuple[ForecastValidationRecord, ...],
        profile: PerformanceAnalyticsProfile,
    ) -> ForecastPerformanceMetrics:
        absolute_errors = [
            item.absolute_error
            for item in records
            if item.absolute_error is not None
        ]
        signed_errors = [
            item.signed_error
            for item in records
            if item.signed_error is not None
        ]
        relative_errors = [
            item.relative_error
            for item in records
            if item.relative_error is not None
        ]
        percentage_errors = [
            item.absolute_percentage_error
            for item in records
            if item.absolute_percentage_error is not None
        ]

        if not absolute_errors or not signed_errors:
            raise ValueError(
                f"Group {group_key} has no usable error metrics."
            )

        mae = sum(absolute_errors) / len(absolute_errors)
        mse = (
            sum(value * value for value in signed_errors)
            / len(signed_errors)
        )
        rmse = sqrt(mse)
        mape = (
            None
            if not percentage_errors
            else sum(percentage_errors) / len(percentage_errors)
        )
        smape_values = [
            self._smape(item)
            for item in records
            if self._smape(item) is not None
        ]
        smape = (
            None
            if not smape_values
            else sum(smape_values) / len(smape_values)
        )
        mean_bias = sum(signed_errors) / len(signed_errors)
        mean_relative_bias = (
            None
            if not relative_errors
            else sum(relative_errors) / len(relative_errors)
        )

        direction_values = [
            item.direction_correct
            for item in records
            if item.direction_correct is not None
        ]
        directional_accuracy = (
            None
            if not direction_values
            else sum(direction_values) / len(direction_values)
        )

        coverage_values = [
            covered
            for item in records
            for coverage, covered in item.interval_coverage.items()
            if abs(
                coverage - profile.target_interval_coverage
            ) <= 1e-9
        ]
        interval_coverage = (
            None
            if not coverage_values
            else sum(coverage_values) / len(coverage_values)
        )
        interval_coverage_gap = (
            None
            if interval_coverage is None
            else interval_coverage
            - profile.target_interval_coverage
        )

        scenario_values = [
            item.scenario_hit is not None
            for item in records
        ]
        scenario_hit_rate = (
            None
            if not scenario_values
            else sum(scenario_values) / len(scenario_values)
        )

        eligible = len(records) >= profile.minimum_sample_size
        score = self._score(
            mae=mae,
            records=records,
            directional_accuracy=directional_accuracy,
            interval_coverage=interval_coverage,
            mean_relative_bias=mean_relative_bias,
            profile=profile,
        )
        grade = self._grade(score)

        return ForecastPerformanceMetrics(
            group_key=group_key,
            grouping=grouping,
            sample_size=len(records),
            evaluation_start=min(
                item.outcome.observation_date for item in records
            ),
            evaluation_end=max(
                item.outcome.observation_date for item in records
            ),
            mae=mae,
            mse=mse,
            rmse=rmse,
            mape=mape,
            smape=smape,
            mean_bias=mean_bias,
            mean_relative_bias=mean_relative_bias,
            directional_accuracy=directional_accuracy,
            interval_coverage=interval_coverage,
            interval_coverage_gap=interval_coverage_gap,
            scenario_hit_rate=scenario_hit_rate,
            score=score,
            grade=grade,
            eligible=eligible,
            explanation=(
                (
                    f"{group_key} produced MAE {mae:.6f} "
                    f"across {len(records)} outcomes."
                ),
                (
                    f"Directional accuracy is "
                    f"{self._format_optional_percent(directional_accuracy)}."
                ),
                (
                    f"Performance score is {score:.3f}, "
                    f"graded {grade.value}."
                ),
            ),
            metadata=dict(profile.metadata),
        )

    @staticmethod
    def _smape(
        record: ForecastValidationRecord,
    ) -> float | None:
        predicted = record.forecast.point_forecast
        observed = record.outcome.observed_value
        denominator = abs(predicted) + abs(observed)
        if denominator == 0:
            return None
        return 2.0 * abs(predicted - observed) / denominator

    @staticmethod
    def _score(
        *,
        mae: float,
        records: tuple[ForecastValidationRecord, ...],
        directional_accuracy: float | None,
        interval_coverage: float | None,
        mean_relative_bias: float | None,
        profile: PerformanceAnalyticsProfile,
    ) -> float:
        mean_reference = (
            sum(item.forecast.reference_value for item in records)
            / len(records)
        )
        normalized_mae = mae / max(abs(mean_reference), 1e-12)
        error_component = max(0.0, 1.0 - min(1.0, normalized_mae))

        direction_component = (
            0.5
            if directional_accuracy is None
            else directional_accuracy
        )
        coverage_component = (
            0.5
            if interval_coverage is None
            else max(
                0.0,
                1.0
                - abs(
                    interval_coverage
                    - profile.target_interval_coverage
                ),
            )
        )
        bias_component = (
            0.5
            if mean_relative_bias is None
            else max(
                0.0,
                1.0 - min(1.0, abs(mean_relative_bias)),
            )
        )

        score = (
            profile.error_weight * error_component
            + profile.direction_weight * direction_component
            + profile.coverage_weight * coverage_component
            + profile.bias_weight * bias_component
        )
        return min(1.0, max(0.0, score))

    @staticmethod
    def _grade(score: float) -> PerformanceGrade:
        if score >= 0.90:
            return PerformanceGrade.EXCELLENT
        if score >= 0.75:
            return PerformanceGrade.GOOD
        if score >= 0.60:
            return PerformanceGrade.FAIR
        if score >= 0.40:
            return PerformanceGrade.WEAK
        return PerformanceGrade.POOR

    @staticmethod
    def _rank(
        scorecards: tuple[ForecastPerformanceMetrics, ...],
    ) -> tuple[ForecastPerformanceRankingEntry, ...]:
        ordered = sorted(
            scorecards,
            key=lambda item: (
                not item.eligible,
                -item.score,
                item.mae,
                -item.sample_size,
                item.group_key,
            ),
        )
        return tuple(
            ForecastPerformanceRankingEntry(
                rank=index,
                group_key=item.group_key,
                grouping=item.grouping,
                score=item.score,
                grade=item.grade,
                sample_size=item.sample_size,
                mae=item.mae,
                directional_accuracy=item.directional_accuracy,
                interval_coverage=item.interval_coverage,
                eligible=item.eligible,
            )
            for index, item in enumerate(ordered, start=1)
        )

    @staticmethod
    def _top_group(
        rankings: tuple[ForecastPerformanceRankingEntry, ...],
    ) -> str:
        for item in rankings:
            if item.eligible:
                return item.group_key
        return "none"

    @staticmethod
    def _format_optional_percent(value: float | None) -> str:
        return "unavailable" if value is None else f"{value:.2%}"
