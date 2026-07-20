"""Read-only, secret-safe operational dashboard projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Mapping

from .observability import EventRecorder, MetricRegistry


@dataclass(frozen=True)
class DashboardSettings:
    portfolio_path: Path = Path("portfolio_holdings.csv")
    alpha_vantage_configured: bool = False
    fred_configured: bool = False

    @classmethod
    def from_environment(cls, values: Mapping[str, str] = os.environ) -> "DashboardSettings":
        return cls(
            Path(values.get("UIIP_PORTFOLIO_CSV", "portfolio_holdings.csv")),
            bool(values.get("UIIP_ALPHA_VANTAGE_API_KEY", "").strip()),
            bool(values.get("UIIP_FRED_API_KEY", "").strip()),
        )


class DashboardService:
    def __init__(self, repository, events: EventRecorder, metrics: MetricRegistry, settings: DashboardSettings):
        self.repository, self.events, self.metrics, self.settings = repository, events, metrics, settings

    def summary(self) -> dict[str, object]:
        ready = self.repository.readiness() if hasattr(self.repository, "readiness") else True
        snapshot = self.metrics.snapshot()
        request_count = sum(
            int(item["value"]) for item in snapshot["counters"]
            if item["name"] == "production_api_requests_total"
        )
        latest = self.events.events[-1].occurred_at.isoformat() if self.events.events else None
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "service": {"live": True, "ready": bool(ready)},
            "integrations": {
                "alpha_vantage": self.settings.alpha_vantage_configured,
                "fred": self.settings.fred_configured,
                "portfolio_csv": self.settings.portfolio_path.is_file(),
            },
            "activity": {
                "api_requests": request_count,
                "recorded_events": len(self.events.events),
                "latest_event_at": latest,
            },
        }

    def event_documents(self, limit: int = 50) -> tuple[dict[str, object], ...]:
        bounded = max(1, min(int(limit), 200))
        selected = reversed(self.events.events[-bounded:])
        return tuple({
            "event_type": event.event_type,
            "occurred_at": event.occurred_at.isoformat(),
            "correlation_id": event.correlation_id,
            "fields": dict(event.fields),
        } for event in selected)

    def metric_document(self) -> dict[str, object]:
        snapshot = self.metrics.snapshot()
        return {"counters": list(snapshot["counters"]), "durations": list(snapshot["durations"])}
