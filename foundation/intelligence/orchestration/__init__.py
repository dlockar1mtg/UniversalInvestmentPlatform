"""Universal decision orchestration, execution, registry, and recovery."""

from .adapters import (
    AdapterEvidence,
    DecisionRankingAdapterResult,
    RankingAllocationAdapterResult,
    adapt_decisions_to_ranking,
    adapt_ranking_to_allocation,
)
from .contracts import (
    CapitalInput,
    FailureScope,
    OrchestrationOpportunity,
    OrchestrationPolicyBundle,
    OrchestrationRunStatus,
    OrchestrationStage,
    PortfolioPositionSnapshot,
    PortfolioSnapshot,
    QuarantinedOpportunity,
    StageRecord,
    StageStatus,
    UniversalOrchestrationResult,
    UniversalRunRequest,
)
from .orchestrator import (
    EndToEndOrchestrationResult,
    OrchestrationEnginePolicy,
    run_universal_orchestration,
)
from .registry import (
    InMemoryRunRegistry,
    RecoveryAction,
    RecoveryPlan,
    RegisteredRun,
    ReproducibilityReport,
    RunAttempt,
    StageCheckpoint,
    request_fingerprint,
)

__all__ = [
    "AdapterEvidence", "CapitalInput", "DecisionRankingAdapterResult",
    "EndToEndOrchestrationResult", "FailureScope", "InMemoryRunRegistry",
    "OrchestrationEnginePolicy", "OrchestrationOpportunity", "OrchestrationPolicyBundle",
    "OrchestrationRunStatus", "OrchestrationStage", "PortfolioPositionSnapshot",
    "PortfolioSnapshot", "QuarantinedOpportunity", "RankingAllocationAdapterResult",
    "RecoveryAction", "RecoveryPlan", "RegisteredRun", "ReproducibilityReport",
    "RunAttempt", "StageCheckpoint", "StageRecord", "StageStatus",
    "UniversalOrchestrationResult", "UniversalRunRequest",
    "adapt_decisions_to_ranking", "adapt_ranking_to_allocation", "request_fingerprint",
    "run_universal_orchestration",
]
