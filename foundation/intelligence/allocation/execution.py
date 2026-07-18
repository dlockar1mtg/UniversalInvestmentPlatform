"""Contribution schedules and execution plans for optimized capital."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_FLOOR
from enum import Enum

from .optimizer import CapitalOptimizationResult


def _decimal(value, name: str) -> Decimal:
    converted = Decimal(str(value))
    if not converted.is_finite() or converted < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return converted


def _floor(value: Decimal, quantum: Decimal) -> Decimal:
    return (value / quantum).to_integral_value(rounding=ROUND_FLOOR) * quantum


class ExecutionAction(str, Enum):
    PURCHASE = "PURCHASE"
    DEFER = "DEFER"
    HOLD_CASH = "HOLD_CASH"


class ExecutionCadence(str, Enum):
    IMMEDIATE = "IMMEDIATE"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    NONE = "NONE"


@dataclass(frozen=True)
class ExecutionPlanningPolicy:
    immediate_fraction: Decimal | float | int | str = Decimal("1")
    recurring_periods: int = 0
    recurring_cadence: ExecutionCadence = ExecutionCadence.MONTHLY
    money_quantum: Decimal | float | int | str = Decimal("0.01")

    def __post_init__(self) -> None:
        fraction = _decimal(self.immediate_fraction, "immediate_fraction")
        quantum = _decimal(self.money_quantum, "money_quantum")
        if fraction > 1:
            raise ValueError("immediate_fraction must be between 0 and 1")
        if quantum == 0:
            raise ValueError("money_quantum must be positive")
        if self.recurring_periods < 0:
            raise ValueError("recurring_periods must be non-negative")
        if fraction < 1 and self.recurring_periods < 1:
            raise ValueError("recurring_periods must be positive when capital is staged")
        if self.recurring_cadence not in {ExecutionCadence.WEEKLY, ExecutionCadence.MONTHLY}:
            raise ValueError("recurring_cadence must be WEEKLY or MONTHLY")
        object.__setattr__(self, "immediate_fraction", fraction)
        object.__setattr__(self, "money_quantum", quantum)


@dataclass(frozen=True)
class ExecutionInstruction:
    sequence: int
    action: ExecutionAction
    opportunity_id: str | None
    amount: Decimal
    cadence: ExecutionCadence
    scheduled_date: date | None
    source_status: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class ContributionExecutionPlan:
    plan_id: str
    allocation_batch_id: str
    start_date: date
    purchase_total: Decimal
    retained_cash: Decimal
    instructions: tuple[ExecutionInstruction, ...]

    def __post_init__(self) -> None:
        purchase_sum = sum(
            (item.amount for item in self.instructions if item.action is ExecutionAction.PURCHASE),
            Decimal("0"),
        )
        hold_sum = sum(
            (item.amount for item in self.instructions if item.action is ExecutionAction.HOLD_CASH),
            Decimal("0"),
        )
        if purchase_sum != self.purchase_total:
            raise ValueError("purchase_total must equal purchase instruction total")
        if hold_sum != self.retained_cash:
            raise ValueError("retained_cash must equal hold-cash instruction total")


def _add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _scheduled_date(start: date, period: int, cadence: ExecutionCadence) -> date:
    if cadence is ExecutionCadence.WEEKLY:
        return start + timedelta(days=7 * period)
    return _add_months(start, period)


def _installments(amount: Decimal, periods: int, quantum: Decimal) -> tuple[Decimal, ...]:
    base = _floor(amount / periods, quantum)
    values = [base for _ in range(periods)]
    values[-1] += amount - sum(values, Decimal("0"))
    return tuple(values)


def build_execution_plan(
    plan_id: str,
    optimization: CapitalOptimizationResult,
    start_date: date,
    policy: ExecutionPlanningPolicy = ExecutionPlanningPolicy(),
) -> ContributionExecutionPlan:
    """Translate optimized allocation lines into a conserved execution plan."""
    if not plan_id.strip():
        raise ValueError("plan_id must not be blank")
    pending: list[tuple[date | None, int, ExecutionInstruction]] = []
    line_order = {
        opportunity_id: index
        for index, opportunity_id in enumerate(optimization.allocation_order)
    }
    for line in optimization.capital_result.lines:
        reasons = tuple(reason.value for reason in line.reason_codes)
        order = line_order[line.opportunity_id]
        if line.allocated_amount == 0:
            pending.append(
                (
                    None,
                    order,
                    ExecutionInstruction(
                        0, ExecutionAction.DEFER, line.opportunity_id, Decimal("0"),
                        ExecutionCadence.NONE, None, line.status.value, reasons,
                    ),
                )
            )
            continue
        immediate = _floor(
            line.allocated_amount * policy.immediate_fraction, policy.money_quantum
        )
        staged = line.allocated_amount - immediate
        if immediate > 0:
            pending.append(
                (
                    start_date,
                    order,
                    ExecutionInstruction(
                        0, ExecutionAction.PURCHASE, line.opportunity_id, immediate,
                        ExecutionCadence.IMMEDIATE, start_date, line.status.value, reasons,
                    ),
                )
            )
        if staged > 0:
            for period, amount in enumerate(
                _installments(staged, policy.recurring_periods, policy.money_quantum), start=1
            ):
                scheduled = _scheduled_date(start_date, period, policy.recurring_cadence)
                pending.append(
                    (
                        scheduled,
                        order,
                        ExecutionInstruction(
                            0, ExecutionAction.PURCHASE, line.opportunity_id, amount,
                            policy.recurring_cadence, scheduled, line.status.value, reasons,
                        ),
                    )
                )

    residual = optimization.capital_result.residual_capital
    if residual > 0:
        pending.append(
            (
                start_date,
                len(line_order),
                ExecutionInstruction(
                    0, ExecutionAction.HOLD_CASH, None, residual,
                    ExecutionCadence.NONE, start_date, "RESIDUAL", ("RETAINED_RESIDUAL",),
                ),
            )
        )
    pending.sort(
        key=lambda item: (
            item[0] is None,
            item[0] or date.max,
            item[1],
            item[2].action.value,
        )
    )
    instructions = tuple(
        ExecutionInstruction(
            sequence,
            instruction.action,
            instruction.opportunity_id,
            instruction.amount,
            instruction.cadence,
            instruction.scheduled_date,
            instruction.source_status,
            instruction.reason_codes,
        )
        for sequence, (_, _, instruction) in enumerate(pending, start=1)
    )
    purchase_total = sum(
        (item.amount for item in instructions if item.action is ExecutionAction.PURCHASE),
        Decimal("0"),
    )
    if purchase_total != optimization.capital_result.allocated_capital:
        raise ValueError("execution purchases must conserve optimized allocated capital")
    return ContributionExecutionPlan(
        plan_id,
        optimization.capital_result.allocation_batch_id,
        start_date,
        purchase_total,
        residual,
        instructions,
    )
