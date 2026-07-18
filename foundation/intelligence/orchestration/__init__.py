"""Universal decision orchestration and formal Phase 5.4 certification."""

from .adapters import (
    AdapterEvidence, DecisionRankingAdapterResult, RankingAllocationAdapterResult,
    adapt_decisions_to_ranking, adapt_ranking_to_allocation,
)
from .certification import (
    CertificationCheck, CertificationStatus, Phase54CertificationReport,
    Phase54CertificationScenario, build_reference_certification_scenario,
    certify_phase_5_4,
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

UnifiedOrchestrationResult = EndToEndOrchestrationResult

__all__ = [
    "AUDIT_COLUMNS", "AdapterEvidence", "CapitalInput", "CertificationCheck",
    "CertificationStatus", "DASHBOARD_COLUMNS", "DecisionRankingAdapterResult",
    "EndToEndOrchestrationResult", "FailureScope", "InMemoryRunRegistry",
    "OrchestrationEnginePolicy", "OrchestrationOpportunity", "OrchestrationPolicyBundle",
    "OrchestrationRunStatus", "OrchestrationStage", "Phase54CertificationReport",
    "Phase54CertificationScenario", "PortfolioPositionSnapshot", "PortfolioSnapshot",
    "QuarantinedOpportunity", "RankingAllocationAdapterResult", "RecoveryAction",
    "RecoveryPlan", "RegisteredRun", "ReproducibilityReport", "RunAttempt",
    "StageCheckpoint", "StageRecord", "StageStatus", "UnifiedOpportunityExplanation",
    "UnifiedOrchestrationResult", "UnifiedOutputPackage", "UniversalOrchestrationResult",
    "UniversalRunRequest", "adapt_decisions_to_ranking", "adapt_ranking_to_allocation",
    "build_reference_certification_scenario", "build_unified_output", "certify_phase_5_4",
    "request_fingerprint", "run_universal_orchestration", "validate_unified_output",
]
