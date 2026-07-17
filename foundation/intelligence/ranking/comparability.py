"""Eligibility and comparability gates for portfolio opportunity ranking."""
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Sequence
from foundation.intelligence.decision import DecisionAction,DecisionStatus,EligibilityStatus
from .contracts import ComparabilityStatus,PortfolioRankingInput,RankingContractError
class RankingComparabilityError(RankingContractError): pass
class ComparabilityConfigurationError(RankingComparabilityError): pass
class DuplicateRankingDecisionError(RankingComparabilityError): pass
class ComparabilitySeverity(StrEnum): INFO="info"; WARNING="warning"; BLOCKING="blocking"
@dataclass(frozen=True,slots=True)
class ComparabilityCheck:
    code:str; passed:bool; severity:ComparabilitySeverity; message:str
    def __post_init__(self):
        if not self.code.strip() or not self.message.strip(): raise RankingComparabilityError("check code and message cannot be empty.")
@dataclass(frozen=True,slots=True)
class RankingComparabilityProfile:
    minimum_freshness_score:float=40; exclusion_freshness_score:float=20
    require_positive_allocation_capacity:bool=True; include_hold_actions:bool=False; include_wait_actions:bool=False
    comparability_version:str="5.2.2"
    def __post_init__(self):
        if not 0<=self.exclusion_freshness_score<=self.minimum_freshness_score<=100: raise ComparabilityConfigurationError("freshness thresholds must satisfy 0 <= exclusion <= minimum <= 100.")
        if not self.comparability_version.strip(): raise ComparabilityConfigurationError("comparability_version cannot be empty.")
@dataclass(frozen=True,slots=True)
class RankingComparabilityResult:
    ranking_input:PortfolioRankingInput; status:ComparabilityStatus
    checks:Sequence[ComparabilityCheck]=field(default_factory=tuple); reasons:Sequence[str]=field(default_factory=tuple)
    comparability_version:str="5.2.2"
    @property
    def may_rank(self): return self.status is not ComparabilityStatus.EXCLUDED
    @property
    def decision_id(self): return self.ranking_input.decision.decision_id
class RankingComparabilityEngine:
    POSITIVE={DecisionAction.STRONG_BUY,DecisionAction.BUY,DecisionAction.ACCUMULATE}
    def __init__(self,profile=None): self.profile=profile or RankingComparabilityProfile()
    def evaluate(self,value):
        d=value.decision; now=value.context.as_of; checks=[]
        def add(code,passed,severity,message): checks.append(ComparabilityCheck(code,passed,severity,message))
        expired=d.status is DecisionStatus.EXPIRED or (d.expires_at is not None and d.expires_at<=now)
        add("decision_current",not expired,ComparabilitySeverity.BLOCKING,"Decision is current." if not expired else "Decision is expired.")
        eligible=d.eligibility not in {EligibilityStatus.INELIGIBLE,EligibilityStatus.INSUFFICIENT_DATA}
        add("decision_eligible",eligible,ComparabilitySeverity.BLOCKING,"Eligibility permits ranking." if eligible else "Eligibility blocks ranking.")
        action_ok=d.action in self.POSITIVE or (d.action is DecisionAction.HOLD and self.profile.include_hold_actions) or (d.action is DecisionAction.WAIT and self.profile.include_wait_actions)
        add("action_rankable",action_ok,ComparabilitySeverity.BLOCKING,"Action is rankable." if action_ok else "Action is not rankable.")
        capacity=d.maximum_allocation>0 if self.profile.require_positive_allocation_capacity else True
        add("allocation_capacity",capacity,ComparabilitySeverity.BLOCKING,"Allocation capacity exists." if capacity else "No allocation capacity.")
        severe=value.freshness_score<self.profile.exclusion_freshness_score
        add("freshness_exclusion",not severe,ComparabilitySeverity.BLOCKING,"Freshness exceeds exclusion threshold." if not severe else "Freshness is below exclusion threshold.")
        stale=value.freshness_score<self.profile.minimum_freshness_score
        add("freshness_quality",not stale,ComparabilitySeverity.WARNING,"Freshness meets standard." if not stale else "Freshness requires conditional ranking.")
        conditional=d.eligibility is EligibilityStatus.CONDITIONALLY_ELIGIBLE
        add("unconditional_eligibility",not conditional,ComparabilitySeverity.WARNING,"Eligibility is unconditional." if not conditional else "Eligibility is conditional.")
        blocking=any(not c.passed and c.severity is ComparabilitySeverity.BLOCKING for c in checks)
        warning=any(not c.passed and c.severity is ComparabilitySeverity.WARNING for c in checks)
        status=ComparabilityStatus.EXCLUDED if blocking else (ComparabilityStatus.CONDITIONAL if warning else ComparabilityStatus.COMPARABLE)
        return RankingComparabilityResult(value,status,tuple(checks),tuple(c.message for c in checks if not c.passed),self.profile.comparability_version)
    def evaluate_batch(self,values):
        ids=[v.decision.decision_id for v in values]
        if len(ids)!=len(set(ids)): raise DuplicateRankingDecisionError("decision_id values must be unique within a ranking batch.")
        return tuple(self.evaluate(v) for v in values)
