"""Cross-asset validation contracts."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
from typing import Mapping

from .validation import validate_non_empty_text, validate_unit_interval


@dataclass(frozen=True, slots=True)
class AssetClassValidationSummary:
    """Comparable validation summary for one asset class and horizon."""

    asset_class: str
    model_id: str
    model_version: str
    horizon_days: int
    observation_count: int
    asset_count: int
    coverage_ratio: Decimal
    spearman: Decimal | None
    kendall: Decimal | None
    hit_rate: Decimal | None
    top_bottom_spread: Decimal | None
    mean_excess_return: Decimal | None
    information_ratio: Decimal | None
    benchmark_win_rate: Decimal | None
    calibration_error: Decimal | None
    limitations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in ("asset_class", "model_id", "model_version"):
            object.__setattr__(
                self,
                field_name,
                validate_non_empty_text(getattr(self, field_name), field_name),
            )
        if self.horizon_days <= 0:
            raise ValueError("horizon_days must be positive.")
        if self.observation_count <= 0:
            raise ValueError("observation_count must be positive.")
        if self.asset_count <= 0:
            raise ValueError("asset_count must be positive.")
        object.__setattr__(
            self,
            "coverage_ratio",
            validate_unit_interval(self.coverage_ratio, "coverage_ratio"),
        )
        object.__setattr__(
            self,
            "limitations",
            tuple(
                validate_non_empty_text(item, "limitation")
                for item in self.limitations
            ),
        )


@dataclass(frozen=True, slots=True)
class CrossAssetGrade:
    """Composite cross-asset validation grade."""

    asset_class: str
    horizon_days: int
    raw_score: Decimal
    adjusted_score: Decimal
    grade: str
    rank: int
    component_scores: Mapping[str, Decimal]
    penalties: Mapping[str, Decimal]
    limitations: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "asset_class",
            validate_non_empty_text(self.asset_class, "asset_class"),
        )
        object.__setattr__(
            self,
            "grade",
            validate_non_empty_text(self.grade, "grade"),
        )
        if self.rank < 1:
            raise ValueError("rank must be at least 1.")
        object.__setattr__(
            self,
            "component_scores",
            MappingProxyType(dict(self.component_scores)),
        )
        object.__setattr__(
            self,
            "penalties",
            MappingProxyType(dict(self.penalties)),
        )


@dataclass(frozen=True, slots=True)
class CrossAssetValidationReport:
    """Ranked cross-asset validation report."""

    horizon_days: int
    grades: tuple[CrossAssetGrade, ...]
    methodology_version: str
    warnings: tuple[str, ...] = ()
