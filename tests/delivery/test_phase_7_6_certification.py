from pathlib import Path
from foundation.production.free_staging_certification import certify_phase_7_6
ROOT = Path(__file__).resolve().parents[2]

def test_free_staging_certification_passes_all_checks():
    report = certify_phase_7_6(ROOT)
    assert report.status == "PASSED" and len(report.checks) == 8
    assert all(check.status == "PASSED" for check in report.checks)

def test_free_staging_certification_is_deterministic():
    assert certify_phase_7_6(ROOT) == certify_phase_7_6(ROOT)

def test_free_staging_document_identifies_nonproduction_profile():
    document = certify_phase_7_6(ROOT).document()
    assert document["phase"] == "7.6" and document["profile"] == "render-free-neon-free"

def test_free_staging_checks_have_unique_identity():
    checks = certify_phase_7_6(ROOT).checks
    assert len({check.check_id for check in checks}) == len(checks)
