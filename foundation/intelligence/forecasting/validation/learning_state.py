"""Learning-state serialization and deterministic persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .learning_contracts import (
    LearningState,
    ModelLearningSnapshot,
    ModelLearningStatus,
)


def learning_state_to_dict(state: LearningState) -> dict[str, Any]:
    """Convert learning state to a JSON-safe mapping."""

    return {
        "schema_version": state.schema_version,
        "generated_at": state.generated_at.isoformat(),
        "snapshots": [
            {
                "model_key": item.model_key,
                "reputation": item.reputation,
                "adaptive_weight": item.adaptive_weight,
                "status": item.status.value,
                "sample_size": item.sample_size,
                "updated_at": item.updated_at.isoformat(),
                "update_count": item.update_count,
                "metadata": dict(item.metadata),
            }
            for item in sorted(
                state.snapshots,
                key=lambda value: value.model_key,
            )
        ],
    }


def learning_state_to_json(state: LearningState) -> str:
    """Serialize learning state deterministically."""

    return json.dumps(
        learning_state_to_dict(state),
        sort_keys=True,
        separators=(",", ":"),
    )


def learning_state_from_dict(
    payload: dict[str, Any],
) -> LearningState:
    """Rehydrate a learning state from a mapping."""

    snapshots = tuple(
        ModelLearningSnapshot(
            model_key=item["model_key"],
            reputation=float(item["reputation"]),
            adaptive_weight=float(item["adaptive_weight"]),
            status=ModelLearningStatus(item["status"]),
            sample_size=int(item["sample_size"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            update_count=int(item["update_count"]),
            metadata=item.get("metadata", {}),
        )
        for item in payload.get("snapshots", [])
    )
    return LearningState(
        snapshots=snapshots,
        generated_at=datetime.fromisoformat(payload["generated_at"]),
        schema_version=str(payload.get("schema_version", "1.0.0")),
    )


def save_learning_state(
    state: LearningState,
    path: str | Path,
) -> None:
    """Persist state atomically using a temporary file."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        learning_state_to_json(state),
        encoding="utf-8",
    )
    temporary.replace(destination)


def load_learning_state(path: str | Path) -> LearningState:
    """Load state from disk."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return learning_state_from_dict(payload)
