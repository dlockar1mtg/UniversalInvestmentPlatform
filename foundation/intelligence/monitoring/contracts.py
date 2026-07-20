"""Immutable monitoring and reoptimization contracts for Phase 5.5."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Mapping


def _number(value: object, name: str, *, non_negative: bool = False) -> Decimal:
    converted = Decimal(str(value))
    if not converted.is_finite() or (non_negative and converted < 0):
        qualifier = "finite and non-negative" if non_negative else "finite"
        raise ValueError(f"{name} must be {qualifier}")
    return converted


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): _freeze(value[key]) for key in sorted(value, key=str)})
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _metric_map(values: Mapping[str, object], name: str) -> Mapping[str, Decimal]:
    if not values:
        raise ValueError(f"{name} must not be empty")
    return MappingProxyType({
        str(key): _number(values[key], f"{name}.{key}")
        for key in sorted(values, key=str)
    })


def _portable(value):
    if isinstance(value, Mapping):
        return {str(key): _portable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_portable(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, timedelta):
        return str(value.total_seconds())
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {name: _portable(getattr(value, name)) for name in value.__dataclass_fields__}
    return value


class MonitoringLifecycleStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ALERTS = "COMPLETED_WITH_ALERTS"
    FAILED = "FAILED"


class DriftCategory(str, Enum):
    MARKET = "MARKET"
    SCORE = "SCORE"
    CONFIDENCE = "CONFIDENCE"
    PORTFOLIO = "PORTFOLIO"
    LIQUIDITY = "LIQUIDITY"
    CAPACITY = "CAPACITY"
    POLICY = "POLICY"
    FRESHNESS = "FRESHNESS"
    EXECUTION = "EXECUTION"
    ALLOCATION = "ALLOCATION"


class DriftDirection(str, Enum):
    INCREASE = "INCREASE"
    DECREASE = "DECREASE"
    ABSOLUTE = "ABSOLUTE"


class TriggerSeverity(str, Enum):
    NONE = "NONE"
    WATCH = "WATCH"
    MATERIAL = "MATERIAL"
    CRITICAL = "CRITICAL"


class ReoptimizationDisposition(str, Enum):
    NO_ACTION = "NO_ACTION"
    CONTINUE_MONITORING = "CONTINUE_MONITORING"
    REOPTIMIZE = "REOPTIMIZE"
    ESCALATE = "ESCALATE"


@dataclass(frozen=True)
class MonitoringBaseline:
    baseline_id: str
    source_run_id: str
    source_output_fingerprint: str
    captured_at: datetime
    metrics: Mapping[str, object]
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("baseline_id", "source_run_id", "source_output_fingerprint"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} must not be blank")
        if self.captured_at.tzinfo is None:
            raise ValueError("captured_at must be timezone-aware")
        object.__setattr__(self, "metrics", _metric_map(self.metrics, "metrics"))
        object.__setattr__(self, "metadata", _freeze(self.metadata))


@dataclass(frozen=True)
class MonitoringObservation:
    observation_id: str
    observed_at: datetime
    metrics: Mapping[str, object]
    opportunity_id: str | None = None
    source_id: str = "SYSTEM"
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.observation_id.strip() or not self.source_id.strip():
            raise ValueError("observation_id and source_id must not be blank")
        if self.opportunity_id is not None and not self.opportunity_id.strip():
            raise ValueError("opportunity_id must not be blank when supplied")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        object.__setattr__(self, "metrics", _metric_map(self.metrics, "metrics"))
        object.__setattr__(self, "metadata", _freeze(self.metadata))


@dataclass(frozen=True)
class MonitoringWindow:
    window_id: str
    starts_at: datetime
    ends_at: datetime
    observations: tuple[MonitoringObservation, ...]

    def __post_init__(self) -> None:
        if not self.window_id.strip():
            raise ValueError("window_id must not be blank")
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("monitoring-window timestamps must be timezone-aware")
        if self.ends_at < self.starts_at:
            raise ValueError("ends_at must not precede starts_at")
        identifiers = [item.observation_id for item in self.observations]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("observation_id values must be unique within a window")
        if any(not self.starts_at <= item.observed_at <= self.ends_at for item in self.observations):
            raise ValueError("every observation must fall within the monitoring window")

    @property
    def duration(self) -> timedelta:
        return self.ends_at - self.starts_at


@dataclass(frozen=True)
class DriftThreshold:
    category: DriftCategory
    metric_name: str
    watch_delta: Decimal | float | int | str
    material_delta: Decimal | float | int | str
    critical_delta: Decimal | float | int | str
    direction: DriftDirection = DriftDirection.ABSOLUTE
    relative: bool = False

    def __post_init__(self) -> None:
        if not self.metric_name.strip():
            raise ValueError("metric_name must not be blank")
        watch = _number(self.watch_delta, "watch_delta", non_negative=True)
        material = _number(self.material_delta, "material_delta", non_negative=True)
        critical = _number(self.critical_delta, "critical_delta", non_negative=True)
        if watch > material or material > critical:
            raise ValueError("thresholds must satisfy watch <= material <= critical")
        object.__setattr__(self, "watch_delta", watch)
        object.__setattr__(self, "material_delta", material)
        object.__setattr__(self, "critical_delta", critical)

    @property
    def key(self) -> tuple[str, str]:
        return self.category.value, self.metric_name


@dataclass(frozen=True)
class MonitoringPolicyBundle:
    policy_version: str
    thresholds: tuple[DriftThreshold, ...]
    minimum_observations: int = 1
    cooldown: timedelta = timedelta(0)
    stale_after: timedelta = timedelta(days=1)
    hysteresis_rate: Decimal | float | int | str = Decimal("0")
    trigger_policy: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.policy_version.strip():
            raise ValueError("policy_version must not be blank")
        if not self.thresholds:
            raise ValueError("thresholds must not be empty")
        keys = [item.key for item in self.thresholds]
        if len(keys) != len(set(keys)):
            raise ValueError("category and metric_name threshold keys must be unique")
        if self.minimum_observations < 1:
            raise ValueError("minimum_observations must be positive")
        if self.cooldown < timedelta(0) or self.stale_after <= timedelta(0):
            raise ValueError("cooldown must be non-negative and stale_after must be positive")
        rate = _number(self.hysteresis_rate, "hysteresis_rate", non_negative=True)
        if rate > 1:
            raise ValueError("hysteresis_rate must be between 0 and 1")
        object.__setattr__(self, "hysteresis_rate", rate)
        object.__setattr__(self, "trigger_policy", _freeze(self.trigger_policy))

    @property
    def fingerprint(self) -> str:
        payload = {
            "policy_version": self.policy_version,
            "thresholds": sorted(self.thresholds, key=lambda item: item.key),
            "minimum_observations": self.minimum_observations,
            "cooldown": self.cooldown,
            "stale_after": self.stale_after,
            "hysteresis_rate": self.hysteresis_rate,
            "trigger_policy": self.trigger_policy,
        }
        encoded = json.dumps(_portable(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
        return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class DriftSignal:
    category: DriftCategory
    metric_name: str
    baseline_value: Decimal | float | int | str
    observed_value: Decimal | float | int | str
    delta: Decimal | float | int | str
    severity: TriggerSeverity
    opportunity_id: str | None = None
    reason_code: str = "DRIFT_DETECTED"

    def __post_init__(self) -> None:
        if not self.metric_name.strip() or not self.reason_code.strip():
            raise ValueError("metric_name and reason_code must not be blank")
        for name in ("baseline_value", "observed_value", "delta"):
            object.__setattr__(self, name, _number(getattr(self, name), name))


@dataclass(frozen=True)
class ReoptimizationTrigger:
    disposition: ReoptimizationDisposition
    severity: TriggerSeverity
    reason_codes: tuple[str, ...]
    eligible_at: datetime
    source_run_id: str

    def __post_init__(self) -> None:
        if not self.source_run_id.strip() or not self.reason_codes:
            raise ValueError("source_run_id and reason_codes are required")
        if self.eligible_at.tzinfo is None:
            raise ValueError("eligible_at must be timezone-aware")


@dataclass(frozen=True)
class MonitoringRunRequest:
    monitoring_run_id: str
    requested_at: datetime
    baseline: MonitoringBaseline
    window: MonitoringWindow
    policy: MonitoringPolicyBundle

    def __post_init__(self) -> None:
        if not self.monitoring_run_id.strip():
            raise ValueError("monitoring_run_id must not be blank")
        if self.requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")
        if self.window.starts_at < self.baseline.captured_at:
            raise ValueError("monitoring window must not start before the baseline")


@dataclass(frozen=True)
class MonitoringRunResult:
    monitoring_run_id: str
    status: MonitoringLifecycleStatus
    policy_fingerprint: str
    signals: tuple[DriftSignal, ...]
    trigger: ReoptimizationTrigger
    output_fingerprint: str | None = None

    def __post_init__(self) -> None:
        if not self.monitoring_run_id.strip() or not self.policy_fingerprint.strip():
            raise ValueError("monitoring_run_id and policy_fingerprint must not be blank")
        if self.status in {
            MonitoringLifecycleStatus.COMPLETED,
            MonitoringLifecycleStatus.COMPLETED_WITH_ALERTS,
        } and not self.output_fingerprint:
            raise ValueError("completed monitoring results require output_fingerprint")
