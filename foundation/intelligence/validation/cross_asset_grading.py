"""Cross-asset grading methodology."""

from __future__ import annotations

from decimal import Decimal

from .cross_asset_contracts import AssetClassValidationSummary, CrossAssetGrade


WEIGHTS = {
    "spearman": Decimal("0.20"),
    "hit_rate": Decimal("0.15"),
    "top_bottom_spread": Decimal("0.15"),
    "mean_excess_return": Decimal("0.15"),
    "information_ratio": Decimal("0.15"),
    "benchmark_win_rate": Decimal("0.10"),
    "calibration": Decimal("0.10"),
}


def _clamp(value: Decimal, minimum: Decimal, maximum: Decimal) -> Decimal:
    return min(max(value, minimum), maximum)


def _normalize_spearman(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("50")
    return _clamp((value + Decimal("1")) * Decimal("50"), Decimal("0"), Decimal("100"))


def _normalize_probability(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("50")
    return _clamp(value * Decimal("100"), Decimal("0"), Decimal("100"))


def _normalize_spread(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("50")
    return _clamp(Decimal("50") + value * Decimal("250"), Decimal("0"), Decimal("100"))


def _normalize_excess_return(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("50")
    return _clamp(Decimal("50") + value * Decimal("500"), Decimal("0"), Decimal("100"))


def _normalize_information_ratio(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("50")
    return _clamp(Decimal("50") + value * Decimal("25"), Decimal("0"), Decimal("100"))


def _normalize_calibration_error(value: Decimal | None) -> Decimal:
    if value is None:
        return Decimal("50")
    return _clamp((Decimal("1") - value) * Decimal("100"), Decimal("0"), Decimal("100"))


def _letter_grade(score: Decimal) -> str:
    if score >= Decimal("93"):
        return "A+"
    if score >= Decimal("90"):
        return "A"
    if score >= Decimal("87"):
        return "A-"
    if score >= Decimal("83"):
        return "B+"
    if score >= Decimal("80"):
        return "B"
    if score >= Decimal("77"):
        return "B-"
    if score >= Decimal("73"):
        return "C+"
    if score >= Decimal("70"):
        return "C"
    if score >= Decimal("67"):
        return "C-"
    if score >= Decimal("60"):
        return "D"
    return "F"


def grade_asset_class(
    summary: AssetClassValidationSummary,
    *,
    rank: int = 1,
) -> CrossAssetGrade:
    """Convert standardized validation metrics into a comparable grade."""
    components = {
        "spearman": _normalize_spearman(summary.spearman),
        "hit_rate": _normalize_probability(summary.hit_rate),
        "top_bottom_spread": _normalize_spread(summary.top_bottom_spread),
        "mean_excess_return": _normalize_excess_return(summary.mean_excess_return),
        "information_ratio": _normalize_information_ratio(summary.information_ratio),
        "benchmark_win_rate": _normalize_probability(summary.benchmark_win_rate),
        "calibration": _normalize_calibration_error(summary.calibration_error),
    }
    raw_score = sum(
        components[name] * weight
        for name, weight in WEIGHTS.items()
    )

    penalties: dict[str, Decimal] = {}
    if summary.coverage_ratio < Decimal("0.80"):
        penalties["coverage"] = (
            Decimal("0.80") - summary.coverage_ratio
        ) * Decimal("50")
    if summary.observation_count < 100:
        penalties["sample_size"] = (
            Decimal(100 - summary.observation_count) / Decimal("100")
        ) * Decimal("10")
    if summary.asset_count < 5:
        penalties["asset_breadth"] = (
            Decimal(5 - summary.asset_count) / Decimal("5")
        ) * Decimal("10")

    adjusted_score = max(
        Decimal("0"),
        raw_score - sum(penalties.values(), Decimal("0")),
    )

    return CrossAssetGrade(
        asset_class=summary.asset_class,
        horizon_days=summary.horizon_days,
        raw_score=raw_score,
        adjusted_score=adjusted_score,
        grade=_letter_grade(adjusted_score),
        rank=rank,
        component_scores=components,
        penalties=penalties,
        limitations=summary.limitations,
    )
