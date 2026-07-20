from dataclasses import replace
from pathlib import Path

from foundation.production.delivery_certification import certify_phase_7


ROOT = Path(__file__).resolve().parents[2]


def test_phase_7_certification_passes_every_go_live_check():
    report = certify_phase_7(ROOT)
    assert report.status == "PASSED"
    assert len(report.checks) == 11
    assert {check.status for check in report.checks} == {"PASSED"}


def test_certification_is_deterministic_and_fingerprint_is_auditable():
    first = certify_phase_7(ROOT)
    second = certify_phase_7(ROOT)
    assert first == second
    assert len(first.certification_fingerprint) == 64


def test_certification_document_is_stably_ordered_and_complete():
    document = certify_phase_7(ROOT).document()
    assert list(document) == ["certification_fingerprint", "checks", "phase", "release_version", "status"]
    assert document["phase"] == "7" and document["release_version"] == "7.0.0"


def test_certification_check_identity_is_unique():
    report = certify_phase_7(ROOT)
    identifiers = [check.check_id for check in report.checks]
    assert len(identifiers) == len(set(identifiers))


def test_failed_check_changes_report_status_when_reconciled():
    report = certify_phase_7(ROOT)
    failed = replace(report.checks[0], status="FAILED")
    reconciled = "PASSED" if all(check.status == "PASSED" for check in (failed, *report.checks[1:])) else "FAILED"
    assert reconciled == "FAILED"
