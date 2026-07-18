"""Stable JSON and dashboard outputs for Phase 5.3 allocation."""

from __future__ import annotations

import csv
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
import io
import json
from typing import Mapping

from .execution import ContributionExecutionPlan
from .explanations import AllocationExplanationAuditResult
from .optimizer import CapitalOptimizationResult


ALLOCATION_COLUMNS = (
    "allocation_batch_id", "allocation_order", "opportunity_id", "allocated_amount",
    "effective_minimum", "effective_target", "effective_maximum", "unmet_amount",
    "allocation_status", "reason_codes", "binding_constraints", "objective_utility",
    "headline", "summary", "allocation_statement", "execution_statement",
)

EXECUTION_COLUMNS = (
    "plan_id", "allocation_batch_id", "sequence", "action", "opportunity_id",
    "amount", "cadence", "scheduled_date", "source_status", "reason_codes",
)

AUDIT_COLUMNS = (
    "allocation_batch_id", "sequence", "opportunity_id", "stage", "evidence_json",
)


def _jsonable(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def allocation_dashboard_rows(
    optimization: CapitalOptimizationResult,
    audit: AllocationExplanationAuditResult,
) -> tuple[dict[str, object], ...]:
    explanations = {item.opportunity_id: item for item in audit.explanations}
    if set(explanations) != set(optimization.allocation_order):
        raise ValueError("audit explanations must match optimization opportunities")
    rows = []
    for order, line in enumerate(optimization.capital_result.lines, start=1):
        explanation = explanations[line.opportunity_id]
        evidence = explanation.audit_evidence
        rows.append(
            {
                "allocation_batch_id": optimization.capital_result.allocation_batch_id,
                "allocation_order": order,
                "opportunity_id": line.opportunity_id,
                "allocated_amount": str(line.allocated_amount),
                "effective_minimum": evidence["effective_minimum"],
                "effective_target": evidence["effective_target"],
                "effective_maximum": evidence["effective_maximum"],
                "unmet_amount": evidence["unmet_amount"],
                "allocation_status": line.status.value,
                "reason_codes": "|".join(reason.value for reason in line.reason_codes),
                "binding_constraints": "|".join(line.binding_constraints),
                "objective_utility": evidence["objective_utility"],
                "headline": explanation.headline,
                "summary": explanation.summary,
                "allocation_statement": explanation.allocation_statement,
                "execution_statement": explanation.execution_statement,
            }
        )
    return tuple(rows)


def execution_dashboard_rows(
    plan: ContributionExecutionPlan,
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "plan_id": plan.plan_id,
            "allocation_batch_id": plan.allocation_batch_id,
            "sequence": instruction.sequence,
            "action": instruction.action.value,
            "opportunity_id": instruction.opportunity_id or "",
            "amount": str(instruction.amount),
            "cadence": instruction.cadence.value,
            "scheduled_date": instruction.scheduled_date.isoformat()
            if instruction.scheduled_date else "",
            "source_status": instruction.source_status,
            "reason_codes": "|".join(instruction.reason_codes),
        }
        for instruction in plan.instructions
    )


def allocation_audit_rows(
    audit: AllocationExplanationAuditResult,
) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "allocation_batch_id": audit.allocation_batch_id,
            "sequence": artifact.sequence,
            "opportunity_id": artifact.opportunity_id,
            "stage": artifact.stage,
            "evidence_json": json.dumps(
                _jsonable(artifact.evidence), sort_keys=True, separators=(",", ":")
            ),
        }
        for artifact in audit.artifacts
    )


def _csv(rows: tuple[dict[str, object], ...], columns: tuple[str, ...]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def allocation_dashboard_csv(
    optimization: CapitalOptimizationResult,
    audit: AllocationExplanationAuditResult,
) -> str:
    return _csv(allocation_dashboard_rows(optimization, audit), ALLOCATION_COLUMNS)


def execution_dashboard_csv(plan: ContributionExecutionPlan) -> str:
    return _csv(execution_dashboard_rows(plan), EXECUTION_COLUMNS)


def allocation_audit_csv(audit: AllocationExplanationAuditResult) -> str:
    return _csv(allocation_audit_rows(audit), AUDIT_COLUMNS)


def allocation_bundle_dict(
    optimization: CapitalOptimizationResult,
    plan: ContributionExecutionPlan,
    audit: AllocationExplanationAuditResult,
) -> dict[str, object]:
    capital = optimization.capital_result
    if plan.allocation_batch_id != capital.allocation_batch_id:
        raise ValueError("execution plan must match optimization batch")
    if audit.allocation_batch_id != capital.allocation_batch_id:
        raise ValueError("audit result must match optimization batch")
    return {
        "schema_version": "5.3.9",
        "allocation_batch_id": capital.allocation_batch_id,
        "ranking_batch_id": capital.ranking_batch_id,
        "capital_summary": {
            "pool_id": capital.pool_id,
            "gross_capital": str(capital.gross_capital),
            "reserved_capital": str(capital.reserved_capital),
            "allocated_capital": str(capital.allocated_capital),
            "residual_capital": str(capital.residual_capital),
            "objective_value": str(optimization.objective_value),
            "created_at": capital.created_at.isoformat(),
        },
        "batch_evidence": _jsonable(audit.batch_evidence),
        "allocations": list(allocation_dashboard_rows(optimization, audit)),
        "execution_plan": {
            "plan_id": plan.plan_id,
            "start_date": plan.start_date.isoformat(),
            "purchase_total": str(plan.purchase_total),
            "retained_cash": str(plan.retained_cash),
            "instructions": list(execution_dashboard_rows(plan)),
        },
        "audit_records": list(allocation_audit_rows(audit)),
    }


def allocation_bundle_json(
    optimization: CapitalOptimizationResult,
    plan: ContributionExecutionPlan,
    audit: AllocationExplanationAuditResult,
    *,
    indent: int | None = 2,
) -> str:
    return json.dumps(
        allocation_bundle_dict(optimization, plan, audit),
        sort_keys=True,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )
