from dataclasses import replace
import json

from foundation.intelligence.monitoring.certification import certify_phase_5_5


def test_phase_5_5_certification_passes_all_checks():
    report = certify_phase_5_5()
    assert report.status == "PASSED"
    assert len(report.checks) == 10
    assert all(item.status == "PASSED" for item in report.checks)


def test_certification_is_repeatable():
    assert certify_phase_5_5() == certify_phase_5_5()


def test_certification_report_is_machine_readable():
    report = certify_phase_5_5()
    encoded = json.dumps(report.to_dict(), sort_keys=True)
    decoded = json.loads(encoded)
    assert decoded["phase"] == "5.5"
    assert decoded["monitoring_run_id"] == "phase-5.5-certification"


def test_certification_fingerprint_is_stable_sha256():
    fingerprint = certify_phase_5_5().certification_fingerprint
    assert len(fingerprint) == 64
    int(fingerprint, 16)


def test_report_status_reflects_failed_check_without_hiding_evidence():
    report = certify_phase_5_5()
    failed = replace(report.checks[0], status="FAILED", evidence="coverage failed")
    changed = replace(report, status="FAILED", checks=(failed, *report.checks[1:]))
    assert changed.status == "FAILED"
    assert len(changed.checks) == 10
    assert changed.checks[-1].status == "PASSED"


def test_certification_covers_control_and_output_boundaries():
    checks = {item.check_id: item for item in certify_phase_5_5().checks}
    assert checks["COOLDOWN_PROTECTION"].status == "PASSED"
    assert checks["CRITICAL_ESCALATION"].status == "PASSED"
    assert checks["UNIFIED_OUTPUT_INTEGRITY"].status == "PASSED"
