"""Validated domain contracts for portfolio-wide opportunity ranking."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from math import isfinite
from typing import Any, Mapping, Sequence
from foundation.intelligence.decision import DecisionResult

class RankingContractError(ValueError): pass
class RankingStatus(StrEnum): DRAFT="draft"; RANKED="ranked"; PARTIAL="partial"; FAILED="failed"; CERTIFIED="certified"
class ComparabilityStatus(StrEnum): COMPARABLE="comparable"; CONDITIONAL="conditional"; EXCLUDED="excluded"
class RankingTier(StrEnum): HIGHEST="highest"; HIGH="high"; MEDIUM="medium"; LOW="low"; DEFERRED="deferred"; EXCLUDED="excluded"
class RankingFactor(StrEnum):
    DECISION_SCORE="decision_score"; CONFIDENCE="confidence"; ACTION_STRENGTH="action_strength"
    RISK_ADJUSTED_OPPORTUNITY="risk_adjusted_opportunity"; LIQUIDITY="liquidity"
    DIVERSIFICATION="diversification"; PORTFOLIO_CAPACITY="portfolio_capacity"; FRESHNESS="freshness"

def _text(value: str, name: str) -> None:
    if not value.strip(): raise RankingContractError(f"{name} cannot be empty.")
def _score(value: float, name: str) -> None:
    if not isfinite(float(value)) or not 0 <= float(value) <= 100: raise RankingContractError(f"{name} must be between 0 and 100.")
def _aware(value: datetime, name: str) -> None:
    if value.tzinfo is None: raise RankingContractError(f"{name} must be timezone-aware.")

@dataclass(frozen=True, slots=True)
class PortfolioRankingContext:
    ranking_id: str; portfolio_id: str; as_of: datetime
    available_capital: Decimal = Decimal("0"); maximum_ranked_opportunities: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        _text(self.ranking_id,"ranking_id"); _text(self.portfolio_id,"portfolio_id"); _aware(self.as_of,"as_of")
        if self.available_capital < 0: raise RankingContractError("available_capital cannot be negative.")
        if self.maximum_ranked_opportunities is not None and self.maximum_ranked_opportunities < 1: raise RankingContractError("maximum_ranked_opportunities must be positive.")

DEFAULT_RANKING_WEIGHTS={
    RankingFactor.DECISION_SCORE:0.25, RankingFactor.CONFIDENCE:0.20,
    RankingFactor.ACTION_STRENGTH:0.10, RankingFactor.RISK_ADJUSTED_OPPORTUNITY:0.15,
    RankingFactor.LIQUIDITY:0.08, RankingFactor.DIVERSIFICATION:0.10,
    RankingFactor.PORTFOLIO_CAPACITY:0.07, RankingFactor.FRESHNESS:0.05,
}

@dataclass(frozen=True, slots=True)
class PortfolioRankingPolicy:
    policy_id: str="universal-ranking-default"; policy_version: str="5.2.1"
    factor_weights: Mapping[RankingFactor,float]=field(default_factory=lambda:dict(DEFAULT_RANKING_WEIGHTS))
    conditional_penalty: float=5.0; expired_decisions_excluded: bool=True
    def __post_init__(self):
        _text(self.policy_id,"policy_id"); _text(self.policy_version,"policy_version")
        if set(self.factor_weights)!=set(RankingFactor): raise RankingContractError("factor_weights must define every ranking factor.")
        if any(not 0 <= float(v) <= 1 for v in self.factor_weights.values()): raise RankingContractError("factor weights must be between 0 and 1.")
        if abs(sum(self.factor_weights.values())-1.0)>1e-9: raise RankingContractError("factor weights must sum to 1.0.")
        _score(self.conditional_penalty,"conditional_penalty")

@dataclass(frozen=True, slots=True)
class PortfolioRankingInput:
    decision: DecisionResult; context: PortfolioRankingContext
    risk_adjusted_opportunity: float; liquidity_quality: float; diversification_contribution: float
    portfolio_capacity: float; freshness_score: float; metadata: Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        for name in ("risk_adjusted_opportunity","liquidity_quality","diversification_contribution","portfolio_capacity","freshness_score"): _score(getattr(self,name),name)
        if self.decision.generated_at > self.context.as_of: raise RankingContractError("decision cannot be generated after ranking as_of.")

@dataclass(frozen=True, slots=True)
class RankingFactorScore:
    factor: RankingFactor; raw_score: float; weight: float; weighted_contribution: float
    reasons: Sequence[str]=field(default_factory=tuple)
    def __post_init__(self):
        _score(self.raw_score,"raw_score")
        if not 0 <= self.weight <= 1: raise RankingContractError("weight must be between 0 and 1.")
        if abs(self.weighted_contribution-(self.raw_score*self.weight))>1e-6: raise RankingContractError("weighted_contribution must equal raw_score multiplied by weight.")

@dataclass(frozen=True, slots=True)
class RankedOpportunity:
    decision_id: str; asset_id: str; asset_class: str; rank: int | None; priority_score: float
    tier: RankingTier; comparability: ComparabilityStatus
    factor_scores: Sequence[RankingFactorScore]=field(default_factory=tuple)
    penalties: Mapping[str,float]=field(default_factory=dict); reasons: Sequence[str]=field(default_factory=tuple)
    def __post_init__(self):
        _text(self.decision_id,"decision_id"); _text(self.asset_id,"asset_id"); _text(self.asset_class,"asset_class"); _score(self.priority_score,"priority_score")
        if self.rank is not None and self.rank < 1: raise RankingContractError("rank must be positive.")
        if self.comparability is ComparabilityStatus.EXCLUDED and self.rank is not None: raise RankingContractError("excluded opportunities cannot have a rank.")
        if any(v < 0 for v in self.penalties.values()): raise RankingContractError("penalties cannot be negative.")

@dataclass(frozen=True, slots=True)
class PortfolioRankingResult:
    context: PortfolioRankingContext; status: RankingStatus
    ranked_opportunities: Sequence[RankedOpportunity]=field(default_factory=tuple)
    excluded_opportunities: Sequence[RankedOpportunity]=field(default_factory=tuple)
    generated_at: datetime=field(default_factory=lambda:datetime.now(timezone.utc)); ranking_version: str="5.2.1"
    metadata: Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        _aware(self.generated_at,"generated_at"); _text(self.ranking_version,"ranking_version")
        ids=[x.decision_id for x in (*self.ranked_opportunities,*self.excluded_opportunities)]
        if len(ids)!=len(set(ids)): raise RankingContractError("decision_id values must be unique within a ranking result.")
        ranks=[x.rank for x in self.ranked_opportunities]
        if any(r is None for r in ranks) or sorted(ranks)!=list(range(1,len(ranks)+1)): raise RankingContractError("ranked opportunities must have contiguous ranks beginning at 1.")
        if any(x.comparability is not ComparabilityStatus.EXCLUDED for x in self.excluded_opportunities): raise RankingContractError("excluded_opportunities must be marked excluded.")
