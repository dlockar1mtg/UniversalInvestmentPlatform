from dataclasses import replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import pytest
from foundation.intelligence.decision import DecisionAction,DecisionResult,DecisionScore,DecisionStatus,EligibilityStatus
from foundation.intelligence.ranking import *
NOW=datetime(2026,7,17,22,0,tzinfo=timezone.utc)
def value(action=DecisionAction.BUY,confidence=.8,**changes):
 d=DecisionResult("D-1","ETF:VOO","etf",action,DecisionStatus.EVALUATED,EligibilityStatus.ELIGIBLE,
  DecisionScore(80,0,80,scoring_version="5.1.3"),confidence,Decimal("1000"),Decimal("500"),generated_at=NOW-timedelta(hours=1),expires_at=NOW+timedelta(hours=1))
 v=dict(decision=d,context=PortfolioRankingContext("R-1","P-1",NOW,Decimal("3000")),risk_adjusted_opportunity=80,liquidity_quality=90,diversification_contribution=75,portfolio_capacity=85,freshness_score=95);v.update(changes);return PortfolioRankingInput(**v)
def result(v=None):
 v=v or value();c=RankingComparabilityEngine().evaluate(v);return UniversalRankingFactorEngine().evaluate(v,c)
def mapping(r): return {x.factor:x for x in r.factor_scores}
def test_all_eight_factors_created(): assert len(result().factor_scores)==8
def test_decision_score_preserved(): assert mapping(result())[RankingFactor.DECISION_SCORE].raw_score==80
def test_confidence_converted_to_100_scale(): assert mapping(result(value(confidence=.75)))[RankingFactor.CONFIDENCE].raw_score==75
def test_action_strength_mapped(): assert mapping(result())[RankingFactor.ACTION_STRENGTH].raw_score==85
def test_input_factors_preserved():
 r=mapping(result());assert r[RankingFactor.LIQUIDITY].raw_score==90 and r[RankingFactor.FRESHNESS].raw_score==95
def test_contributions_sum_to_total():
 r=result();assert sum(x.weighted_contribution for x in r.factor_scores)==pytest.approx(r.weighted_factor_total)
def test_default_weights_used(): assert sum(x.weight for x in result().factor_scores)==pytest.approx(1)
def test_reasons_are_auditable(): assert all(x.reasons for x in result().factor_scores)
def test_conditional_input_can_be_scored():
 v=value(freshness_score=30);r=UniversalRankingFactorEngine().evaluate(v,RankingComparabilityEngine().evaluate(v));assert r.comparability is ComparabilityStatus.CONDITIONAL
def test_excluded_input_rejected():
 v=value(freshness_score=10)
 with pytest.raises(IncomparableRankingInputError): UniversalRankingFactorEngine().evaluate(v,RankingComparabilityEngine().evaluate(v))
def test_mismatched_comparability_rejected():
 v=value();other=replace(v,decision=replace(v.decision,decision_id="D-2"));c=RankingComparabilityEngine().evaluate(other)
 with pytest.raises(RankingFactorConsistencyError): UniversalRankingFactorEngine().evaluate(v,c)
def test_profile_requires_every_action():
 with pytest.raises(RankingFactorError): RankingFactorProfile(action_strength={})
def test_profile_rejects_invalid_strength():
 strengths=dict(DEFAULT_ACTION_STRENGTH);strengths[DecisionAction.BUY]=101
 with pytest.raises(RankingFactorError): RankingFactorProfile(action_strength=strengths)
def test_custom_action_strength_applied():
 strengths=dict(DEFAULT_ACTION_STRENGTH);strengths[DecisionAction.BUY]=60
 r=UniversalRankingFactorEngine(profile=RankingFactorProfile(strengths)).evaluate(value(),RankingComparabilityEngine().evaluate(value()))
 assert mapping(r)[RankingFactor.ACTION_STRENGTH].raw_score==60
def test_result_rejects_incomplete_factors():
 with pytest.raises(RankingFactorError): RankingFactorResult("D","A",ComparabilityStatus.COMPARABLE,(),0)
