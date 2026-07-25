"""Fail-closed readiness checks for the UIP-native Metals runtime."""
from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class NativeReadinessReport:
    status: str
    reason_codes: tuple[str, ...]
    package_id: str | None
    dataset_count: int
    external_dependency_count: int

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["reason_codes"] = list(self.reason_codes)
        return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _looks_external(value: str) -> bool:
    normalized = value.replace("\\", "/")
    return ":/Users/" in normalized or normalized.startswith("/home/")


def evaluate_native_readiness(package_root: Path) -> NativeReadinessReport:
    reasons: list[str] = []
    external = 0
    if not package_root.exists():
        return NativeReadinessReport("FAILED", ("PACKAGE_ROOT_MISSING",), None, 0, 0)
    summary_path = package_root / "package_summary.json"
    manifest_path = package_root / "export_manifest.csv"
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig")) if summary_path.exists() else {}
    if not summary_path.exists():
        reasons.append("MISSING_PACKAGE_SUMMARY")
    rows: list[dict[str, str]] = []
    if not manifest_path.exists():
        reasons.append("MISSING_EXPORT_MANIFEST")
    else:
        with manifest_path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
    for row in rows:
        path = package_root / row.get("filename", "")
        if not path.exists():
            reasons.append("MISSING_DATASET_FILE")
            continue
        if row.get("sha256") != _sha256(path):
            reasons.append("CHECKSUM_MISMATCH")
        with path.open(newline="", encoding="utf-8-sig") as handle:
            count = sum(1 for _ in csv.DictReader(handle))
        if count != int(row.get("row_count", "-1")):
            reasons.append("ROW_COUNT_MISMATCH")
        if _looks_external(path.read_text(encoding="utf-8-sig", errors="ignore")):
            external += 1
    required = {"export_manifest.csv", "platform_status.csv", "package_summary.json"}
    present = {item.name for item in package_root.iterdir()}
    if not required.issubset(present):
        reasons.append("REQUIRED_PACKAGE_FILES_MISSING")
    if summary.get("validation_status") != "PASS":
        reasons.append("PACKAGE_NOT_VALIDATED")
    if external:
        reasons.append("EXTERNAL_RUNTIME_DEPENDENCY")
    status = "PASS" if not reasons else "FAILED"
    if status == "PASS":
        reasons.append("UIP_NATIVE_METALS_READY")
    return NativeReadinessReport(status, tuple(dict.fromkeys(reasons)), summary.get("package_id"), len(rows), external)


def publish_native_readiness(report: NativeReadinessReport, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")
    return output_path
