"""Formal end-to-end certification for Phase 5.3 capital allocation."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from hashlib import sha256
import io
import json

from .constraints import ConstraintContext, evaluate_allocation_constraints
from .contracts import (
    AllocationBounds, AllocationConstraint, AllocationConstraintType,
    AllocationRequest, CapitalPool, CapitalPoolType,
)
from .execution import build_execution_plan
from .explanations import AllocationAuditInput, build_allocation_explanation_audit
from .objectives import ObjectiveInputs, calculate_allocation_objective
from .optimizer import OptimizationCandidate, optimize_capital
from .serialization import (
    allocation_audit_csv, allocation_bundle_json, allocation_dashboard_csv,
    execution_dashboard_csv,
)
from .sizing import SizingInputs, size_opportunity
from .supply import ReserveRule, ReserveType, calculate_capital_supply


class CertificationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CertificationCheck:
    check_id: str
    status: CertificationStatus
    evidence: str


@dataclass(frozen=True)
class Phase53CertificationScenario:
    supply: object
    audit_inputs: tuple[AllocationAuditInput, ...]
    candidates: tuple[OptimizationCandidate, ...]
    start_date: date


@dataclass(frozen=True)
class Phase53CertificationReport:
    phase: str
    status: CertificationStatus
    allocation_batch_id: str
    certification_fingerprint: str | None
    checks: tuple[CertificationCheck, ...]

    @property
    def passed(self) -> bool:
        return self.status is CertificationStatus.PASSED

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "status": self.status.value,
            "allocation_batch_id": self.allocation_batch_id,
            "certification_fingerprint": self.certification_fingerprint,
            "checks": [
                {
                    "check_id": check.check_id,
                    "status": check.status.value,
                    "evidence": check.evidence,
                }
                for check in self.checks
            ],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent)


def _check(check_id: str, condition: bool, success: str, failure: str) -> CertificationCheck:
    return CertificationCheck(
        check_id,
        CertificationStatus.PASSED if condition else CertificationStatus.FAILED,
        success if condition else failure,
    )


def build_reference_certification_scenario() -> Phase53CertificationScenario:
    pool = CapitalPool("certification-pool", CapitalPoolType.ONE_TIME, 3000, 300)
    supply = calculate_capital_supply(
        pool,
        [ReserveRule("strategic-dry-powder", ReserveType.STRATEGIC_DRY_POWDER, 200)],
        unavailable_capital=100,
    )
    definitions = (
        ("BTC", "crypto", "crypto", 92, 100, 800, 1200, 90, 85, 90, 80),
        ("VOO", "etf", "etf", 88, 100, 700, 1000, 92, 82, 85, 90),
        ("GLD", "metals", "metals", 82, 50, 400, 600, 85, 75, 80, 82),
        ("MTG-BOX", "collectibles", "mtg", 75, 200, 500, 700, 72, 68, 70, 65),
    )
    audit_inputs = []
    candidates = []
    for (
        opportunity_id, asset_class, group_key, priority, minimum, target, maximum,
        confidence, action, diversification, efficiency,
    ) in definitions:
        request = AllocationRequest(
            f"request-{opportunity_id}", opportunity_id, "ranking-certification",
            priority, "P1", AllocationBounds(minimum, target, maximum),
            asset_class, group_key,
        )
        sizing = size_opportunity(
            SizingInputs(
                request, confidence, action, maximum, maximum, maximum, minimum
            ),
            supply,
        )
        rules = (
            AllocationConstraint(
                f"position-{opportunity_id}",
                AllocationConstraintType.MAXIMUM_POSITION,
                maximum,
                opportunity_id,
            ),
        )
        constraints = evaluate_allocation_constraints(
            request, sizing, supply, rules, ConstraintContext()
        )
        objective = calculate_allocation_objective(
            ObjectiveInputs(
                request, sizing, constraints, 85, diversification, 85, efficiency
            )
        )
        audit_inputs.append(AllocationAuditInput(request, sizing, constraints, objective))
        candidates.append(OptimizationCandidate(request, constraints, objective))
    return Phase53CertificationScenario(
        supply, tuple(audit_inputs), tuple(candidates), date(2026, 7, 18)
    )


def certify_phase_5_3(
    scenario: Phase53CertificationScenario | None = None,
) -> Phase53CertificationReport:
    scenario = scenario or build_reference_certification_scenario()
    checks: list[CertificationCheck] = []
    groups = {item.request.group_key for item in scenario.audit_inputs}
    checks.append(
        _check(
            "CROSS_ASSET_COVERAGE",
            len(groups) >= 4,
            f"Certified portfolio groups: {', '.join(sorted(groups))}.",
            "Certification requires at least four distinct portfolio groups.",
        )
    )
    timestamp = datetime(2026, 7, 18, tzinfo=timezone.utc)
    try:
        first = optimize_capital(
            "phase-5.3-certification", "ranking-certification", scenario.supply,
            scenario.candidates, created_at=timestamp,
        )
        repeated = optimize_capital(
            "phase-5.3-certification", "ranking-certification", scenario.supply,
            scenario.candidates, created_at=timestamp,
        )
        reversed_result = optimize_capital(
            "phase-5.3-certification", "ranking-certification", scenario.supply,
            reversed(scenario.candidates), created_at=timestamp,
        )
        plan = build_execution_plan(
            "phase-5.3-execution", first, scenario.start_date
        )
        audit = build_allocation_explanation_audit(
            scenario.audit_inputs, first, plan
        )
        bundle = allocation_bundle_json(first, plan, audit, indent=None)
    except Exception as exc:
        checks.append(
            CertificationCheck("PIPELINE_EXECUTION", CertificationStatus.FAILED, str(exc))
        )
        return Phase53CertificationReport(
            "5.3", CertificationStatus.FAILED, "phase-5.3-certification", None,
            tuple(checks),
        )
    checks.append(_check("PIPELINE_EXECUTION", True, "Full allocation pipeline executed.", ""))
    checks.append(
        _check(
            "DETERMINISM_AND_INPUT_ORDER",
            first == repeated and first == reversed_result,
            "Repeated and reversed-input optimization produced identical results.",
            "Optimization changed across repeated or reversed inputs.",
        )
    )
    capital = first.capital_result
    checks.append(
        _check(
            "CAPITAL_CONSERVATION",
            capital.gross_capital
            == capital.reserved_capital + capital.allocated_capital + capital.residual_capital,
            "Gross capital equals reserved, allocated, and residual capital.",
            "Capital conservation failed.",
        )
    )
    checks.append(
        _check(
            "RESERVE_PROTECTION",
            capital.reserved_capital
            == scenario.supply.unavailable_capital + scenario.supply.reserved_capital
            and capital.allocated_capital <= scenario.supply.deployable_capital,
            "Unavailable and reserved capital remained protected.",
            "Allocation consumed protected capital.",
        )
    )
    inputs_by_id = {item.request.opportunity_id: item for item in scenario.audit_inputs}
    bounds_valid = all(
        line.allocated_amount <= inputs_by_id[line.opportunity_id].constraints.effective_bounds.maximum_amount
        and (
            line.allocated_amount == 0
            or line.allocated_amount
            >= inputs_by_id[line.opportunity_id].constraints.effective_bounds.minimum_amount
        )
        for line in capital.lines
    )
    checks.append(
        _check(
            "CONSTRAINT_AND_MINIMUM_INTEGRITY",
            bounds_valid,
            "Every allocation respects effective maximums and atomic minimums.",
            "An allocation violated a bound or minimum purchase.",
        )
    )
    expected_order = tuple(
        item.request.opportunity_id
        for item in sorted(
            scenario.audit_inputs,
            key=lambda item: (-item.objective.objective_utility, item.request.opportunity_id),
        )
    )
    checks.append(
        _check(
            "OBJECTIVE_ORDERING",
            first.allocation_order == expected_order,
            "Allocation order follows objective utility and stable tie-breaking.",
            "Allocation order does not match certified objective ordering.",
        )
    )
    checks.append(
        _check(
            "EXECUTION_CONSERVATION",
            plan.purchase_total == capital.allocated_capital
            and plan.retained_cash == capital.residual_capital,
            "Execution purchases and retained cash match optimization totals.",
            "Execution plan does not conserve optimized capital.",
        )
    )
    expected_artifacts = len(scenario.audit_inputs) * 6
    checks.append(
        _check(
            "AUDIT_COMPLETENESS",
            len(audit.artifacts) == expected_artifacts
            and [artifact.sequence for artifact in audit.artifacts]
            == list(range(1, expected_artifacts + 1)),
            f"Preserved {expected_artifacts} ordered audit artifacts.",
            "Audit stages are missing, duplicated, or out of order.",
        )
    )
    try:
        payload = json.loads(bundle)
        allocation_rows = list(csv.DictReader(io.StringIO(allocation_dashboard_csv(first, audit))))
        execution_rows = list(csv.DictReader(io.StringIO(execution_dashboard_csv(plan))))
        audit_rows = list(csv.DictReader(io.StringIO(allocation_audit_csv(audit))))
        serialization_valid = (
            payload["schema_version"] == "5.3.9"
            and len(allocation_rows) == len(scenario.audit_inputs)
            and len(execution_rows) == len(plan.instructions)
            and len(audit_rows) == expected_artifacts
            and payload["capital_summary"]["allocated_capital"]
            == payload["execution_plan"]["purchase_total"]
        )
    except Exception:
        serialization_valid = False
    checks.append(
        _check(
            "SERIALIZATION_INTEGRITY",
            serialization_valid,
            "JSON and all dashboard CSV outputs passed integrity validation.",
            "One or more serialized outputs failed integrity validation.",
        )
    )
    status = (
        CertificationStatus.PASSED
        if all(check.status is CertificationStatus.PASSED for check in checks)
        else CertificationStatus.FAILED
    )
    fingerprint = sha256(bundle.encode("utf-8")).hexdigest()
    return Phase53CertificationReport(
        "5.3", status, capital.allocation_batch_id, fingerprint, tuple(checks)
    )
