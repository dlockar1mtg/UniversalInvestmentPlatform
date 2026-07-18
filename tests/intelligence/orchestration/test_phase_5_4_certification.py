from dataclasses import replace
import json

from foundation.intelligence.orchestration.certification import (
    CertificationStatus,
    build_reference_certification_scenario,
    certify_phase_5_4,
)


def test_reference_cross_asset_certification_passes_all_checks():
    report = certify_phase_5_4()
    assert report.passed
    assert report.status is CertificationStatus.PASSED
    assert len(report.checks) == 10
    assert all(item.status is CertificationStatus.PASSED for item in report.checks)


def test_certification_is_repeatable_with_stable_fingerprint():
    first = certify_phase_5_4()
    second = certify_phase_5_4()
    assert first == second
    assert len(first.certification_fingerprint) == 64


def test_report_is_machine_readable():
    report = certify_phase_5_4()
    payload = json.loads(report.to_json())
    assert payload["phase"] == "5.4"
    assert payload["status"] == "PASSED"
    assert payload["run_id"] == "phase-5.4-certification"
    assert payload["certification_fingerprint"] == report.certification_fingerprint


def test_reference_scenario_covers_required_groups_and_quarantine_boundary():
    scenario = build_reference_certification_scenario()
    groups = {item.group_key for item in scenario.request.opportunities}
    assert set(scenario.expected_groups) == {"crypto", "etf", "metals", "mtg"}
    assert set(scenario.expected_groups).issubset(groups)
    assert scenario.quarantined_opportunity_id == "INVALID-HANDOFF"


def test_pipeline_exception_becomes_failed_certification_report():
    scenario = build_reference_certification_scenario()
    invalid = replace(scenario, policy=None)
    report = certify_phase_5_4(invalid)
    assert not report.passed
    assert report.certification_fingerprint is None
    assert report.checks[-1].check_id == "PIPELINE_EXECUTION"
    assert report.checks[-1].status is CertificationStatus.FAILED


def test_each_certification_check_contains_auditable_evidence():
    report = certify_phase_5_4()
    assert all(item.check_id and item.evidence for item in report.checks)
