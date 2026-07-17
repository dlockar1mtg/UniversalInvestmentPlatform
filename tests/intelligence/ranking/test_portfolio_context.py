from datetime import datetime,timedelta,timezone
from decimal import Decimal
import pytest
from foundation.intelligence.decision import DecisionAction,DecisionResult,DecisionScore,DecisionStatus,EligibilityStatus
from foundation.intelligence.ranking import *
NOW=datetime(2026,7,17,22,0,tzinfo=timezone.utc)
def value():
 d=DecisionResult("D-1","ETF:VOO","etf",DecisionAction.BUY,DecisionStatus.EVALUATED,EligibilityStatus.ELIGIBLE,DecisionScore(80,0,80),.8,Decimal("1000"),Decimal("500"),generated_at=NOW-timedelta(hours=1),expires_at=NOW+timedelta(hours=1))
 return PortfolioRankingInput(d,PortfolioRankingContext("R-1","P-1",NOW,Decimal("3000")),80,90,0,0,95)
def snapshot(**changes):
 v=dict(portfolio_id="P-1",as_of=NOW,portfolio_value=Decimal("100000"),asset_weights={"ETF:VOO":.05},asset_class_weights={"etf":.30});v.update(changes);return PortfolioExposureSnapshot(**v)
def candidate(**changes):
 v=dict(asset_id="ETF:VOO",asset_class="etf",target_asset_weight=.08,maximum_asset_weight=.10,target_asset_class_weight=.40,maximum_asset_class_weight=.50,correlation_to_portfolio=.5);v.update(changes);return CandidatePortfolioContext(**v)
def result(**changes): return PortfolioContextIntelligenceEngine().evaluate(value(),snapshot(),candidate(**changes))
def test_current_exposures_loaded(): assert result().current_asset_weight==.05 and result().current_asset_class_weight==.30
def test_target_gaps_calculated(): assert result().asset_target_gap==pytest.approx(.03)
def test_headroom_calculated(): assert result().asset_headroom==pytest.approx(.05)
def test_capacity_uses_binding_headroom(): assert result().portfolio_capacity==pytest.approx(40)
def test_correlation_transformed(): assert result().correlation_score==25
def test_negative_correlation_improves_diversification(): assert result(correlation_to_portfolio=-.5).diversification_contribution>result(correlation_to_portfolio=.5).diversification_contribution
def test_concentration_pressure_calculated(): assert result().concentration_pressure==pytest.approx(60)
def test_enrich_returns_new_input():
 original=value();enriched,r=PortfolioContextIntelligenceEngine().enrich(original,snapshot(),candidate());assert original.diversification_contribution==0 and enriched.diversification_contribution==r.diversification_contribution
def test_enrichment_preserves_decision():
 original=value();enriched,_=PortfolioContextIntelligenceEngine().enrich(original,snapshot(),candidate());assert enriched.decision is original.decision
def test_new_asset_uses_zero_weight():
 s=snapshot(asset_weights={});assert PortfolioContextIntelligenceEngine().evaluate(value(),s,candidate()).current_asset_weight==0
def test_snapshot_rejects_naive_time():
 with pytest.raises(PortfolioContextError): snapshot(as_of=datetime(2026,1,1))
def test_snapshot_rejects_excess_total():
 with pytest.raises(PortfolioContextError): snapshot(asset_weights={"A":.6,"B":.6})
def test_candidate_rejects_target_above_maximum():
 with pytest.raises(PortfolioContextError): candidate(target_asset_weight=.2,maximum_asset_weight=.1)
def test_candidate_rejects_invalid_correlation():
 with pytest.raises(PortfolioContextError): candidate(correlation_to_portfolio=1.1)
def test_profile_weights_validated():
 with pytest.raises(PortfolioContextConfigurationError): PortfolioContextProfile(.5,.5,.5)
def test_portfolio_identity_must_match():
 with pytest.raises(PortfolioContextConsistencyError): PortfolioContextIntelligenceEngine().evaluate(value(),snapshot(portfolio_id="OTHER"),candidate())
def test_asset_identity_must_match():
 with pytest.raises(PortfolioContextConsistencyError): PortfolioContextIntelligenceEngine().evaluate(value(),snapshot(),candidate(asset_id="ETF:SCHD"))
def test_future_snapshot_rejected():
 with pytest.raises(PortfolioContextConsistencyError): PortfolioContextIntelligenceEngine().evaluate(value(),snapshot(as_of=NOW+timedelta(seconds=1)),candidate())
