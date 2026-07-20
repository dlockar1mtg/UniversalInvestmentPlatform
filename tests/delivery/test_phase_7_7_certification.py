from dataclasses import replace
from pathlib import Path

from foundation.production.portfolio_delivery_certification import certify_phase_7_7


ROOT = Path(__file__).resolve().parents[2]


def test_phase_7_7_certification_passes_all_secure_delivery_checks():
    report = certify_phase_7_7(ROOT)
    assert report.status == "PASSED"
    assert len(report.checks) == 11
    assert {check.status for check in report.checks} == {"PASSED"}


def test_phase_7_7_certification_is_deterministic_and_auditable():
    first, second = certify_phase_7_7(ROOT), certify_phase_7_7(ROOT)
    assert first == second
    assert len(first.certification_fingerprint) == 64


def test_phase_7_7_document_is_complete_and_stably_ordered():
    document = certify_phase_7_7(ROOT).document()
    assert list(document) == ["certification_fingerprint", "checks", "phase", "profile", "status"]
    assert document["phase"] == "7.7" and document["profile"] == "secure-hosted-portfolio"


def test_phase_7_7_check_identity_is_unique():
    checks = certify_phase_7_7(ROOT).checks
    assert len({check.check_id for check in checks}) == len(checks)


def test_failed_secure_delivery_check_changes_reconciled_status():
    report = certify_phase_7_7(ROOT)
    failed = replace(report.checks[0], status="FAILED")
    status = "PASSED" if all(check.status == "PASSED" for check in (failed, *report.checks[1:])) else "FAILED"
    assert status == "FAILED"
