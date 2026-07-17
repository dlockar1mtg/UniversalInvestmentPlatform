from datetime import datetime, timezone
import pytest
from foundation.intelligence.decision.certification import (CertificationReport, CertificationResult,
    DecisionCertificationProfile, DecisionCertificationRunner, validate_determinism, validate_scenarios)

def test_default_profile_enables_all_gates():
    p=DecisionCertificationProfile(); assert all((p.verify_determinism,p.verify_replay,p.verify_serialization,p.verify_constraints,p.verify_cross_asset,p.verify_repository_tests,p.verify_regression))
def test_determinism_passes(): assert validate_determinism(lambda:"stable").passed
def test_determinism_fails():
    values=iter(("one","two","three")); assert not validate_determinism(lambda:next(values)).passed
def test_regression_records_failure():
    r=validate_scenarios((("pass",lambda:True),("fail",lambda:False))); assert r.metadata["failures"]==["fail"]
def test_report_requires_every_gate():
    now=datetime.now(timezone.utc); r=CertificationReport("5.1","5.1.10"); r.add(CertificationResult("one",True,0,now)); r.add(CertificationResult("two",False,0,now)); assert not r.passed
def test_report_renders_markdown():
    r=CertificationReport("5.1","5.1.10"); r.add(CertificationResult("gate",True,0,datetime.now(timezone.utc))); assert "Overall status:** PASS" in r.to_markdown()
def test_naive_timestamp_rejected():
    with pytest.raises(ValueError): CertificationResult("gate",True,0,datetime(2026,7,17))
def test_negative_duration_rejected():
    with pytest.raises(ValueError): CertificationResult("gate",True,-1,datetime.now(timezone.utc))
def test_core_certification_gates_pass():
    r=DecisionCertificationRunner(DecisionCertificationProfile(verify_repository_tests=False)).run(); assert r.passed,r.to_markdown()
    assert {x.validator_name for x in r.results}=={"determinism","replay","serialization","constraints","cross_asset","regression"}
