"""Capital allocation and decision optimization contracts."""

from .contracts import (
    AllocationBounds,
    AllocationConstraint,
    AllocationConstraintType,
    AllocationLine,
    AllocationReasonCode,
    AllocationRequest,
    AllocationStatus,
    CapitalAllocationResult,
    CapitalPool,
    CapitalPoolType,
)

__all__ = [
    "AllocationBounds",
    "AllocationConstraint",
    "AllocationConstraintType",
    "AllocationLine",
    "AllocationReasonCode",
    "AllocationRequest",
    "AllocationStatus",
    "CapitalAllocationResult",
    "CapitalPool",
    "CapitalPoolType",
]

from .supply import (
    CapitalSupplyResult,
    CapitalSupplyStatus,
    ReserveLine,
    ReserveRule,
    ReserveType,
    calculate_capital_supply,
)

from .sizing import (
    OpportunitySizingResult,
    SizingInputs,
    SizingPolicy,
    SizingReasonCode,
    SizingStatus,
    size_opportunities,
    size_opportunity,
)

from .constraints import (
    ConstraintContext,
    ConstraintDisposition,
    ConstraintEligibility,
    ConstraintEvaluation,
    ConstraintOutcome,
    evaluate_allocation_constraints,
)

from .objectives import (
    AllocationObjectiveResult,
    ObjectiveContribution,
    ObjectiveInputs,
    ObjectivePenalty,
    ObjectivePolicy,
    ObjectiveStatus,
    calculate_allocation_objective,
    calculate_allocation_objectives,
)

from .optimizer import (
    CapitalOptimizationResult,
    OptimizationCandidate,
    OptimizerPolicy,
    optimize_capital,
)
