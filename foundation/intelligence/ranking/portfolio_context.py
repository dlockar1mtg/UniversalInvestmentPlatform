"""Portfolio-relative diversification and capacity intelligence."""
from dataclasses import dataclass,field,replace
from datetime import datetime
from decimal import Decimal
from math import isfinite
from typing import Any,Mapping,Sequence
from .contracts import PortfolioRankingInput,RankingContractError
class PortfolioContextError(RankingContractError): pass
class PortfolioContextConfigurationError(PortfolioContextError): pass
class PortfolioContextConsistencyError(PortfolioContextError): pass
def _ratio(value,name):
    if not isfinite(float(value)) or not 0<=float(value)<=1: raise PortfolioContextError(f"{name} must be between 0 and 1.")
def _clamp(value): return max(0.0,min(100.0,float(value)))
@dataclass(frozen=True,slots=True)
class PortfolioExposureSnapshot:
    portfolio_id:str; as_of:datetime; portfolio_value:Decimal
    asset_weights:Mapping[str,float]=field(default_factory=dict)
    asset_class_weights:Mapping[str,float]=field(default_factory=dict)
    metadata:Mapping[str,Any]=field(default_factory=dict)
    def __post_init__(self):
        if not self.portfolio_id.strip(): raise PortfolioContextError("portfolio_id cannot be empty.")
        if self.as_of.tzinfo is None: raise PortfolioContextError("as_of must be timezone-aware.")
        if self.portfolio_value<0: raise PortfolioContextError("portfolio_value cannot be negative.")
        for k,v in self.asset_weights.items():
            if not str(k).strip(): raise PortfolioContextError("asset identifiers cannot be empty.")
            _ratio(v,f"asset_weights[{k}]")
        for k,v in self.asset_class_weights.items():
            if not str(k).strip(): raise PortfolioContextError("asset-class identifiers cannot be empty.")
            _ratio(v,f"asset_class_weights[{k}]")
        if sum(self.asset_weights.values())>1.000001 or sum(self.asset_class_weights.values())>1.000001: raise PortfolioContextError("exposure weights cannot sum above 1.0.")
@dataclass(frozen=True,slots=True)
class CandidatePortfolioContext:
    asset_id:str; asset_class:str; target_asset_weight:float; maximum_asset_weight:float
    target_asset_class_weight:float; maximum_asset_class_weight:float
    correlation_to_portfolio:float=0.0
    def __post_init__(self):
        if not self.asset_id.strip() or not self.asset_class.strip(): raise PortfolioContextError("candidate identifiers cannot be empty.")
        for name in ("target_asset_weight","maximum_asset_weight","target_asset_class_weight","maximum_asset_class_weight"): _ratio(getattr(self,name),name)
        if self.target_asset_weight>self.maximum_asset_weight or self.target_asset_class_weight>self.maximum_asset_class_weight: raise PortfolioContextError("target weights cannot exceed maximum weights.")
        if not isfinite(float(self.correlation_to_portfolio)) or not -1<=self.correlation_to_portfolio<=1: raise PortfolioContextError("correlation_to_portfolio must be between -1 and 1.")
@dataclass(frozen=True,slots=True)
class PortfolioContextProfile:
    correlation_weight:float=.40; target_gap_weight:float=.35; class_headroom_weight:float=.25
    context_version:str="5.2.5"
    def __post_init__(self):
        weights=(self.correlation_weight,self.target_gap_weight,self.class_headroom_weight)
        if any(not 0<=x<=1 for x in weights) or abs(sum(weights)-1)>1e-9: raise PortfolioContextConfigurationError("diversification weights must be between 0 and 1 and sum to 1.")
        if not self.context_version.strip(): raise PortfolioContextConfigurationError("context_version cannot be empty.")
@dataclass(frozen=True,slots=True)
class PortfolioContextResult:
    asset_id:str; current_asset_weight:float; current_asset_class_weight:float
    asset_target_gap:float; asset_class_target_gap:float; asset_headroom:float; asset_class_headroom:float
    correlation_score:float; diversification_contribution:float; portfolio_capacity:float
    concentration_pressure:float; reasons:Sequence[str]=field(default_factory=tuple)
    context_version:str="5.2.5"
    def __post_init__(self):
        for name in ("correlation_score","diversification_contribution","portfolio_capacity","concentration_pressure"):
            if not 0<=getattr(self,name)<=100: raise PortfolioContextError(f"{name} must be between 0 and 100.")
class PortfolioContextIntelligenceEngine:
    def __init__(self,profile=None): self.profile=profile or PortfolioContextProfile()
    def evaluate(self,value:PortfolioRankingInput,snapshot:PortfolioExposureSnapshot,candidate:CandidatePortfolioContext):
        d=value.decision
        if snapshot.portfolio_id!=value.context.portfolio_id: raise PortfolioContextConsistencyError("snapshot portfolio_id must match ranking context.")
        if candidate.asset_id!=d.asset_id or candidate.asset_class!=d.asset_class: raise PortfolioContextConsistencyError("candidate identity must match decision.")
        if snapshot.as_of>value.context.as_of: raise PortfolioContextConsistencyError("snapshot cannot occur after ranking as_of.")
        aw=float(snapshot.asset_weights.get(d.asset_id,0));cw=float(snapshot.asset_class_weights.get(d.asset_class,0))
        ag=candidate.target_asset_weight-aw;cg=candidate.target_asset_class_weight-cw
        ah=max(0.0,candidate.maximum_asset_weight-aw);ch=max(0.0,candidate.maximum_asset_class_weight-cw)
        asset_capacity=_clamp(100*ah/candidate.maximum_asset_weight) if candidate.maximum_asset_weight else 0
        class_capacity=_clamp(100*ch/candidate.maximum_asset_class_weight) if candidate.maximum_asset_class_weight else 0
        capacity=min(asset_capacity,class_capacity)
        target_score=_clamp(50+50*ag/max(candidate.target_asset_weight,.000001))
        class_headroom=_clamp(100*ch/max(candidate.maximum_asset_class_weight,.000001))
        correlation=_clamp((1-candidate.correlation_to_portfolio)*50)
        diversification=_clamp(correlation*self.profile.correlation_weight+target_score*self.profile.target_gap_weight+class_headroom*self.profile.class_headroom_weight)
        asset_pressure=_clamp(100*aw/max(candidate.maximum_asset_weight,.000001));class_pressure=_clamp(100*cw/max(candidate.maximum_asset_class_weight,.000001))
        pressure=max(asset_pressure,class_pressure)
        reasons=(f"Correlation contribution score: {correlation:.4f}.",f"Target-gap score: {target_score:.4f}.",f"Asset-class headroom score: {class_headroom:.4f}.",f"Portfolio capacity: {capacity:.4f}.")
        return PortfolioContextResult(d.asset_id,aw,cw,ag,cg,ah,ch,correlation,diversification,capacity,pressure,reasons,self.profile.context_version)
    def enrich(self,value,snapshot,candidate):
        result=self.evaluate(value,snapshot,candidate)
        metadata=dict(value.metadata);metadata["portfolio_context_version"]=result.context_version;metadata["concentration_pressure"]=result.concentration_pressure
        return replace(value,diversification_contribution=result.diversification_contribution,portfolio_capacity=result.portfolio_capacity,metadata=metadata),result
