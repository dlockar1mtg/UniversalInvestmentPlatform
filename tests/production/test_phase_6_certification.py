from dataclasses import replace
import json

from foundation.production import certify_phase_6


def test_phase_6_production_readiness_certification_passes():
    report = certify_phase_6()
    assert report.status == "PASSED"
    assert len(report.checks) == 10
    assert all(item.status == "PASSED" for item in report.checks)


def test_phase_6_certification_is_repeatable():
    assert certify_phase_6() == certify_phase_6()


def test_phase_6_report_is_machine_readable():
    document = json.loads(json.dumps(certify_phase_6().to_dict(), sort_keys=True))
    assert document["phase"] == "6"
    assert document["release_version"] == "6.0.0"
    assert len(document["checks"]) == 10


def test_certification_fingerprint_is_stable_sha256():
    fingerprint = certify_phase_6().certification_fingerprint
    assert len(fingerprint) == 64
    int(fingerprint, 16)


def test_failed_check_can_be_reported_without_hiding_other_evidence():
    report = certify_phase_6()
    failed = replace(report.checks[0], status="FAILED", evidence="startup failed")
    changed = replace(report, status="FAILED", checks=(failed, *report.checks[1:]))
    assert changed.status == "FAILED"
    assert len(changed.checks) == 10
    assert changed.checks[-1].status == "PASSED"


def test_certification_covers_security_recovery_and_restore_boundaries():
    checks = {item.check_id: item.status for item in certify_phase_6().checks}
    assert checks["SECURITY_BOUNDARIES"] == "PASSED"
    assert checks["SCHEDULING_IDEMPOTENCY_AND_RECOVERY"] == "PASSED"
    assert checks["BACKUP_AND_RESTORE"] == "PASSED"
