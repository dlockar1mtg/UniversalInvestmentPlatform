from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from foundation.intelligence.decision import (DecisionAction,DecisionResult,DecisionScore,DecisionStatus,EligibilityStatus)
from foundation.intelligence.ranking import *
NOW=datetime(2026,7,17,22,0,tzinfo=timezone.utc)
def decision():
    return DecisionResult("D-1","ETF:VOO","etf",DecisionAction.BUY,DecisionStatus.EVALUATED,
        EligibilityStatus.ELIGIBLE,DecisionScore(base_score=80,penalty_score=0,final_score=80,scoring_version="5.1.3"),.8,Decimal("1000"),Decimal("500"),generated_at=NOW-timedelta(hours=1))
def context(): return PortfolioRankingContext("R-1","P-1",NOW,Decimal("3000"))
def ranking_input(**changes):
    values=dict(decision=decision(),context=context(),risk_adjusted_opportunity=80,liquidity_quality=90,diversification_contribution=75,portfolio_capacity=85,freshness_score=95); values.update(changes); return PortfolioRankingInput(**values)
def factor(): return RankingFactorScore(RankingFactor.DECISION_SCORE,80,.25,20)
def opportunity(rank=1,excluded=False):
    return RankedOpportunity("D-1","ETF:VOO","etf",None if excluded else rank,80,RankingTier.EXCLUDED if excluded else RankingTier.HIGH,ComparabilityStatus.EXCLUDED if excluded else ComparabilityStatus.COMPARABLE,(factor(),))
def test_context_valid(): assert context().available_capital==Decimal("3000")
def test_context_rejects_naive_time():
    with pytest.raises(RankingContractError): PortfolioRankingContext("R","P",datetime(2026,1,1))
def test_context_rejects_negative_capital():
    with pytest.raises(RankingContractError): PortfolioRankingContext("R","P",NOW,Decimal("-1"))
def test_default_weights_sum_to_one(): assert sum(PortfolioRankingPolicy().factor_weights.values())==pytest.approx(1)
def test_policy_requires_all_factors():
    with pytest.raises(RankingContractError): PortfolioRankingPolicy(factor_weights={})
def test_policy_requires_weight_sum():
    with pytest.raises(RankingContractError): PortfolioRankingPolicy(factor_weights={x:.1 for x in RankingFactor})
def test_input_accepts_decision(): assert ranking_input().decision.asset_id=="ETF:VOO"
@pytest.mark.parametrize("field",["risk_adjusted_opportunity","liquidity_quality","diversification_contribution","portfolio_capacity","freshness_score"])
def test_input_rejects_invalid_scores(field):
    with pytest.raises(RankingContractError): ranking_input(**{field:101})
def test_input_rejects_future_decision():
    with pytest.raises(RankingContractError): ranking_input(decision=replace(decision(),generated_at=NOW+timedelta(seconds=1)))
def test_factor_validates_contribution():
    with pytest.raises(RankingContractError): RankingFactorScore(RankingFactor.CONFIDENCE,80,.2,15)
def test_excluded_opportunity_cannot_have_rank():
    with pytest.raises(RankingContractError): replace(opportunity(excluded=True),rank=1)
def test_result_accepts_contiguous_ranks():
    second=replace(opportunity(),decision_id="D-2",asset_id="CRYPTO:BTC",rank=2)
    assert PortfolioRankingResult(context(),RankingStatus.RANKED,(opportunity(),second)).status is RankingStatus.RANKED
def test_result_rejects_rank_gap():
    with pytest.raises(RankingContractError): PortfolioRankingResult(context(),RankingStatus.RANKED,(replace(opportunity(),rank=2),))
def test_result_rejects_duplicate_decisions():
    with pytest.raises(RankingContractError): PortfolioRankingResult(context(),RankingStatus.RANKED,(opportunity(),replace(opportunity(),rank=2)))
def test_result_requires_excluded_status():
    with pytest.raises(RankingContractError): PortfolioRankingResult(context(),RankingStatus.PARTIAL,(),(opportunity(),))
