"""Immutable production runtime and persistence contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping


def _freeze(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): values[key] for key in sorted(values, key=str)})


class ProductionRunStatus(str, Enum):
    REGISTERED = "REGISTERED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ProductionRun:
    run_id: str
    source_phase: str
    request_fingerprint: str
    policy_fingerprint: str
    created_at: datetime
    status: ProductionRunStatus = ProductionRunStatus.REGISTERED
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not all((self.run_id.strip(), self.source_phase.strip(), self.request_fingerprint.strip(), self.policy_fingerprint.strip())):
            raise ValueError("run identity, phase, request, and policy fingerprints are required")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        object.__setattr__(self, "metadata", _freeze(self.metadata))


@dataclass(frozen=True)
class PersistedArtifact:
    artifact_id: str
    run_id: str
    artifact_type: str
    payload: bytes
    created_at: datetime
    content_fingerprint: str = ""

    def __post_init__(self) -> None:
        if not all((self.artifact_id.strip(), self.run_id.strip(), self.artifact_type.strip())):
            raise ValueError("artifact identity, run identity, and type are required")
        if self.created_at.tzinfo is None or not self.payload:
            raise ValueError("artifact timestamp must be aware and payload must not be empty")
        fingerprint = sha256(self.payload).hexdigest()
        if self.content_fingerprint and self.content_fingerprint != fingerprint:
            raise ValueError("artifact content fingerprint mismatch")
        object.__setattr__(self, "content_fingerprint", fingerprint)


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    run_id: str
    sequence: int
    event_type: str
    occurred_at: datetime
    evidence: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not all((self.event_id.strip(), self.run_id.strip(), self.event_type.strip())) or self.sequence < 1:
            raise ValueError("audit identity, run identity, positive sequence, and type are required")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        object.__setattr__(self, "evidence", _freeze(self.evidence))


def canonical_json(values: Mapping[str, object]) -> str:
    return json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
