from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

from foundation.production.metals_legacy_retirement import (
    evaluate_retirement_evidence,
    load_retirement_evidence,
    publish_retirement_result,
)

SAMPLE = Path("config/metals/legacy_retirement_validation_sample.json")


def test_complete_retirement_evidence_passes():
    result = evaluate_retirement_evidence(load_retirement_evidence(SAMPLE))
    assert result.status == "PASS"
    assert result.reason_codes == ("RETIREMENT_EVIDENCE_COMPLETE",)


def test_missing_schedule_disablement_is_incomplete():
    document = deepcopy(load_retirement_evidence(SAMPLE))
    document["schedule_disabled"] = False
    result = evaluate_retirement_evidence(document)
    assert result.status == "INCOMPLETE"
    assert "SCHEDULE_NOT_DISABLED" in result.reason_codes


def test_runtime_execution_detection_fails():
    document = deepcopy(load_retirement_evidence(SAMPLE))
    document["legacy_runtime_execution_count"] = 1
    result = evaluate_retirement_evidence(document)
    assert result.status == "FAILED"
    assert "LEGACY_RUNTIME_EXECUTION_DETECTED" in result.reason_codes


def test_database_access_detection_fails():
    document = deepcopy(load_retirement_evidence(SAMPLE))
    document["legacy_database_access_count"] = 2
    result = evaluate_retirement_evidence(document)
    assert result.status == "FAILED"
    assert "LEGACY_DATABASE_ACCESS_DETECTED" in result.reason_codes


def test_invalid_checksum_is_incomplete():
    document = deepcopy(load_retirement_evidence(SAMPLE))
    document["archive_checksum_sha256"] = "bad"
    result = evaluate_retirement_evidence(document)
    assert result.status == "INCOMPLETE"
    assert "INVALID_ARCHIVE_CHECKSUM" in result.reason_codes


def test_publisher_writes_result(tmp_path):
    result = evaluate_retirement_evidence(load_retirement_evidence(SAMPLE))
    publish_retirement_result(result, tmp_path)
    output = tmp_path / "metals_legacy_retirement_verification.json"
    assert output.exists()
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "PASS"


def test_cli_strict_sample_passes(tmp_path):
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/publish_metals_legacy_retirement_verification.py",
            "--input",
            str(SAMPLE),
            "--output-dir",
            str(tmp_path),
            "--strict",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
