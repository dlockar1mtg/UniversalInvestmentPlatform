"""Policy-controlled end-to-end universal decision orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping

from foundation.intelligence.allocation.constraints import (
    ConstraintContext,
    ConstraintEvaluation,
    evaluate_allocation_constraints,
)
from foundation.intelligence.allocation.contracts import (
    AllocationConstraint,
    CapitalPool,
    CapitalPoolType,
)
from foundation.intelligence.allocation.execution import (
    ContributionExecutionPlan,
    ExecutionPlanningPolicy,
    build_execution_plan,
)
from foundation.intelligence.allocation.objectives import (
    AllocationObjectiveResult,
    ObjectiveInputs,
    ObjectivePolicy,
    calculate_allocation_objective,
)
from foundation.intelligence.allocation.optimizer import (
    CapitalOptimizationResult,
    OptimizationCandidate,
    OptimizerPolicy,
    optimize_capital,
)
from foundation.intelligence.allocation.sizing import (
    OpportunitySizingResult,
    SizingInputs,
    SizingPolicy,
    size_opportunity,
)
from foundation.intelligence.allocation.supply import (
    CapitalSupplyResult,
    ReserveRule,
    calculate_capital_supply,
)
from foundation.intelligence.ranking.competition import CompetitionPolicy
from foundation.intelligence.ranking.orchestrator import (
    PortfolioRankingBatchResult,
    run_portfolio_ranking,
)

from .adapters import adapt_decisions_to_ranking, adapt_ranking_to_allocation
from .contracts import (
    FailureScope,
    OrchestrationRunStatus,
    OrchestrationStage,
    QuarantinedOpportunity,
    StageRecord,
    StageStatus,
    UniversalOrchestrationResult,
    UniversalRunRequest,
)


def _mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def _portable(value):
    if isinstance(value, Mapping):
        return {str(key): _portable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_portable(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _portable(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    if isinstance(value, (date,)):
        return value.isoformat()
    return value


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(
        _portable(payload), sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class OrchestrationEnginePolicy:
    ranking: CompetitionPolicy
    reserve_rules: tuple[ReserveRule, ...] = ()
    constraints: tuple[AllocationConstraint, ...] = ()
    sizing: SizingPolicy = field(default_factory=SizingPolicy)
    objectives: ObjectivePolicy = field(default_factory=ObjectivePolicy)
    optimizer: OptimizerPolicy = field(default_factory=OptimizerPolicy)
    execution: ExecutionPlanningPolicy = field(default_factory=ExecutionPlanningPolicy)

    def __post_init__(self) -> None:
        reserve_ids = [item.reserve_id for item in self.reserve_rules]
        constraint_ids = [item.constraint_id for item in self.constraints]
        if len(reserve_ids) != len(set(reserve_ids)):
            raise ValueError("reserve rule identifiers must be unique")
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("allocation constraint identifiers must be unique")


@dataclass(frozen=True)
class EndToEndOrchestrationResult:
    run: UniversalOrchestrationResult
    ranking: PortfolioRankingBatchResult | None
    capital_supply: CapitalSupplyResult | None
    sizing_results: tuple[OpportunitySizingResult, ...]
    constraint_results: tuple[ConstraintEvaluation, ...]
    objective_results: tuple[AllocationObjectiveResult, ...]
    optimization: CapitalOptimizationResult | None
    execution_plan: ContributionExecutionPlan | None


def _stage(stage, timestamp, processed, failed=0, **evidence) -> StageRecord:
    return StageRecord(
        stage=stage,
        status=StageStatus.PASSED,
        started_at=timestamp,
        completed_at=timestamp,
        processed_count=processed,
        failed_count=failed,
        evidence=evidence,
    )


def _quarantine(opportunity_id: str, stage: OrchestrationStage, exc: Exception):
    return QuarantinedOpportunity(
        opportunity_id=opportunity_id,
        stage=stage,
        reason_code=f"INVALID_{stage.value}_INPUT",
        message=str(exc),
        failure_scope=FailureScope.OPPORTUNITY,
    )


def _failed_result(
    request: UniversalRunRequest,
    records: list[StageRecord],
    quarantined: list[QuarantinedOpportunity],
    stage: OrchestrationStage,
    message: str,
) -> EndToEndOrchestrationResult:
    timestamp = request.requested_at
    records.append(
        StageRecord(
            stage, StageStatus.FAILED, timestamp, timestamp,
            len(request.opportunities), len(request.opportunities),
            {"error": message},
        )
    )
    if not quarantined:
        quarantined.extend(
            QuarantinedOpportunity(
                item.opportunity_id, stage, "BATCH_EXECUTION_FAILED", message,
                FailureScope.BATCH,
            )
            for item in sorted(request.opportunities, key=lambda item: item.opportunity_id)
        )
    run = UniversalOrchestrationResult(
        request.run_id,
        OrchestrationRunStatus.FAILED,
        request.policies.fingerprint,
        tuple(records),
        (),
        tuple(quarantined),
    )
    return EndToEndOrchestrationResult(run, None, None, (), (), (), None, None)


def run_universal_orchestration(
    request: UniversalRunRequest,
    policy: OrchestrationEnginePolicy,
) -> EndToEndOrchestrationResult:
    """Execute one immutable, fully audited decision-to-execution run."""
    timestamp = request.requested_at
    records: list[StageRecord] = []
    quarantined: list[QuarantinedOpportunity] = []
    by_id = {item.opportunity_id: item for item in request.opportunities}

    adapted = adapt_decisions_to_ranking(request.opportunities)
    quarantined.extend(adapted.quarantined)
    records.append(_stage(
        OrchestrationStage.DECISION, timestamp, len(request.opportunities),
        len(adapted.quarantined), adapter_evidence=len(adapted.evidence),
    ))
    if not adapted.items:
        return _failed_result(
            request, records, quarantined, OrchestrationStage.RANKING,
            "no valid opportunities remained after decision-to-ranking adaptation",
        )

    try:
        ranking = run_portfolio_ranking(
            f"{request.run_id}:ranking", adapted.items, policy.ranking
        )
    except Exception as exc:
        return _failed_result(request, records, quarantined, OrchestrationStage.RANKING, str(exc))
    records.append(_stage(
        OrchestrationStage.RANKING, timestamp, len(adapted.items),
        selected_count=len(ranking.selected), fingerprint=ranking.batch_fingerprint,
    ))

    pool = CapitalPool(
        pool_id=f"{request.run_id}:capital",
        pool_type=CapitalPoolType.ONE_TIME,
        gross_capital=request.capital.gross_capital,
        required_reserve=request.capital.required_reserve,
        currency=request.capital.currency,
        as_of=timestamp,
    )
    supply = calculate_capital_supply(
        pool, policy.reserve_rules,
        unavailable_capital=request.capital.unavailable_capital,
    )
    records.append(_stage(
        OrchestrationStage.CAPITAL_SUPPLY, timestamp, 1,
        deployable_capital=str(supply.deployable_capital), status=supply.status.value,
    ))

    allocation_adapted = adapt_ranking_to_allocation(ranking, request.opportunities)
    quarantined.extend(allocation_adapted.quarantined)
    requests_by_id = {item.opportunity_id: item for item in allocation_adapted.requests}

    sizing_results: list[OpportunitySizingResult] = []
    for allocation_request in allocation_adapted.requests:
        source = by_id[allocation_request.opportunity_id].source_payload
        try:
            values = _mapping(source.get("sizing_inputs"), "sizing_inputs")
            sizing_results.append(size_opportunity(SizingInputs(
                request=allocation_request,
                confidence_score=values["confidence_score"],
                action_strength_score=values["action_strength_score"],
                portfolio_gap_amount=values["portfolio_gap_amount"],
                opportunity_capacity_amount=values["opportunity_capacity_amount"],
                liquidity_capacity_amount=values["liquidity_capacity_amount"],
                minimum_purchase_amount=values.get("minimum_purchase_amount", 0),
            ), supply, policy.sizing))
        except Exception as exc:
            quarantined.append(_quarantine(allocation_request.opportunity_id, OrchestrationStage.SIZING, exc))
    sizing_results.sort(key=lambda item: item.opportunity_id)
    records.append(_stage(
        OrchestrationStage.SIZING, timestamp, len(ranking.selected),
        len(allocation_adapted.quarantined) + len(allocation_adapted.requests) - len(sizing_results),
    ))

    portfolio = request.portfolio
    asset_totals: dict[str, Decimal] = {}
    group_totals: dict[str, Decimal] = {}
    position_totals = {item.opportunity_id: item.market_value for item in portfolio.positions}
    for position in portfolio.positions:
        asset_totals[position.asset_class] = asset_totals.get(position.asset_class, Decimal("0")) + position.market_value
        group_totals[position.group_key] = group_totals.get(position.group_key, Decimal("0")) + position.market_value

    constraint_results: list[ConstraintEvaluation] = []
    sizing_by_id = {item.opportunity_id: item for item in sizing_results}
    for opportunity_id in sorted(sizing_by_id):
        allocation_request = requests_by_id[opportunity_id]
        try:
            constraint_results.append(evaluate_allocation_constraints(
                allocation_request, sizing_by_id[opportunity_id], supply, policy.constraints,
                ConstraintContext(
                    position_totals.get(opportunity_id, 0),
                    asset_totals.get(allocation_request.asset_class, 0),
                    group_totals.get(allocation_request.group_key, 0),
                ),
            ))
        except Exception as exc:
            quarantined.append(_quarantine(opportunity_id, OrchestrationStage.CONSTRAINTS, exc))
    records.append(_stage(
        OrchestrationStage.CONSTRAINTS, timestamp, len(sizing_results),
        len(sizing_results) - len(constraint_results),
    ))

    objective_results: list[AllocationObjectiveResult] = []
    constraints_by_id = {item.opportunity_id: item for item in constraint_results}
    for opportunity_id in sorted(constraints_by_id):
        source = by_id[opportunity_id].source_payload
        try:
            values = _mapping(source.get("objective_inputs"), "objective_inputs")
            objective_results.append(calculate_allocation_objective(ObjectiveInputs(
                request=requests_by_id[opportunity_id],
                sizing=sizing_by_id[opportunity_id],
                constraints=constraints_by_id[opportunity_id],
                target_gap_score=values["target_gap_score"],
                diversification_score=values["diversification_score"],
                liquidity_score=values["liquidity_score"],
                capital_efficiency_score=values["capital_efficiency_score"],
            ), policy.objectives))
        except Exception as exc:
            quarantined.append(_quarantine(opportunity_id, OrchestrationStage.OBJECTIVES, exc))
    objective_results.sort(key=lambda item: item.deterministic_key)
    records.append(_stage(
        OrchestrationStage.OBJECTIVES, timestamp, len(constraint_results),
        len(constraint_results) - len(objective_results),
    ))

    objectives_by_id = {item.opportunity_id: item for item in objective_results}
    candidates = tuple(
        OptimizationCandidate(
            requests_by_id[opportunity_id], constraints_by_id[opportunity_id], objectives_by_id[opportunity_id]
        )
        for opportunity_id in sorted(objectives_by_id)
    )
    optimization = optimize_capital(
        f"{request.run_id}:allocation", ranking.batch_id, supply, candidates,
        policy.optimizer, created_at=timestamp,
    )
    records.append(_stage(
        OrchestrationStage.OPTIMIZATION, timestamp, len(candidates),
        allocated_capital=str(optimization.capital_result.allocated_capital),
        residual_capital=str(optimization.capital_result.residual_capital),
    ))
    execution = build_execution_plan(
        f"{request.run_id}:execution", optimization, timestamp.date(), policy.execution
    )
    records.append(_stage(
        OrchestrationStage.EXECUTION, timestamp, len(execution.instructions),
        purchase_total=str(execution.purchase_total), retained_cash=str(execution.retained_cash),
    ))

    successful = tuple(sorted(objectives_by_id))
    status = (
        OrchestrationRunStatus.COMPLETED_WITH_QUARANTINE
        if quarantined else OrchestrationRunStatus.COMPLETED
    )
    output_fingerprint = _fingerprint({
        "run_id": request.run_id,
        "policy_fingerprint": request.policies.fingerprint,
        "ranking_fingerprint": ranking.batch_fingerprint,
        "supply": supply,
        "optimization": optimization,
        "execution": execution,
        "quarantined": tuple(quarantined),
    })
    run = UniversalOrchestrationResult(
        request.run_id, status, request.policies.fingerprint, tuple(records), successful,
        tuple(quarantined), output_fingerprint,
    )
    return EndToEndOrchestrationResult(
        run, ranking, supply, tuple(sizing_results), tuple(constraint_results),
        tuple(objective_results), optimization, execution,
    )
