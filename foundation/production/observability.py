"""Structured events, deterministic metrics, health, and secured API gateway."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import MappingProxyType
from typing import Callable, Mapping

from .api import APIResponse, ProductionAPI
from .security import APIKeyAuthenticator, Permission, redact


@dataclass(frozen=True)
class OperationalEvent:
    event_type: str
    occurred_at: datetime
    correlation_id: str
    fields: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.event_type.strip() or not self.correlation_id.strip() or self.occurred_at.tzinfo is None:
            raise ValueError("event type, correlation identity, and aware timestamp are required")
        object.__setattr__(self, "fields", redact(self.fields))


class EventRecorder:
    def __init__(self):
        self._events: list[OperationalEvent] = []

    def record(self, event: OperationalEvent) -> None:
        self._events.append(event)

    @property
    def events(self) -> tuple[OperationalEvent, ...]:
        return tuple(self._events)


class MetricRegistry:
    def __init__(self):
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], int] = {}
        self._durations: dict[tuple[str, tuple[tuple[str, str], ...]], list[Decimal]] = {}

    @staticmethod
    def _key(name: str, labels: Mapping[str, str]):
        if not name.strip():
            raise ValueError("metric name must not be blank")
        return name, tuple(sorted((str(key), str(value)) for key, value in labels.items()))

    def increment(self, name: str, labels: Mapping[str, str] = MappingProxyType({})) -> None:
        key = self._key(name, labels)
        self._counters[key] = self._counters.get(key, 0) + 1

    def observe_duration(self, name: str, seconds: object, labels: Mapping[str, str] = MappingProxyType({})) -> None:
        value = Decimal(str(seconds))
        if not value.is_finite() or value < 0:
            raise ValueError("duration must be finite and non-negative")
        self._durations.setdefault(self._key(name, labels), []).append(value)

    def snapshot(self) -> Mapping[str, object]:
        counters = [{"name": key[0], "labels": dict(key[1]), "value": value} for key, value in sorted(self._counters.items())]
        durations = [{
            "name": key[0], "labels": dict(key[1]), "count": len(values),
            "total_seconds": str(sum(values, Decimal(0))), "maximum_seconds": str(max(values)),
        } for key, values in sorted(self._durations.items())]
        return MappingProxyType({"counters": tuple(counters), "durations": tuple(durations)})


@dataclass(frozen=True)
class HealthReport:
    live: bool
    ready: bool
    checks: Mapping[str, bool]


def evaluate_health(checks: Mapping[str, Callable[[], bool]]) -> HealthReport:
    results = {}
    for name in sorted(checks):
        try:
            results[name] = bool(checks[name]())
        except Exception:
            results[name] = False
    return HealthReport(True, all(results.values()) and bool(results), MappingProxyType(results))


class SecuredProductionGateway:
    def __init__(self, api: ProductionAPI, authenticator: APIKeyAuthenticator, events: EventRecorder, metrics: MetricRegistry):
        self.api, self.authenticator, self.events, self.metrics = api, authenticator, events, metrics

    def handle(self, method: str, path: str, body=None, *, credential: str | None = None, correlation_id: str) -> APIResponse:
        principal = self.authenticator.authenticate(credential)
        permission = Permission.RUN_SUBMIT if method.upper() == "POST" else Permission.RUN_READ
        if principal is None:
            response = APIResponse(401, {"error": {"code": "UNAUTHENTICATED", "message": "valid credentials are required"}})
        elif not principal.permits(permission):
            response = APIResponse(403, {"error": {"code": "FORBIDDEN", "message": "permission is required"}})
        else:
            response = self.api.handle(method, path, body)
        labels = {"method": method.upper(), "status": str(response.status_code)}
        self.metrics.increment("production_api_requests_total", labels)
        self.events.record(OperationalEvent(
            "PRODUCTION_API_REQUEST", datetime.now(timezone.utc), correlation_id,
            {"method": method.upper(), "path": path, "status": response.status_code,
             "principal_id": principal.principal_id if principal else "ANONYMOUS", "credential": credential},
        ))
        return response
