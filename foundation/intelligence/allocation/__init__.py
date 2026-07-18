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

from .execution import (
    ContributionExecutionPlan,
    ExecutionAction,
    ExecutionCadence,
    ExecutionInstruction,
    ExecutionPlanningPolicy,
    build_execution_plan,
)

from .explanations import (
    AllocationAuditArtifact,
    AllocationAuditInput,
    AllocationExplanation,
    AllocationExplanationAuditResult,
    build_allocation_explanation_audit,
)

from .serialization import (
    ALLOCATION_COLUMNS,
    AUDIT_COLUMNS,
    EXECUTION_COLUMNS,
    allocation_audit_csv,
    allocation_audit_rows,
    allocation_bundle_dict,
    allocation_bundle_json,
    allocation_dashboard_csv,
    allocation_dashboard_rows,
    execution_dashboard_csv,
    execution_dashboard_rows,
)

from .certification import (
    CertificationCheck,
    CertificationStatus,
    Phase53CertificationReport,
    Phase53CertificationScenario,
    build_reference_certification_scenario,
    certify_phase_5_3,
)
