from dataclasses import replace
import json

from foundation.intelligence.allocation.certification import (
    CertificationStatus, build_reference_certification_scenario, certify_phase_5_3,
)


def test_reference_cross_asset_certification_passes_all_checks():
    report = certify_phase_5_3()
    assert report.passed
    assert report.status is CertificationStatus.PASSED
    assert len(report.checks) == 10
    assert all(check.status is CertificationStatus.PASSED for check in report.checks)


def test_certification_is_repeatable_with_stable_fingerprint():
    first = certify_phase_5_3()
    second = certify_phase_5_3()
    assert first == second
    assert len(first.certification_fingerprint) == 64


def test_report_is_machine_readable():
    report = certify_phase_5_3()
    payload = json.loads(report.to_json())
    assert payload["phase"] == "5.3"
    assert payload["status"] == "PASSED"
    assert payload["certification_fingerprint"] == report.certification_fingerprint


def test_reference_scenario_covers_crypto_etf_metals_and_mtg():
    scenario = build_reference_certification_scenario()
    assert {item.request.group_key for item in scenario.audit_inputs} == {
        "crypto", "etf", "metals", "mtg"
    }


def test_invalid_duplicate_scenario_becomes_failed_report():
    scenario = build_reference_certification_scenario()
    invalid = replace(
        scenario,
        candidates=(scenario.candidates[0], scenario.candidates[0]),
    )
    report = certify_phase_5_3(invalid)
    assert not report.passed
    assert report.certification_fingerprint is None
    assert report.checks[-1].check_id == "PIPELINE_EXECUTION"


def test_each_certification_check_contains_evidence():
    report = certify_phase_5_3()
    assert all(check.check_id and check.evidence for check in report.checks)
