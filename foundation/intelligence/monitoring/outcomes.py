"""Execution, allocation, and outcome reconciliation for Phase 5.5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from typing import Iterable


def _amount(value: object, name: str) -> Decimal:
    converted = Decimal(str(value))
    if not converted.is_finite() or converted < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return converted


def _score(value: object | None, name: str) -> Decimal | None:
    if value is None:
        return None
    converted = _amount(value, name)
    if converted > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return converted


class OutcomeMonitoringStatus(str, Enum):
    ON_TRACK = "ON_TRACK"
    UNDER_EXECUTED = "UNDER_EXECUTED"
    OVER_EXECUTED = "OVER_EXECUTED"
    NOT_EXECUTED = "NOT_EXECUTED"
    POSITION_MISMATCH = "POSITION_MISMATCH"
    UNPLANNED_ACTIVITY = "UNPLANNED_ACTIVITY"


class OutcomeReasonCode(str, Enum):
    EXECUTION_MATCHED = "EXECUTION_MATCHED"
    EXECUTION_SHORTFALL = "EXECUTION_SHORTFALL"
    EXECUTION_EXCESS = "EXECUTION_EXCESS"
    EXECUTION_MISSING = "EXECUTION_MISSING"
    POSITION_RECONCILIATION_FAILED = "POSITION_RECONCILIATION_FAILED"
    TARGET_SHORTFALL = "TARGET_SHORTFALL"
    OBJECTIVE_DETERIORATION = "OBJECTIVE_DETERIORATION"
    UNPLANNED_EXECUTION = "UNPLANNED_EXECUTION"


@dataclass(frozen=True)
class PlannedAllocationOutcome:
    opportunity_id: str
    planned_amount: Decimal | float | int | str
    target_position_amount: Decimal | float | int | str
    baseline_position_amount: Decimal | float | int | str = Decimal("0")
    planned_objective_score: Decimal | float | int | str | None = None

    def __post_init__(self) -> None:
        if not self.opportunity_id.strip():
            raise ValueError("opportunity_id must not be blank")
        for name in ("planned_amount", "target_position_amount", "baseline_position_amount"):
            object.__setattr__(self, name, _amount(getattr(self, name), name))
        object.__setattr__(
            self, "planned_objective_score",
            _score(self.planned_objective_score, "planned_objective_score"),
        )


@dataclass(frozen=True)
class AllocationOutcomePlan:
    source_run_id: str
    source_output_fingerprint: str
    currency: str
    gross_capital: Decimal | float | int | str
    protected_capital: Decimal | float | int | str
    planned_residual_capital: Decimal | float | int | str
    allocations: tuple[PlannedAllocationOutcome, ...]

    def __post_init__(self) -> None:
        for name in ("source_run_id", "source_output_fingerprint", "currency"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        for name in ("gross_capital", "protected_capital", "planned_residual_capital"):
            object.__setattr__(self, name, _amount(getattr(self, name), name))
        identifiers = [item.opportunity_id for item in self.allocations]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("planned opportunity_id values must be unique")
        allocated = sum((item.planned_amount for item in self.allocations), Decimal("0"))
        if self.gross_capital != self.protected_capital + allocated + self.planned_residual_capital:
            raise ValueError("planned capital must satisfy gross = protected + allocated + residual")

    @property
    def planned_allocation_total(self) -> Decimal:
        return sum((item.planned_amount for item in self.allocations), Decimal("0"))


@dataclass(frozen=True)
class ObservedAllocationOutcome:
    observation_id: str
    opportunity_id: str
    observed_at: datetime
    executed_amount: Decimal | float | int | str
    current_position_amount: Decimal | float | int | str
    observed_objective_score: Decimal | float | int | str | None = None

    def __post_init__(self) -> None:
        if not self.observation_id.strip() or not self.opportunity_id.strip():
            raise ValueError("observation_id and opportunity_id must not be blank")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        for name in ("executed_amount", "current_position_amount"):
            object.__setattr__(self, name, _amount(getattr(self, name), name))
        object.__setattr__(
            self, "observed_objective_score",
            _score(self.observed_objective_score, "observed_objective_score"),
        )


@dataclass(frozen=True)
class OutcomeMonitoringPolicy:
    amount_tolerance: Decimal | float | int | str = Decimal("0.01")
    relative_tolerance: Decimal | float | int | str = Decimal("0")
    objective_score_tolerance: Decimal | float | int | str = Decimal("5")
    protected_capital_tolerance: Decimal | float | int | str = Decimal("0.01")
    residual_capital_tolerance: Decimal | float | int | str = Decimal("0.01")

    def __post_init__(self) -> None:
        for name in (
            "amount_tolerance", "relative_tolerance", "objective_score_tolerance",
            "protected_capital_tolerance", "residual_capital_tolerance",
        ):
            object.__setattr__(self, name, _amount(getattr(self, name), name))
        if self.relative_tolerance > 1:
            raise ValueError("relative_tolerance must be between 0 and 1")


@dataclass(frozen=True)
class AllocationOutcomeLine:
    opportunity_id: str
    planned_amount: Decimal
    executed_amount: Decimal
    execution_variance: Decimal
    expected_position_amount: Decimal
    current_position_amount: Decimal
    position_variance: Decimal
    target_shortfall: Decimal
    objective_variance: Decimal | None
    status: OutcomeMonitoringStatus
    reason_codes: tuple[OutcomeReasonCode, ...]
    observation_id: str | None


@dataclass(frozen=True)
class AllocationOutcomeMonitoringResult:
    source_run_id: str
    source_output_fingerprint: str
    currency: str
    lines: tuple[AllocationOutcomeLine, ...]
    planned_allocation_total: Decimal
    executed_total: Decimal
    execution_variance: Decimal
    observed_protected_capital: Decimal
    protected_capital_variance: Decimal
    observed_residual_capital: Decimal
    residual_capital_variance: Decimal
    observed_capital_variance: Decimal
    result_fingerprint: str


def _latest_observations(
    observations: Iterable[ObservedAllocationOutcome],
) -> dict[str, ObservedAllocationOutcome]:
    materialized = tuple(observations)
    identifiers = [item.observation_id for item in materialized]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("observation_id values must be unique")
    latest: dict[str, ObservedAllocationOutcome] = {}
    for item in materialized:
        current = latest.get(item.opportunity_id)
        if current is None or (item.observed_at, item.observation_id) > (
            current.observed_at, current.observation_id
        ):
            latest[item.opportunity_id] = item
    return latest


def _allowed(planned: Decimal, policy: OutcomeMonitoringPolicy) -> Decimal:
    return max(policy.amount_tolerance, planned * policy.relative_tolerance)


def monitor_allocation_outcomes(
    plan: AllocationOutcomePlan,
    observations: Iterable[ObservedAllocationOutcome],
    *,
    observed_protected_capital: Decimal | float | int | str,
    observed_residual_capital: Decimal | float | int | str,
    policy: OutcomeMonitoringPolicy = OutcomeMonitoringPolicy(),
) -> AllocationOutcomeMonitoringResult:
    """Reconcile latest observed outcomes against one immutable allocation plan."""
    protected = _amount(observed_protected_capital, "observed_protected_capital")
    residual = _amount(observed_residual_capital, "observed_residual_capital")
    latest = _latest_observations(observations)
    planned = {item.opportunity_id: item for item in plan.allocations}
    identifiers = sorted(set(planned) | set(latest))
    lines: list[AllocationOutcomeLine] = []

    for opportunity_id in identifiers:
        target = planned.get(opportunity_id)
        actual = latest.get(opportunity_id)
        planned_amount = target.planned_amount if target else Decimal("0")
        baseline_position = target.baseline_position_amount if target else Decimal("0")
        target_position = target.target_position_amount if target else Decimal("0")
        executed = actual.executed_amount if actual else Decimal("0")
        current_position = actual.current_position_amount if actual else baseline_position
        execution_variance = executed - planned_amount
        expected_position = baseline_position + executed
        position_variance = current_position - expected_position
        target_shortfall = max(Decimal("0"), target_position - current_position)
        objective_variance = None
        if (
            target and target.planned_objective_score is not None
            and actual and actual.observed_objective_score is not None
        ):
            objective_variance = actual.observed_objective_score - target.planned_objective_score

        tolerance = _allowed(planned_amount, policy)
        reasons: list[OutcomeReasonCode] = []
        if target is None:
            status = OutcomeMonitoringStatus.UNPLANNED_ACTIVITY
            reasons.append(OutcomeReasonCode.UNPLANNED_EXECUTION)
        elif actual is None or (planned_amount > tolerance and executed == 0):
            status = OutcomeMonitoringStatus.NOT_EXECUTED
            reasons.append(OutcomeReasonCode.EXECUTION_MISSING)
        elif execution_variance < -tolerance:
            status = OutcomeMonitoringStatus.UNDER_EXECUTED
            reasons.append(OutcomeReasonCode.EXECUTION_SHORTFALL)
        elif execution_variance > tolerance:
            status = OutcomeMonitoringStatus.OVER_EXECUTED
            reasons.append(OutcomeReasonCode.EXECUTION_EXCESS)
        elif abs(position_variance) > policy.amount_tolerance:
            status = OutcomeMonitoringStatus.POSITION_MISMATCH
            reasons.append(OutcomeReasonCode.POSITION_RECONCILIATION_FAILED)
        else:
            status = OutcomeMonitoringStatus.ON_TRACK
            reasons.append(OutcomeReasonCode.EXECUTION_MATCHED)
        if target_shortfall > policy.amount_tolerance:
            reasons.append(OutcomeReasonCode.TARGET_SHORTFALL)
        if (
            objective_variance is not None
            and objective_variance < -policy.objective_score_tolerance
        ):
            reasons.append(OutcomeReasonCode.OBJECTIVE_DETERIORATION)

        lines.append(AllocationOutcomeLine(
            opportunity_id, planned_amount, executed, execution_variance,
            expected_position, current_position, position_variance, target_shortfall,
            objective_variance, status, tuple(dict.fromkeys(reasons)),
            actual.observation_id if actual else None,
        ))

    planned_total = plan.planned_allocation_total
    executed_total = sum((item.executed_amount for item in lines), Decimal("0"))
    execution_variance = executed_total - planned_total
    protected_variance = protected - plan.protected_capital
    residual_variance = residual - plan.planned_residual_capital
    observed_capital_variance = (
        plan.gross_capital - protected - executed_total - residual
    )
    payload = {
        "source_run_id": plan.source_run_id,
        "source_output_fingerprint": plan.source_output_fingerprint,
        "currency": plan.currency,
        "lines": [
            {
                "opportunity_id": item.opportunity_id,
                "planned_amount": str(item.planned_amount),
                "executed_amount": str(item.executed_amount),
                "execution_variance": str(item.execution_variance),
                "expected_position_amount": str(item.expected_position_amount),
                "current_position_amount": str(item.current_position_amount),
                "position_variance": str(item.position_variance),
                "target_shortfall": str(item.target_shortfall),
                "objective_variance": str(item.objective_variance) if item.objective_variance is not None else None,
                "status": item.status.value,
                "reason_codes": [reason.value for reason in item.reason_codes],
                "observation_id": item.observation_id,
            }
            for item in lines
        ],
        "planned_allocation_total": str(planned_total),
        "executed_total": str(executed_total),
        "execution_variance": str(execution_variance),
        "observed_protected_capital": str(protected),
        "protected_capital_variance": str(protected_variance),
        "observed_residual_capital": str(residual),
        "residual_capital_variance": str(residual_variance),
        "observed_capital_variance": str(observed_capital_variance),
    }
    fingerprint = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return AllocationOutcomeMonitoringResult(
        plan.source_run_id, plan.source_output_fingerprint, plan.currency,
        tuple(lines), planned_total, executed_total, execution_variance,
        protected, protected_variance, residual, residual_variance,
        observed_capital_variance, fingerprint,
    )
