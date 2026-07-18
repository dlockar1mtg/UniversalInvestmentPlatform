"""Universal decision-orchestration contracts and cross-stage adapters."""

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

__all__ = [
    "AdapterEvidence", "CapitalInput", "DecisionRankingAdapterResult",
    "FailureScope", "OrchestrationOpportunity", "OrchestrationPolicyBundle",
    "OrchestrationRunStatus", "OrchestrationStage", "PortfolioPositionSnapshot",
    "PortfolioSnapshot", "QuarantinedOpportunity", "RankingAllocationAdapterResult",
    "StageRecord", "StageStatus", "UniversalOrchestrationResult", "UniversalRunRequest",
    "adapt_decisions_to_ranking", "adapt_ranking_to_allocation",
]
