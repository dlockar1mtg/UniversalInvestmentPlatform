"""Statuses produced by portfolio constraint evaluation."""

from enum import StrEnum


class ConstraintStatus(StrEnum):
    """Severity of an individual portfolio or policy constraint."""

    PASSED = "passed"
    WARNING = "warning"
    BLOCKED = "blocked"
