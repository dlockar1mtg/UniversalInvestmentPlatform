"""Auditable factor calculations for portfolio-wide opportunity ranking."""
from dataclasses import dataclass,field
from typing import Mapping,Sequence
from foundation.intelligence.decision import DecisionAction
from .comparability import RankingComparabilityResult
from .contracts import (ComparabilityStatus,PortfolioRankingInput,PortfolioRankingPolicy,
 RankingFactor,RankingFactorScore,RankingContractError)
class RankingFactorError(RankingContractError): pass
class IncomparableRankingInputError(RankingFactorError): pass
class RankingFactorConsistencyError(RankingFactorError): pass
DEFAULT_ACTION_STRENGTH={DecisionAction.STRONG_BUY:100.0,DecisionAction.BUY:85.0,
 DecisionAction.ACCUMULATE:70.0,DecisionAction.HOLD:50.0,DecisionAction.WAIT:35.0,
 DecisionAction.REDUCE:20.0,DecisionAction.SELL:10.0,DecisionAction.AVOID:0.0,
 DecisionAction.INELIGIBLE:0.0,DecisionAction.INSUFFICIENT_DATA:0.0}
@dataclass(frozen=True,slots=True)
class RankingFactorProfile:
    action_strength:Mapping[DecisionAction,float]=field(default_factory=lambda:dict(DEFAULT_ACTION_STRENGTH))
    factor_version:str="5.2.3"
    def __post_init__(self):
        if set(self.action_strength)!=set(DecisionAction): raise RankingFactorError("action_strength must define every DecisionAction.")
        if any(not 0<=float(v)<=100 for v in self.action_strength.values()): raise RankingFactorError("action strength values must be between 0 and 100.")
        if not self.factor_version.strip(): raise RankingFactorError("factor_version cannot be empty.")
@dataclass(frozen=True,slots=True)
class RankingFactorResult:
    decision_id:str; asset_id:str; comparability:ComparabilityStatus
    factor_scores:Sequence[RankingFactorScore]; weighted_factor_total:float
    reasons:Sequence[str]=field(default_factory=tuple); factor_version:str="5.2.3"
    def __post_init__(self):
        if not self.decision_id.strip() or not self.asset_id.strip(): raise RankingFactorError("decision_id and asset_id cannot be empty.")
        factors=[x.factor for x in self.factor_scores]
        if set(factors)!=set(RankingFactor) or len(factors)!=len(set(factors)): raise RankingFactorError("factor_scores must contain every ranking factor exactly once.")
        calculated=sum(x.weighted_contribution for x in self.factor_scores)
        if abs(calculated-self.weighted_factor_total)>1e-6: raise RankingFactorError("weighted_factor_total must equal factor contributions.")
        if not 0<=self.weighted_factor_total<=100: raise RankingFactorError("weighted_factor_total must be between 0 and 100.")
class UniversalRankingFactorEngine:
    def __init__(self,policy=None,profile=None):
        self.policy=policy or PortfolioRankingPolicy(); self.profile=profile or RankingFactorProfile()
    def evaluate(self,value:PortfolioRankingInput,comparability:RankingComparabilityResult)->RankingFactorResult:
        if comparability.ranking_input.decision.decision_id!=value.decision.decision_id: raise RankingFactorConsistencyError("comparability result must match ranking input.")
        if comparability.status is ComparabilityStatus.EXCLUDED: raise IncomparableRankingInputError("excluded opportunities cannot receive ranking factors.")
        raw={RankingFactor.DECISION_SCORE:value.decision.score.final_score,
             RankingFactor.CONFIDENCE:value.decision.confidence*100,
             RankingFactor.ACTION_STRENGTH:self.profile.action_strength[value.decision.action],
             RankingFactor.RISK_ADJUSTED_OPPORTUNITY:value.risk_adjusted_opportunity,
             RankingFactor.LIQUIDITY:value.liquidity_quality,
             RankingFactor.DIVERSIFICATION:value.diversification_contribution,
             RankingFactor.PORTFOLIO_CAPACITY:value.portfolio_capacity,
             RankingFactor.FRESHNESS:value.freshness_score}
        scores=tuple(RankingFactorScore(factor,raw[factor],self.policy.factor_weights[factor],raw[factor]*self.policy.factor_weights[factor],(f"{factor.value} contributes {raw[factor]*self.policy.factor_weights[factor]:.4f} points.",)) for factor in RankingFactor)
        return RankingFactorResult(value.decision.decision_id,value.decision.asset_id,comparability.status,scores,sum(x.weighted_contribution for x in scores),comparability.reasons,self.profile.factor_version)
