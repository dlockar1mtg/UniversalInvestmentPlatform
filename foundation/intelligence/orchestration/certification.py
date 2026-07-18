"""Formal cross-asset certification for Phase 5.4 decision orchestration."""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
import io
import json

from foundation.intelligence.ranking.competition import CompetitionPolicy

from .contracts import (
    CapitalInput,
    OrchestrationOpportunity,
    OrchestrationPolicyBundle,
    OrchestrationRunStatus,
    OrchestrationStage,
    PortfolioSnapshot,
    StageStatus,
    UniversalRunRequest,
)
from .orchestrator import OrchestrationEnginePolicy, run_universal_orchestration
from .outputs import build_unified_output, validate_unified_output
from .registry import InMemoryRunRegistry, RecoveryAction


class CertificationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CertificationCheck:
    check_id: str
    status: CertificationStatus
    evidence: str


@dataclass(frozen=True)
class Phase54CertificationScenario:
    request: UniversalRunRequest
    policy: OrchestrationEnginePolicy
    expected_groups: tuple[str, ...]
    quarantined_opportunity_id: str


@dataclass(frozen=True)
class Phase54CertificationReport:
    phase: str
    status: CertificationStatus
    run_id: str
    certification_fingerprint: str | None
    checks: tuple[CertificationCheck, ...]

    @property
    def passed(self) -> bool:
        return self.status is CertificationStatus.PASSED

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "status": self.status.value,
            "run_id": self.run_id,
            "certification_fingerprint": self.certification_fingerprint,
            "checks": [
                {"check_id": item.check_id, "status": item.status.value, "evidence": item.evidence}
                for item in self.checks
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


def _opportunity(
    opportunity_id: str,
    asset_class: str,
    group_key: str,
    priority_score: int,
    maximum: int,
    *,
    valid: bool = True,
) -> OrchestrationOpportunity:
    payload = {
        "priority_score": priority_score,
        "priority_tier": "P1" if priority_score >= 85 else "P2",
        "factor_scores": {
            "confidence": min(100, priority_score + 2),
            "capacity": min(100, priority_score),
            "diversification": 80,
        },
        "portfolio_context": {"group": group_key},
        "allocation_bounds": {
            "minimum_amount": 100,
            "target_amount": maximum * 3 // 4,
            "maximum_amount": maximum,
        },
        "sizing_inputs": {
            "confidence_score": min(100, priority_score + 2),
            "action_strength_score": priority_score,
            "portfolio_gap_amount": maximum,
            "opportunity_capacity_amount": maximum,
            "liquidity_capacity_amount": maximum,
            "minimum_purchase_amount": 100,
        },
        "objective_inputs": {
            "target_gap_score": 85,
            "diversification_score": 80,
            "liquidity_score": 85,
            "capital_efficiency_score": 82,
        },
    }
    if not valid:
        payload.pop("sizing_inputs")
    return OrchestrationOpportunity(
        opportunity_id,
        f"decision-{opportunity_id}",
        asset_class,
        group_key,
        source_payload=payload,
    )


def build_reference_certification_scenario() -> Phase54CertificationScenario:
    timestamp = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)
    opportunities = (
        _opportunity("BTC", "crypto", "crypto", 94, 1200),
        _opportunity("VOO", "etf", "etf", 90, 1100),
        _opportunity("GLD", "metals", "metals", 84, 800),
        _opportunity("MTG-BOX", "collectibles", "mtg", 78, 700),
        _opportunity("INVALID-HANDOFF", "other", "quarantine", 76, 500, valid=False),
    )
    request = UniversalRunRequest(
        "phase-5.4-certification",
        timestamp,
        "phase-5.4-source-decisions",
        PortfolioSnapshot("phase-5.4-portfolio", timestamp, ()),
        CapitalInput(5000, 500, 200),
        opportunities,
        OrchestrationPolicyBundle(
            "phase-5.4-certification-policy",
            ranking_policy={"max_selected": 5},
            failure_policy={"opportunity_failure": "QUARANTINE"},
        ),
    )
    return Phase54CertificationScenario(
        request,
        OrchestrationEnginePolicy(CompetitionPolicy(max_selected=5)),
        ("crypto", "etf", "metals", "mtg"),
        "INVALID-HANDOFF",
    )


def certify_phase_5_4(
    scenario: Phase54CertificationScenario | None = None,
) -> Phase54CertificationReport:
    scenario = scenario or build_reference_certification_scenario()
    request = scenario.request
    checks: list[CertificationCheck] = []
    groups = {item.group_key for item in request.opportunities}
    coverage = set(scenario.expected_groups).issubset(groups)
    checks.append(_check(
        "CROSS_ASSET_COVERAGE", coverage,
        f"Certified portfolio groups: {', '.join(scenario.expected_groups)}.",
        "Certification scenario lacks one or more required portfolio groups.",
    ))

    try:
        first = run_universal_orchestration(request, scenario.policy)
        repeated = run_universal_orchestration(request, scenario.policy)
        reversed_request = replace(request, opportunities=tuple(reversed(request.opportunities)))
        reversed_result = run_universal_orchestration(reversed_request, scenario.policy)
        package = build_unified_output(first, indent=None)
        validate_unified_output(package)
    except Exception as exc:
        checks.append(CertificationCheck(
            "PIPELINE_EXECUTION", CertificationStatus.FAILED, str(exc)
        ))
        return Phase54CertificationReport(
            "5.4", CertificationStatus.FAILED, request.run_id, None, tuple(checks)
        )
    if (
        first.ranking is None
        or first.optimization is None
        or first.execution_plan is None
        or first.run.status is OrchestrationRunStatus.FAILED
    ):
        evidence = (
            first.run.quarantined[0].message
            if first.run.quarantined
            else "Orchestration did not produce terminal ranking, allocation, and execution outputs."
        )
        checks.append(CertificationCheck(
            "PIPELINE_EXECUTION", CertificationStatus.FAILED, evidence
        ))
        return Phase54CertificationReport(
            "5.4", CertificationStatus.FAILED, request.run_id, None, tuple(checks)
        )
    checks.append(_check(
        "PIPELINE_EXECUTION", True,
        "Universal decision orchestration and unified outputs executed successfully.", "",
    ))

    expected_stages = (
        OrchestrationStage.DECISION, OrchestrationStage.RANKING,
        OrchestrationStage.CAPITAL_SUPPLY, OrchestrationStage.SIZING,
        OrchestrationStage.CONSTRAINTS, OrchestrationStage.OBJECTIVES,
        OrchestrationStage.OPTIMIZATION, OrchestrationStage.EXECUTION,
    )
    actual_stages = tuple(item.stage for item in first.run.stage_records)
    stage_complete = actual_stages == expected_stages and all(
        item.status is StageStatus.PASSED for item in first.run.stage_records
    )
    checks.append(_check(
        "STAGE_COMPLETENESS", stage_complete,
        "All eight ordered orchestration stages completed with preserved evidence.",
        "Orchestration stage history is incomplete, failed, or out of order.",
    ))

    deterministic = (
        first.run.output_fingerprint == repeated.run.output_fingerprint
        == reversed_result.run.output_fingerprint
        and first.optimization == repeated.optimization == reversed_result.optimization
        and first.execution_plan == repeated.execution_plan == reversed_result.execution_plan
    )
    checks.append(_check(
        "DETERMINISM_AND_INPUT_ORDER", deterministic,
        "Repeated and reversed-input runs produced identical results.",
        "Run output changed across repetition or input order.",
    ))

    source_ids = {item.opportunity_id for item in request.opportunities}
    ranked_ids = {item.opportunity_id for item in first.ranking.outcomes}
    allocation_ids = {item.opportunity_id for item in first.optimization.capital_result.lines}
    lineage = ranked_ids.issubset(source_ids) and allocation_ids.issubset(ranked_ids) and all(
        line.request_id == f"{first.ranking.batch_id}:{line.opportunity_id}"
        for line in first.optimization.capital_result.lines
    )
    checks.append(_check(
        "IDENTITY_AND_LINEAGE", lineage,
        "Opportunity identity and decision-to-ranking-to-allocation lineage were preserved.",
        "An opportunity or request identifier lost its source lineage.",
    ))

    quarantined_ids = {item.opportunity_id for item in first.run.quarantined}
    quarantine_valid = (
        first.run.status is OrchestrationRunStatus.COMPLETED_WITH_QUARANTINE
        and quarantined_ids == {scenario.quarantined_opportunity_id}
        and set(first.run.successful_opportunity_ids) == allocation_ids
        and scenario.quarantined_opportunity_id not in allocation_ids
    )
    checks.append(_check(
        "QUARANTINE_ISOLATION", quarantine_valid,
        "Invalid opportunity was quarantined without blocking four valid opportunities.",
        "Quarantine was missing, leaked into allocation, or blocked valid opportunities.",
    ))

    capital = first.optimization.capital_result
    conservation = (
        capital.gross_capital
        == capital.reserved_capital + capital.allocated_capital + capital.residual_capital
        and first.execution_plan.purchase_total == capital.allocated_capital
        and first.execution_plan.retained_cash == capital.residual_capital
    )
    checks.append(_check(
        "CAPITAL_AND_EXECUTION_CONSERVATION", conservation,
        "Capital and execution totals reconcile exactly through the full run.",
        "Capital or execution conservation failed.",
    ))

    registry = InMemoryRunRegistry()
    registered_first = registry.execute(request, scenario.policy)
    registered_second = registry.execute(request, scenario.policy)
    plan = registry.recovery_plan(request.run_id)
    idempotent = (
        registered_first is registered_second
        and len(registry.get(request.run_id).attempts) == 1
        and plan.action is RecoveryAction.RETURN_COMPLETED
    )
    checks.append(_check(
        "REGISTRY_IDEMPOTENCY", idempotent,
        "Completed run was reused without a duplicate allocation attempt.",
        "Registry allowed duplicate execution or produced an invalid recovery plan.",
    ))

    reproducibility = registry.verify_reproducibility(request.run_id, scenario.policy)
    checks.append(_check(
        "REPRODUCIBILITY", reproducibility.reproducible,
        "Replay matched request, policy, output, and stage-checkpoint fingerprints.",
        "Reproducibility replay diverged from the registered attempt.",
    ))

    try:
        dashboard_rows = tuple(csv.DictReader(io.StringIO(package.dashboard_csv)))
        audit_rows = tuple(csv.DictReader(io.StringIO(package.audit_csv)))
        payload = json.loads(package.json_text)
        output_valid = (
            payload["schema_version"] == "5.4.5"
            and payload["package_fingerprint"] == package.package_fingerprint
            and len(dashboard_rows) == len(request.opportunities)
            and len(audit_rows) == len(package.audit_rows)
            and [int(item["sequence"]) for item in audit_rows]
            == list(range(1, len(audit_rows) + 1))
        )
    except Exception:
        output_valid = False
    checks.append(_check(
        "UNIFIED_OUTPUT_INTEGRITY", output_valid,
        "JSON, dashboard CSV, and audit CSV passed fingerprint and cardinality validation.",
        "One or more unified outputs failed integrity validation.",
    ))

    status = (
        CertificationStatus.PASSED
        if all(item.status is CertificationStatus.PASSED for item in checks)
        else CertificationStatus.FAILED
    )
    return Phase54CertificationReport(
        "5.4", status, request.run_id, package.package_fingerprint, tuple(checks)
    )
