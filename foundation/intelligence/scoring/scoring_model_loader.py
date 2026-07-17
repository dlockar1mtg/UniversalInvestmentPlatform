"""YAML loader for scoring model registry definitions."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Mapping

from .scoring_model import ScoringModelDefinition, ScoringModelStatus
from .scoring_model_registry import ScoringModelRegistry


def _parse_date(value: Any, field_name: str) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be an ISO date string.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from exc


def model_from_mapping(data: Mapping[str, Any]) -> ScoringModelDefinition:
    """Create a scoring model definition from parsed configuration."""
    required = {
        "model_id",
        "asset_class",
        "version",
        "scoring_profile_id",
        "normalization_profile_id",
        "status",
        "effective_from",
    }
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"Missing scoring model fields: {', '.join(missing)}.")

    effective_to = data.get("effective_to")
    return ScoringModelDefinition(
        model_id=data["model_id"],
        asset_class=data["asset_class"],
        version=str(data["version"]),
        scoring_profile_id=data["scoring_profile_id"],
        normalization_profile_id=data["normalization_profile_id"],
        status=ScoringModelStatus(data["status"]),
        effective_from=_parse_date(data["effective_from"], "effective_from"),
        effective_to=(
            _parse_date(effective_to, "effective_to")
            if effective_to is not None
            else None
        ),
        description=data.get("description", ""),
        metadata=data.get("metadata", {}),
    )


def load_registry_from_yaml(path: str | Path) -> ScoringModelRegistry:
    """Load and validate a scoring model registry YAML file."""
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to load scoring model registry configuration."
        ) from exc

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(config_path)

    parsed = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise ValueError("Registry YAML root must be a mapping.")

    model_rows = parsed.get("models")
    if not isinstance(model_rows, list):
        raise ValueError("Registry YAML must contain a models list.")

    registry = ScoringModelRegistry(
        model_from_mapping(row)
        for row in model_rows
    )
    errors = registry.validate()
    if errors:
        raise ValueError("Invalid scoring model registry: " + " | ".join(errors))
    return registry
