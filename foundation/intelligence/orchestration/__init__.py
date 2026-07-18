"""Universal decision-orchestration contracts, adapters, and run engine."""

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

__all__ = [
    "AdapterEvidence", "CapitalInput", "DecisionRankingAdapterResult",
    "EndToEndOrchestrationResult", "FailureScope", "OrchestrationEnginePolicy",
    "OrchestrationOpportunity", "OrchestrationPolicyBundle", "OrchestrationRunStatus",
    "OrchestrationStage", "PortfolioPositionSnapshot", "PortfolioSnapshot",
    "QuarantinedOpportunity", "RankingAllocationAdapterResult", "StageRecord",
    "StageStatus", "UniversalOrchestrationResult", "UniversalRunRequest",
    "adapt_decisions_to_ranking", "adapt_ranking_to_allocation",
    "run_universal_orchestration",
]
