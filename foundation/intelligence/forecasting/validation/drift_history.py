"""Drift-history serialization and persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .drift_contracts import (
    DriftHistory,
    DriftHistoryEntry,
    DriftRecommendation,
    DriftSeverity,
)


def drift_history_to_dict(history: DriftHistory) -> dict[str, Any]:
    """Convert drift history into a JSON-safe mapping."""

    return {
        "schema_version": history.schema_version,
        "generated_at": history.generated_at.isoformat(),
        "entries": [
            {
                "model_key": item.model_key,
                "evaluated_at": item.evaluated_at.isoformat(),
                "drift_score": item.drift_score,
                "severity": item.severity.value,
                "recommendation": item.recommendation.value,
                "baseline_regime": item.baseline_regime,
                "current_regime": item.current_regime,
                "metrics": dict(item.metrics),
            }
            for item in sorted(
                history.entries,
                key=lambda value: (
                    value.evaluated_at,
                    value.model_key,
                ),
            )
        ],
    }


def drift_history_to_json(history: DriftHistory) -> str:
    """Serialize drift history deterministically."""

    return json.dumps(
        drift_history_to_dict(history),
        sort_keys=True,
        separators=(",", ":"),
    )


def drift_history_from_dict(
    payload: dict[str, Any],
) -> DriftHistory:
    """Rehydrate drift history from a mapping."""

    entries = tuple(
        DriftHistoryEntry(
            model_key=item["model_key"],
            evaluated_at=datetime.fromisoformat(
                item["evaluated_at"]
            ),
            drift_score=float(item["drift_score"]),
            severity=DriftSeverity(item["severity"]),
            recommendation=DriftRecommendation(
                item["recommendation"]
            ),
            baseline_regime=item["baseline_regime"],
            current_regime=item["current_regime"],
            metrics=item.get("metrics", {}),
        )
        for item in payload.get("entries", [])
    )
    return DriftHistory(
        entries=entries,
        generated_at=datetime.fromisoformat(payload["generated_at"]),
        schema_version=str(payload.get("schema_version", "1.0.0")),
    )


def save_drift_history(
    history: DriftHistory,
    path: str | Path,
) -> None:
    """Persist drift history atomically."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        drift_history_to_json(history),
        encoding="utf-8",
    )
    temporary.replace(destination)


def load_drift_history(path: str | Path) -> DriftHistory:
    """Load drift history from disk."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return drift_history_from_dict(payload)
