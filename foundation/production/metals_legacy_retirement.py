"""Legacy Metals retirement evidence validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LegacyRetirementResult:
    retirement_id: str
    legacy_system_name: str
    status: str
    schedule_disabled: bool
    observation_window_completed: bool
    legacy_runtime_execution_count: int
    legacy_database_access_count: int
    archive_path: str
    archive_checksum_sha256: str
    archive_checksum_verified: bool
    recovery_procedure_path: str
    owner: str
    evidence_as_of: str
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        row = asdict(self)
        row["reason_codes"] = list(self.reason_codes)
        return row


def load_retirement_evidence(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_retirement_evidence(document: dict[str, Any]) -> LegacyRetirementResult:
    reasons: list[str] = []

    retirement_id = str(document.get("retirement_id", "")).strip()
    legacy_system_name = str(document.get("legacy_system_name", "")).strip()
    schedule_disabled = document.get("schedule_disabled") is True
    observation_window_days = int(document.get("observation_window_days", 0) or 0)
    observation_window_completed = document.get("observation_window_completed") is True
    runtime_count = int(document.get("legacy_runtime_execution_count", -1))
    database_count = int(document.get("legacy_database_access_count", -1))
    archive_path = str(document.get("archive_path", "")).strip()
    checksum = str(document.get("archive_checksum_sha256", "")).strip().lower()
    checksum_verified = document.get("archive_checksum_verified") is True
    recovery_path = str(document.get("recovery_procedure_path", "")).strip()
    owner = str(document.get("owner", "")).strip()
    evidence_as_of = str(document.get("evidence_as_of", "")).strip()

    if not retirement_id:
        reasons.append("MISSING_RETIREMENT_ID")
    if not legacy_system_name:
        reasons.append("MISSING_LEGACY_SYSTEM_NAME")
    if not schedule_disabled:
        reasons.append("SCHEDULE_NOT_DISABLED")
    if not document.get("schedule_disabled_at"):
        reasons.append("MISSING_SCHEDULE_DISABLED_AT")
    if observation_window_days <= 0:
        reasons.append("INVALID_OBSERVATION_WINDOW")
    if not observation_window_completed:
        reasons.append("OBSERVATION_WINDOW_INCOMPLETE")
    if runtime_count < 0:
        reasons.append("MISSING_RUNTIME_EXECUTION_COUNT")
    elif runtime_count > 0:
        reasons.append("LEGACY_RUNTIME_EXECUTION_DETECTED")
    if database_count < 0:
        reasons.append("MISSING_DATABASE_ACCESS_COUNT")
    elif database_count > 0:
        reasons.append("LEGACY_DATABASE_ACCESS_DETECTED")
    if not archive_path:
        reasons.append("MISSING_ARCHIVE_PATH")
    if len(checksum) != 64 or any(char not in "0123456789abcdef" for char in checksum):
        reasons.append("INVALID_ARCHIVE_CHECKSUM")
    if not checksum_verified:
        reasons.append("ARCHIVE_CHECKSUM_NOT_VERIFIED")
    if not recovery_path:
        reasons.append("MISSING_RECOVERY_PROCEDURE")
    if not owner:
        reasons.append("MISSING_OWNER")
    if not evidence_as_of:
        reasons.append("MISSING_EVIDENCE_AS_OF")

    failure_codes = {
        "LEGACY_RUNTIME_EXECUTION_DETECTED",
        "LEGACY_DATABASE_ACCESS_DETECTED",
    }
    if any(reason in failure_codes for reason in reasons):
        status = "FAILED"
    elif reasons:
        status = "INCOMPLETE"
    else:
        status = "PASS"

    return LegacyRetirementResult(
        retirement_id=retirement_id,
        legacy_system_name=legacy_system_name,
        status=status,
        schedule_disabled=schedule_disabled,
        observation_window_completed=observation_window_completed,
        legacy_runtime_execution_count=runtime_count,
        legacy_database_access_count=database_count,
        archive_path=archive_path,
        archive_checksum_sha256=checksum,
        archive_checksum_verified=checksum_verified,
        recovery_procedure_path=recovery_path,
        owner=owner,
        evidence_as_of=evidence_as_of,
        reason_codes=tuple(reasons or ["RETIREMENT_EVIDENCE_COMPLETE"]),
    )


def publish_retirement_result(result: LegacyRetirementResult, output_dir: str | Path) -> None:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    (target / "metals_legacy_retirement_verification.json").write_text(
        json.dumps(result.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
