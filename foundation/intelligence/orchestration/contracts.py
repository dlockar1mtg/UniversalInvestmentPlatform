"""Immutable contracts and policy fingerprints for Phase 5.4."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping


def _decimal(value, name: str) -> Decimal:
    converted = Decimal(str(value))
    if not converted.is_finite() or converted < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return converted


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(value[key]) for key in sorted(value, key=str)})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _portable(value):
    if isinstance(value, Mapping):
        return {str(key): _portable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_portable(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    return value


class OrchestrationRunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_QUARANTINE = "COMPLETED_WITH_QUARANTINE"
    FAILED = "FAILED"


class OrchestrationStage(str, Enum):
    DECISION = "DECISION"
    RANKING = "RANKING"
    CAPITAL_SUPPLY = "CAPITAL_SUPPLY"
    SIZING = "SIZING"
    CONSTRAINTS = "CONSTRAINTS"
    OBJECTIVES = "OBJECTIVES"
    OPTIMIZATION = "OPTIMIZATION"
    EXECUTION = "EXECUTION"
    EXPLANATION = "EXPLANATION"
    SERIALIZATION = "SERIALIZATION"


class StageStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class FailureScope(str, Enum):
    OPPORTUNITY = "OPPORTUNITY"
    BATCH = "BATCH"


@dataclass(frozen=True)
class PortfolioPositionSnapshot:
    opportunity_id: str
    asset_class: str
    group_key: str
    market_value: Decimal | float | int | str
    quantity: Decimal | float | int | str = Decimal("0")
    currency: str = "USD"

    def __post_init__(self) -> None:
        for name in ("opportunity_id", "asset_class", "group_key", "currency"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        object.__setattr__(self, "market_value", _decimal(self.market_value, "market_value"))
        object.__setattr__(self, "quantity", _decimal(self.quantity, "quantity"))


@dataclass(frozen=True)
class PortfolioSnapshot:
    snapshot_id: str
    as_of: datetime
    positions: tuple[PortfolioPositionSnapshot, ...]
    currency: str = "USD"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.snapshot_id.strip() or not self.currency.strip():
            raise ValueError("snapshot_id and currency must not be blank")
        if self.as_of.tzinfo is None:
            raise ValueError("as_of must be timezone-aware")
        ids = [position.opportunity_id for position in self.positions]
        if len(ids) != len(set(ids)):
            raise ValueError("portfolio position opportunity_id values must be unique")
        if any(position.currency != self.currency for position in self.positions):
            raise ValueError("position currencies must match snapshot currency")
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    @property
    def total_market_value(self) -> Decimal:
        return sum((position.market_value for position in self.positions), Decimal("0"))


@dataclass(frozen=True)
class CapitalInput:
    gross_capital: Decimal | float | int | str
    required_reserve: Decimal | float | int | str = Decimal("0")
    unavailable_capital: Decimal | float | int | str = Decimal("0")
    currency: str = "USD"

    def __post_init__(self) -> None:
        for name in ("gross_capital", "required_reserve", "unavailable_capital"):
            object.__setattr__(self, name, _decimal(getattr(self, name), name))
        if self.required_reserve + self.unavailable_capital > self.gross_capital:
            raise ValueError("protected capital must not exceed gross_capital")
        if not self.currency.strip():
            raise ValueError("currency must not be blank")

    @property
    def initially_deployable_capital(self) -> Decimal:
        return self.gross_capital - self.required_reserve - self.unavailable_capital


@dataclass(frozen=True)
class OrchestrationOpportunity:
    opportunity_id: str
    decision_id: str
    asset_class: str
    group_key: str
    currency: str = "USD"
    source_payload: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("opportunity_id", "decision_id", "asset_class", "group_key", "currency"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        object.__setattr__(self, "source_payload", _freeze(self.source_payload))


@dataclass(frozen=True)
class OrchestrationPolicyBundle:
    policy_version: str
    decision_policy: Mapping[str, object] = field(default_factory=dict)
    ranking_policy: Mapping[str, object] = field(default_factory=dict)
    allocation_policy: Mapping[str, object] = field(default_factory=dict)
    execution_policy: Mapping[str, object] = field(default_factory=dict)
    failure_policy: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version must not be blank")
        for name in (
            "decision_policy", "ranking_policy", "allocation_policy",
            "execution_policy", "failure_policy",
        ):
            object.__setattr__(self, name, _freeze(getattr(self, name)))

    @property
    def fingerprint(self) -> str:
        payload = {
            "policy_version": self.policy_version,
            "decision_policy": _portable(self.decision_policy),
            "ranking_policy": _portable(self.ranking_policy),
            "allocation_policy": _portable(self.allocation_policy),
            "execution_policy": _portable(self.execution_policy),
            "failure_policy": _portable(self.failure_policy),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class UniversalRunRequest:
    run_id: str
    requested_at: datetime
    source_decision_batch_id: str
    portfolio: PortfolioSnapshot
    capital: CapitalInput
    opportunities: tuple[OrchestrationOpportunity, ...]
    policies: OrchestrationPolicyBundle

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.source_decision_batch_id.strip():
            raise ValueError("run_id and source_decision_batch_id must not be blank")
        if self.requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")
        if not self.opportunities:
            raise ValueError("orchestration run requires at least one opportunity")
        ids = [item.opportunity_id for item in self.opportunities]
        decisions = [item.decision_id for item in self.opportunities]
        if len(ids) != len(set(ids)) or len(decisions) != len(set(decisions)):
            raise ValueError("opportunity_id and decision_id values must be unique")
        if self.portfolio.currency != self.capital.currency or any(
            item.currency != self.capital.currency for item in self.opportunities
        ):
            raise ValueError("portfolio, capital, and opportunity currencies must match")


@dataclass(frozen=True)
class StageRecord:
    stage: OrchestrationStage
    status: StageStatus
    started_at: datetime
    completed_at: datetime | None = None
    processed_count: int = 0
    failed_count: int = 0
    evidence: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.started_at.tzinfo is None or (
            self.completed_at is not None and self.completed_at.tzinfo is None
        ):
            raise ValueError("stage timestamps must be timezone-aware")
        if self.completed_at is not None and self.completed_at < self.started_at:
            raise ValueError("completed_at must not precede started_at")
        if self.processed_count < 0 or self.failed_count < 0:
            raise ValueError("stage counts must be non-negative")
        if self.failed_count > self.processed_count:
            raise ValueError("failed_count must not exceed processed_count")
        object.__setattr__(self, "evidence", _freeze(self.evidence))


@dataclass(frozen=True)
class QuarantinedOpportunity:
    opportunity_id: str
    stage: OrchestrationStage
    reason_code: str
    message: str
    failure_scope: FailureScope = FailureScope.OPPORTUNITY

    def __post_init__(self) -> None:
        for name in ("opportunity_id", "reason_code", "message"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")


@dataclass(frozen=True)
class UniversalOrchestrationResult:
    run_id: str
    status: OrchestrationRunStatus
    policy_fingerprint: str
    stage_records: tuple[StageRecord, ...]
    successful_opportunity_ids: tuple[str, ...]
    quarantined: tuple[QuarantinedOpportunity, ...] = ()
    output_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.policy_fingerprint.strip():
            raise ValueError("run_id and policy_fingerprint must not be blank")
        success = set(self.successful_opportunity_ids)
        quarantine = {item.opportunity_id for item in self.quarantined}
        if len(success) != len(self.successful_opportunity_ids):
            raise ValueError("successful_opportunity_ids must be unique")
        if success & quarantine:
            raise ValueError("an opportunity cannot be both successful and quarantined")
        if self.status is OrchestrationRunStatus.COMPLETED and self.quarantined:
            raise ValueError("COMPLETED result must not contain quarantined opportunities")
        if self.status is OrchestrationRunStatus.COMPLETED_WITH_QUARANTINE and not self.quarantined:
            raise ValueError("COMPLETED_WITH_QUARANTINE requires quarantine evidence")
        if self.status in {
            OrchestrationRunStatus.COMPLETED,
            OrchestrationRunStatus.COMPLETED_WITH_QUARANTINE,
        } and not self.output_fingerprint:
            raise ValueError("completed result requires output_fingerprint")
