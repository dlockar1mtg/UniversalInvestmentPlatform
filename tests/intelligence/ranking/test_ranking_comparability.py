from datetime import datetime,timedelta,timezone
from decimal import Decimal
import pytest
from foundation.intelligence.decision import DecisionAction,DecisionResult,DecisionScore,DecisionStatus,EligibilityStatus
from foundation.intelligence.ranking import *
NOW=datetime(2026,7,17,22,0,tzinfo=timezone.utc)
def decision(**changes):
 v=dict(decision_id="D-1",asset_id="ETF:VOO",asset_class="etf",action=DecisionAction.BUY,status=DecisionStatus.EVALUATED,eligibility=EligibilityStatus.ELIGIBLE,score=DecisionScore(80,0,80,scoring_version="5.1.3"),confidence=.8,maximum_allocation=Decimal("1000"),recommended_allocation=Decimal("500"),generated_at=NOW-timedelta(hours=1),expires_at=NOW+timedelta(hours=1));v.update(changes);return DecisionResult(**v)
def value(**changes):
 v=dict(decision=decision(),context=PortfolioRankingContext("R-1","P-1",NOW,Decimal("3000")),risk_adjusted_opportunity=80,liquidity_quality=90,diversification_contribution=75,portfolio_capacity=85,freshness_score=95);v.update(changes);return PortfolioRankingInput(**v)
def status(v): return RankingComparabilityEngine().evaluate(v).status
def test_valid_buy_comparable(): assert status(value()) is ComparabilityStatus.COMPARABLE
def test_expired_time_excluded(): assert status(value(decision=decision(expires_at=NOW))) is ComparabilityStatus.EXCLUDED
def test_expired_status_excluded(): assert status(value(decision=decision(status=DecisionStatus.EXPIRED))) is ComparabilityStatus.EXCLUDED
@pytest.mark.parametrize("x",[EligibilityStatus.INELIGIBLE,EligibilityStatus.INSUFFICIENT_DATA])
def test_bad_eligibility_excluded(x): assert status(value(decision=decision(eligibility=x))) is ComparabilityStatus.EXCLUDED
@pytest.mark.parametrize("x",[DecisionAction.REDUCE,DecisionAction.SELL,DecisionAction.AVOID,DecisionAction.INELIGIBLE,DecisionAction.INSUFFICIENT_DATA])
def test_non_opportunity_actions_excluded(x): assert status(value(decision=decision(action=x))) is ComparabilityStatus.EXCLUDED
def test_hold_excluded_default(): assert not RankingComparabilityEngine().evaluate(value(decision=decision(action=DecisionAction.HOLD))).may_rank
def test_hold_profile_enabled(): assert RankingComparabilityEngine(RankingComparabilityProfile(include_hold_actions=True)).evaluate(value(decision=decision(action=DecisionAction.HOLD))).may_rank
def test_zero_capacity_excluded(): assert status(value(decision=decision(maximum_allocation=Decimal(0),recommended_allocation=Decimal(0)))) is ComparabilityStatus.EXCLUDED
def test_low_freshness_conditional(): assert status(value(freshness_score=30)) is ComparabilityStatus.CONDITIONAL
def test_very_low_freshness_excluded(): assert status(value(freshness_score=10)) is ComparabilityStatus.EXCLUDED
def test_conditional_eligibility_conditional(): assert status(value(decision=decision(eligibility=EligibilityStatus.CONDITIONALLY_ELIGIBLE))) is ComparabilityStatus.CONDITIONAL
def test_failures_preserved(): assert RankingComparabilityEngine().evaluate(value(freshness_score=30)).reasons
def test_batch_order():
 second=value(decision=decision(decision_id="D-2",asset_id="CRYPTO:BTC"));assert [x.decision_id for x in RankingComparabilityEngine().evaluate_batch((value(),second))]==["D-1","D-2"]
def test_batch_duplicate_rejected():
 with pytest.raises(DuplicateRankingDecisionError): RankingComparabilityEngine().evaluate_batch((value(),value()))
def test_profile_thresholds_validated():
 with pytest.raises(ComparabilityConfigurationError): RankingComparabilityProfile(minimum_freshness_score=10,exclusion_freshness_score=20)
