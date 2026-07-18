"""Universal decision orchestration, recovery, explanations, and outputs."""

from .adapters import (
    AdapterEvidence, DecisionRankingAdapterResult, RankingAllocationAdapterResult,
    adapt_decisions_to_ranking, adapt_ranking_to_allocation,
)
from .contracts import (
    CapitalInput, FailureScope, OrchestrationOpportunity, OrchestrationPolicyBundle,
    OrchestrationRunStatus, OrchestrationStage, PortfolioPositionSnapshot,
    PortfolioSnapshot, QuarantinedOpportunity, StageRecord, StageStatus,
    UniversalOrchestrationResult, UniversalRunRequest,
)
from .orchestrator import (
    EndToEndOrchestrationResult, OrchestrationEnginePolicy,
    run_universal_orchestration,
)
from .outputs import (
    AUDIT_COLUMNS, DASHBOARD_COLUMNS, UnifiedOpportunityExplanation,
    UnifiedOutputPackage, build_unified_output, validate_unified_output,
)
from .registry import (
    InMemoryRunRegistry, RecoveryAction, RecoveryPlan, RegisteredRun,
    ReproducibilityReport, RunAttempt, StageCheckpoint, request_fingerprint,
)

__all__ = [
    "AUDIT_COLUMNS", "AdapterEvidence", "CapitalInput", "DASHBOARD_COLUMNS",
    "DecisionRankingAdapterResult", "EndToEndOrchestrationResult", "FailureScope",
    "InMemoryRunRegistry", "OrchestrationEnginePolicy", "OrchestrationOpportunity",
    "OrchestrationPolicyBundle", "OrchestrationRunStatus", "OrchestrationStage",
    "PortfolioPositionSnapshot", "PortfolioSnapshot", "QuarantinedOpportunity",
    "RankingAllocationAdapterResult", "RecoveryAction", "RecoveryPlan", "RegisteredRun",
    "ReproducibilityReport", "RunAttempt", "StageCheckpoint", "StageRecord",
    "StageStatus", "UnifiedOpportunityExplanation", "UnifiedOrchestrationResult",
    "UnifiedOutputPackage", "UniversalOrchestrationResult", "UniversalRunRequest",
    "adapt_decisions_to_ranking", "adapt_ranking_to_allocation", "build_unified_output",
    "request_fingerprint", "run_universal_orchestration", "validate_unified_output",
]

# Backward-friendly semantic alias for consumers that name the complete result by scope.
UnifiedOrchestrationResult = EndToEndOrchestrationResult
