"""Composite priority scoring and deterministic ordering."""
from dataclasses import dataclass,field
from typing import Mapping,Sequence
from .contracts import (ComparabilityStatus,PortfolioRankingInput,PortfolioRankingPolicy,
 RankedOpportunity,RankingFactor,RankingTier,RankingContractError)
from .factors import RankingFactorResult
class PriorityScoringError(RankingContractError): pass
class PriorityConsistencyError(PriorityScoringError): pass
class PriorityConfigurationError(PriorityScoringError): pass
@dataclass(frozen=True,slots=True)
class PriorityScoringProfile:
    highest_threshold:float=85; high_threshold:float=72; medium_threshold:float=60; low_threshold:float=45
    priority_version:str="5.2.4"
    def __post_init__(self):
        if not 0<=self.low_threshold<self.medium_threshold<self.high_threshold<self.highest_threshold<=100:
            raise PriorityConfigurationError("tier thresholds must be strictly ordered between 0 and 100.")
        if not self.priority_version.strip(): raise PriorityConfigurationError("priority_version cannot be empty.")
    def tier(self,score):
        if score>=self.highest_threshold:return RankingTier.HIGHEST
        if score>=self.high_threshold:return RankingTier.HIGH
        if score>=self.medium_threshold:return RankingTier.MEDIUM
        if score>=self.low_threshold:return RankingTier.LOW
        return RankingTier.DEFERRED
@dataclass(frozen=True,slots=True)
class PriorityScoreResult:
    decision_id:str; asset_id:str; asset_class:str; base_factor_score:float
    penalties:Mapping[str,float]; final_priority_score:float; tier:RankingTier
    comparability:ComparabilityStatus; reasons:Sequence[str]=field(default_factory=tuple)
    priority_version:str="5.2.4"
    def __post_init__(self):
        if not self.decision_id.strip() or not self.asset_id.strip() or not self.asset_class.strip(): raise PriorityScoringError("identifiers cannot be empty.")
        if not 0<=self.base_factor_score<=100 or not 0<=self.final_priority_score<=100: raise PriorityScoringError("priority scores must be between 0 and 100.")
        if any(not 0<=float(v)<=100 for v in self.penalties.values()): raise PriorityScoringError("penalties must be between 0 and 100.")
        if abs(max(0,self.base_factor_score-sum(self.penalties.values()))-self.final_priority_score)>1e-6: raise PriorityScoringError("final_priority_score must equal base score less penalties, floored at zero.")
class CompositePriorityScoringEngine:
    def __init__(self,policy=None,profile=None): self.policy=policy or PortfolioRankingPolicy();self.profile=profile or PriorityScoringProfile()
    def score(self,value:PortfolioRankingInput,factors:RankingFactorResult,additional_penalties=None):
        d=value.decision
        if factors.decision_id!=d.decision_id or factors.asset_id!=d.asset_id: raise PriorityConsistencyError("factor result must match ranking input.")
        if factors.comparability is ComparabilityStatus.EXCLUDED: raise PriorityConsistencyError("excluded factors cannot receive a priority score.")
        penalties=dict(additional_penalties or {})
        if factors.comparability is ComparabilityStatus.CONDITIONAL: penalties["conditional_comparability"]=self.policy.conditional_penalty
        if any(not str(k).strip() for k in penalties): raise PriorityScoringError("penalty names cannot be empty.")
        if any(not 0<=float(v)<=100 for v in penalties.values()): raise PriorityScoringError("penalties must be between 0 and 100.")
        final=max(0,factors.weighted_factor_total-sum(penalties.values()))
        reasons=tuple(factors.reasons)+tuple(f"{k} penalty: {v:.4f}." for k,v in sorted(penalties.items()))
        return PriorityScoreResult(d.decision_id,d.asset_id,d.asset_class,factors.weighted_factor_total,penalties,final,self.profile.tier(final),factors.comparability,reasons,self.profile.priority_version)
    @staticmethod
    def _factor(factors,factor): return next(x.raw_score for x in factors.factor_scores if x.factor is factor)
    def rank(self,items:Sequence[tuple[PortfolioRankingInput,RankingFactorResult,PriorityScoreResult]]):
        for value,factors,priority in items:
            if value.decision.decision_id!=factors.decision_id or factors.decision_id!=priority.decision_id: raise PriorityConsistencyError("all ranking artifacts must share decision_id.")
        ordered=sorted(items,key=lambda x:(-x[2].final_priority_score,-self._factor(x[1],RankingFactor.CONFIDENCE),-self._factor(x[1],RankingFactor.DECISION_SCORE),-self._factor(x[1],RankingFactor.ACTION_STRENGTH),x[0].decision.asset_id,x[0].decision.decision_id))
        return tuple(RankedOpportunity(v.decision.decision_id,v.decision.asset_id,v.decision.asset_class,index,p.final_priority_score,p.tier,p.comparability,f.factor_scores,p.penalties,p.reasons) for index,(v,f,p) in enumerate(ordered,1))
