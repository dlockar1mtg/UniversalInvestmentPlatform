"""Phase 5.1 Universal Decision Engine certification runner."""
import json, subprocess, sys
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from time import perf_counter
from foundation.intelligence.decision import (DecisionContext, DecisionEvidence, DecisionInput,
    EligibilityStatus, UniversalDecisionDeserializer, UniversalDecisionOrchestrator,
    UniversalDecisionSerializer)
from .certification_profile import DecisionCertificationProfile
from .certification_report import CertificationReport
from .certification_result import CertificationResult
from .deterministic_validator import validate_determinism
from .regression_suite import validate_scenarios
from .replay_validator import validate_replay

FIXED_TIME = datetime(2026, 7, 17, 21, 0, tzinfo=timezone.utc)

def _input(asset_id="ETF:VOO", asset_class="etf", **changes):
    values = dict(asset_id=asset_id, asset_class=asset_class, time_horizon="3_year",
        context=DecisionContext(portfolio_id="PORTFOLIO-CERTIFICATION", as_of=FIXED_TIME,
            portfolio_value=Decimal("100000"), available_capital=Decimal("3000"),
            current_position_value=Decimal("0"), current_asset_weight=0.0,
            current_asset_class_weight=0.20), forecast_strength=88.0, forecast_confidence=86.0,
        historical_reliability=82.0, risk_adjusted_opportunity=84.0,
        market_regime_alignment=76.0, diversification_fit=80.0, liquidity_quality=95.0,
        valuation_attractiveness=79.0, data_quality=96.0,
        evidence=(DecisionEvidence(evidence_id="EVIDENCE-CERTIFICATION", category="forecast",
            source="phase_5_1_certification", description="Certification evidence.", observed_at=FIXED_TIME),),
        metadata={"source_system": "certification"})
    values.update(changes); return DecisionInput(**values)

def _result(value=None):
    return UniversalDecisionOrchestrator().evaluate(value or _input(), generated_at=FIXED_TIME,
        decision_id="DECISION-CERTIFICATION-001")

def _simple(name, passed, started, **metadata):
    return CertificationResult(name, passed, perf_counter()-started, datetime.now(timezone.utc),
        metadata, f"{name.replace('_', ' ').title()} {'passed' if passed else 'failed'}.")

class DecisionCertificationRunner:
    def __init__(self, profile=None): self.profile = profile or DecisionCertificationProfile()
    def run(self, repository_root: Path | None = None):
        report = CertificationReport("5.1", "5.1.10"); serializer = UniversalDecisionSerializer(); result = _result()
        if self.profile.verify_determinism:
            report.add(validate_determinism(lambda: serializer.to_json(result)))
        if self.profile.verify_replay:
            raw = serializer.to_json(result)
            report.add(validate_replay(result.decision_result, lambda: UniversalDecisionDeserializer().from_json(raw)))
        if self.profile.verify_serialization:
            started=perf_counter(); payload=json.loads(serializer.to_json(result))
            report.add(_simple("serialization", payload.get("schema_version")=="1.0" and payload["decision"]["decision_id"]==result.decision_id, started))
        if self.profile.verify_constraints:
            started=perf_counter(); context=replace(_input().context, available_capital=Decimal("0"))
            zero=_result(_input(context=context)).decision_result; illiquid=_result(_input(liquidity_quality=10.0)).decision_result
            report.add(_simple("constraints", zero.recommended_allocation==0 and illiquid.eligibility is EligibilityStatus.INELIGIBLE, started))
        if self.profile.verify_cross_asset:
            started=perf_counter(); assets=(("ETF:VOO","etf"),("CRYPTO:BTC","crypto"),("METAL:GOLD","metal"),("MTG:DISPLAY","collectible"))
            decisions=[_result(_input(a,c)).decision_result for a,c in assets]
            report.add(_simple("cross_asset", all(d.asset_id for d in decisions), started, asset_count=len(decisions)))
        if self.profile.verify_regression:
            report.add(validate_scenarios((("eligible allocation",lambda:_result().decision_result.recommended_allocation>0),
                ("low data quality",lambda:_result(_input(data_quality=20.0)).decision_result.recommended_allocation==0),
                ("stable identifier",lambda:_result().decision_id==_result().decision_id))))
        if self.profile.verify_repository_tests and repository_root:
            started=perf_counter(); completed=subprocess.run([sys.executable,"-m","pytest","tests/intelligence/decision","-q"],cwd=repository_root,capture_output=True,text=True)
            report.add(_simple("repository_tests", completed.returncode==0, started, returncode=completed.returncode, output=completed.stdout[-1000:]))
        return report

