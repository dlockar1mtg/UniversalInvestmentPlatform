from dataclasses import replace
from datetime import datetime,timedelta,timezone
from decimal import Decimal
import pytest
from foundation.intelligence.decision import DecisionAction,DecisionResult,DecisionScore,DecisionStatus,EligibilityStatus
from foundation.intelligence.ranking import *
NOW=datetime(2026,7,17,22,0,tzinfo=timezone.utc)
def value(decision_id="D-1",asset_id="ETF:VOO",score=80,confidence=.8,freshness=95):
 d=DecisionResult(decision_id,asset_id,"etf",DecisionAction.BUY,DecisionStatus.EVALUATED,EligibilityStatus.ELIGIBLE,DecisionScore(score,0,score),confidence,Decimal("1000"),Decimal("500"),generated_at=NOW-timedelta(hours=1),expires_at=NOW+timedelta(hours=1))
 return PortfolioRankingInput(d,PortfolioRankingContext("R-1","P-1",NOW,Decimal("3000")),80,90,75,85,freshness)
def artifacts(v=None):
 v=v or value();c=RankingComparabilityEngine().evaluate(v);f=UniversalRankingFactorEngine().evaluate(v,c);p=CompositePriorityScoringEngine().score(v,f);return v,f,p
def test_base_score_comes_from_factors():
 v,f,p=artifacts();assert p.base_factor_score==pytest.approx(f.weighted_factor_total)
def test_comparable_has_no_default_penalty(): assert artifacts()[2].penalties=={}
def test_conditional_penalty_applied():
 v,f,p=artifacts(value(freshness=30));assert p.penalties["conditional_comparability"]==5 and p.final_priority_score==pytest.approx(p.base_factor_score-5)
def test_additional_penalties_are_explicit():
 v,f,_=artifacts();p=CompositePriorityScoringEngine().score(v,f,{"policy":7});assert p.final_priority_score==pytest.approx(p.base_factor_score-7)
def test_penalties_floor_score_at_zero():
 v,f,_=artifacts();p=CompositePriorityScoringEngine().score(v,f,{"large":100});assert p.final_priority_score==0
@pytest.mark.parametrize("score,tier",[(90,RankingTier.HIGHEST),(80,RankingTier.HIGH),(65,RankingTier.MEDIUM),(50,RankingTier.LOW),(30,RankingTier.DEFERRED)])
def test_tier_boundaries(score,tier): assert PriorityScoringProfile().tier(score) is tier
def test_threshold_profile_validated():
 with pytest.raises(PriorityConfigurationError): PriorityScoringProfile(highest_threshold=70,high_threshold=80)
def test_mismatched_factor_rejected():
 v,f,_=artifacts();f=replace(f,decision_id="OTHER")
 with pytest.raises(PriorityConsistencyError): CompositePriorityScoringEngine().score(v,f)
def test_negative_penalty_rejected():
 v,f,_=artifacts()
 with pytest.raises(PriorityScoringError): CompositePriorityScoringEngine().score(v,f,{"bad":-1})
def test_rank_orders_priority_descending():
 a=artifacts(value("D-1","ETF:VOO",90,.9));b=artifacts(value("D-2","ETF:SCHD",60,.6));r=CompositePriorityScoringEngine().rank((b,a));assert [x.decision_id for x in r]==["D-1","D-2"]
def test_tie_breaks_by_confidence():
 a=artifacts(value("D-1","ETF:VOO",80,.9));b=artifacts(value("D-2","ETF:SCHD",82,.8));
 # force equal final scores while retaining factor inputs
 b=(b[0],b[1],replace(b[2],base_factor_score=a[2].base_factor_score,final_priority_score=a[2].final_priority_score,tier=a[2].tier))
 r=CompositePriorityScoringEngine().rank((b,a));assert r[0].decision_id=="D-1"
def test_final_tie_breaks_by_asset_id():
 a=artifacts(value("D-2","ETF:ZZZ"));b=artifacts(value("D-1","ETF:AAA"));r=CompositePriorityScoringEngine().rank((a,b));assert r[0].asset_id=="ETF:AAA"
def test_ranks_are_contiguous():
 a=artifacts(value("D-1","ETF:VOO"));b=artifacts(value("D-2","ETF:SCHD"));assert [x.rank for x in CompositePriorityScoringEngine().rank((a,b))]==[1,2]
