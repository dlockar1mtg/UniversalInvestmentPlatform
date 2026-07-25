from __future__ import annotations

import json
from pathlib import Path

from foundation.production.metals_runtime_migration import evaluate_contract


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def _contract(capabilities):
    return {"capabilities": capabilities}


def _cap(path: str, state: str = "IMPLEMENTED", *, required: bool = True, hosted: bool = True):
    return {
        "capability_id": path.replace("/", "_"),
        "required": required,
        "legacy_source": "legacy",
        "uip_target": path,
        "migration_state": state,
        "github_hosted_compatible": hosted,
    }


def test_passes_when_every_required_capability_is_implemented(tmp_path: Path):
    target = tmp_path / "native.py"
    target.write_text("ok", encoding="utf-8")
    report = evaluate_contract(_contract([_cap("native.py")]), tmp_path)
    assert report.status == "PASS"
    assert report.reason_codes == ("RUNTIME_MIGRATION_COMPLETE",)


def test_incomplete_when_required_capability_is_planned(tmp_path: Path):
    report = evaluate_contract(_contract([_cap("native.py", "PLANNED")]), tmp_path)
    assert report.status == "INCOMPLETE"
    assert "REQUIRED_CAPABILITIES_INCOMPLETE" in report.reason_codes


def test_failed_when_implemented_target_is_missing(tmp_path: Path):
    report = evaluate_contract(_contract([_cap("missing.py")]), tmp_path)
    assert report.status == "FAILED"
    assert report.missing_target_count == 1


def test_failed_when_capability_is_blocked(tmp_path: Path):
    report = evaluate_contract(_contract([_cap("future.py", "BLOCKED")]), tmp_path)
    assert report.status == "FAILED"


def test_incomplete_when_required_capability_is_not_hosted_compatible(tmp_path: Path):
    report = evaluate_contract(_contract([_cap("future.py", "PLANNED", hosted=False)]), tmp_path)
    assert report.status == "INCOMPLETE"
    assert "NOT_GITHUB_HOSTED_COMPATIBLE" in report.reason_codes


def test_detects_duplicate_capability_ids(tmp_path: Path):
    first = _cap("one.py", "PLANNED")
    second = dict(first)
    report = evaluate_contract(_contract([first, second]), tmp_path)
    assert report.status == "INCOMPLETE"
    assert "DUPLICATE_CAPABILITY_ID" in report.reason_codes


def test_empty_contract_is_incomplete(tmp_path: Path):
    report = evaluate_contract({}, tmp_path)
    assert report.status == "INCOMPLETE"
    assert "MISSING_CAPABILITIES" in report.reason_codes


def test_repository_contract_is_incomplete_without_missing_implemented_targets():
    contract_path = REPOSITORY_ROOT / "config" / "metals" / "runtime_migration_contract.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    report = evaluate_contract(contract, REPOSITORY_ROOT)

    assert report.status == "INCOMPLETE"
    assert report.missing_target_count == 0
    assert report.implemented_count == 8
    assert report.planned_count == 5
    assert report.reason_codes == ("REQUIRED_CAPABILITIES_INCOMPLETE",)
