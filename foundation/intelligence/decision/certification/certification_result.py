from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

@dataclass(frozen=True, slots=True)
class CertificationResult:
    """Result returned by every certification validator."""

    validator_name: str
    passed: bool
    duration_seconds: float
    timestamp: datetime
    metadata: Mapping[str, object] = field(default_factory=dict)
    message: str = ""

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("Certification timestamps must be timezone-aware.")
        if self.duration_seconds < 0:
            raise ValueError("Certification duration cannot be negative.")
