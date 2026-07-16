from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


VALID_SEVERITIES = {
    "info",
    "warning",
    "error",
    "critical",
}


@dataclass(frozen=True)
class ValidationFinding:
    validation_id: str
    category: str
    severity: str
    message: str
    platform_id: str | None = None
    run_id: str | None = None
    contract_name: str | None = None
    record_identifier: str | None = None
    suggested_action: str | None = None

    def __post_init__(self) -> None:
        if self.severity not in VALID_SEVERITIES:
            raise ValueError(
                f"Unsupported severity: {self.severity}"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def has_failures(
    findings: list[ValidationFinding],
) -> bool:
    return any(
        finding.severity in {"error", "critical"}
        for finding in findings
    )


def severity_counts(
    findings: list[ValidationFinding],
) -> dict[str, int]:
    counts = {
        "info": 0,
        "warning": 0,
        "error": 0,
        "critical": 0,
    }

    for finding in findings:
        counts[finding.severity] += 1

    return counts