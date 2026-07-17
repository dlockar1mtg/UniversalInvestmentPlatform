"""Threshold-based validation certification."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from .cross_asset_contracts import AssetClassValidationSummary
from .validation_profile import ValidationProfile


@dataclass(frozen=True, slots=True)
class ThresholdEvaluation:
    """Evaluation of one configured validation threshold."""

    metric_name: str
    observed_value: Decimal | None
    required_value: Decimal
    passed: bool
    message: str


@dataclass(frozen=True, slots=True)
class ModelCertificationDecision:
    """Pass/fail certification decision for one model and horizon."""

    asset_class: str
    model_id: str
    model_version: str
    horizon_days: int
    passed: bool
    evaluations: Mapping[str, ThresholdEvaluation]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evaluations",
            MappingProxyType(dict(self.evaluations)),
        )


_METRIC_MAP = {
    "spearman_rank_correlation": "spearman",
    "kendall_rank_correlation": "kendall",
    "hit_rate": "hit_rate",
    "top_bottom_spread": "top_bottom_spread",
    "mean_excess_return": "mean_excess_return",
    "information_ratio": "information_ratio",
    "benchmark_win_rate": "benchmark_win_rate",
}


def evaluate_model_certification(
    summary: AssetClassValidationSummary,
    profile: ValidationProfile,
) -> ModelCertificationDecision:
    """Evaluate validation metrics and sample requirements against a profile."""
    evaluations: dict[str, ThresholdEvaluation] = {}
    warnings: list[str] = []

    sample_checks = {
        "minimum_observations": (
            Decimal(summary.observation_count),
            Decimal(profile.minimum_observations),
        ),
        "minimum_assets": (
            Decimal(summary.asset_count),
            Decimal(profile.minimum_assets),
        ),
        "minimum_date_coverage": (
            summary.coverage_ratio,
            profile.minimum_date_coverage,
        ),
    }

    for name, (observed, required) in sample_checks.items():
        passed = observed >= required
        evaluations[name] = ThresholdEvaluation(
            metric_name=name,
            observed_value=observed,
            required_value=required,
            passed=passed,
            message=(
                f"{name}: observed {observed}, required at least {required}."
            ),
        )

    for threshold_name, required in profile.thresholds.items():
        attribute_name = _METRIC_MAP.get(threshold_name, threshold_name)
        observed = getattr(summary, attribute_name, None)
        if observed is None:
            passed = False
            warnings.append(
                f"Metric unavailable for certification: {threshold_name}."
            )
        else:
            passed = observed >= required
        evaluations[threshold_name] = ThresholdEvaluation(
            metric_name=threshold_name,
            observed_value=observed,
            required_value=required,
            passed=passed,
            message=(
                f"{threshold_name}: observed {observed}, "
                f"required at least {required}."
            ),
        )

    passed = all(item.passed for item in evaluations.values())
    warnings.extend(summary.limitations)

    return ModelCertificationDecision(
        asset_class=summary.asset_class,
        model_id=summary.model_id,
        model_version=summary.model_version,
        horizon_days=summary.horizon_days,
        passed=passed,
        evaluations=evaluations,
        warnings=tuple(dict.fromkeys(warnings)),
    )
