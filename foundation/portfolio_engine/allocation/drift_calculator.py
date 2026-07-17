"""Allocation drift and band classification."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class AllocationStatus(StrEnum):
    UNDERWEIGHT = "underweight"
    WITHIN_BAND = "within_band"
    OVERWEIGHT = "overweight"
    UNCONFIGURED = "unconfigured"
    NO_VALUE = "no_value"


@dataclass(slots=True)
class DriftResult:
    actual_weight: Decimal
    target_weight: Decimal
    minimum_weight: Decimal
    maximum_weight: Decimal
    percentage_point_drift: Decimal
    relative_drift: Decimal
    target_value: Decimal
    dollar_variance: Decimal
    status: AllocationStatus


def calculate_drift(
    *,
    actual_value: Decimal,
    total_value: Decimal,
    target_weight: Decimal,
    minimum_weight: Decimal,
    maximum_weight: Decimal,
) -> DriftResult:
    actual_value = Decimal(str(actual_value))
    total_value = Decimal(str(total_value))
    target_weight = Decimal(str(target_weight))
    minimum_weight = Decimal(str(minimum_weight))
    maximum_weight = Decimal(str(maximum_weight))

    actual_weight = (
        Decimal("0") if total_value == 0 else actual_value / total_value
    )
    drift = actual_weight - target_weight
    relative = Decimal("0") if target_weight == 0 else drift / target_weight
    target_value = total_value * target_weight
    dollar_variance = actual_value - target_value

    if total_value == 0:
        status = AllocationStatus.NO_VALUE
    elif actual_weight < minimum_weight:
        status = AllocationStatus.UNDERWEIGHT
    elif actual_weight > maximum_weight:
        status = AllocationStatus.OVERWEIGHT
    else:
        status = AllocationStatus.WITHIN_BAND

    return DriftResult(
        actual_weight=actual_weight,
        target_weight=target_weight,
        minimum_weight=minimum_weight,
        maximum_weight=maximum_weight,
        percentage_point_drift=drift,
        relative_drift=relative,
        target_value=target_value,
        dollar_variance=dollar_variance,
        status=status,
    )
