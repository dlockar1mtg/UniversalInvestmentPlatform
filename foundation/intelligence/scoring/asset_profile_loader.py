"""Load asset-class scoring profiles from YAML configuration."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from .asset_profile import AssetClassScoringProfile, MetricNormalizationRule
from .score_dimension import ScoreDimension
from .scoring_profile import ScoringProfile


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping.")
    return value


def asset_profile_from_mapping(data: Mapping[str, Any]) -> AssetClassScoringProfile:
    required = {
        "model_id",
        "profile_id",
        "asset_class",
        "version",
        "normalization_profile_id",
        "dimension_weights",
        "minimum_coverage",
        "confidence_floor",
        "maximum_risk_penalty",
        "metrics",
    }
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"Missing asset profile fields: {', '.join(missing)}.")

    dimension_weights = {
        ScoreDimension(name): Decimal(str(weight))
        for name, weight in _require_mapping(
            data["dimension_weights"],
            "dimension_weights",
        ).items()
    }

    scoring_profile = ScoringProfile(
        profile_id=data["profile_id"],
        asset_class=data["asset_class"],
        version=str(data["version"]),
        dimension_weights=dimension_weights,
        minimum_coverage=Decimal(str(data["minimum_coverage"])),
        confidence_floor=Decimal(str(data["confidence_floor"])),
        maximum_risk_penalty=Decimal(str(data["maximum_risk_penalty"])),
        status=data.get("status", "active"),
    )

    metrics = data["metrics"]
    if not isinstance(metrics, list):
        raise TypeError("metrics must be a list.")

    rules = tuple(
        MetricNormalizationRule(
            metric_name=row["metric_name"],
            dimension=ScoreDimension(row["dimension"]),
            strategy=row["strategy"],
            weight=Decimal(str(row["weight"])),
            confidence=Decimal(str(row.get("confidence", 1))),
            parameters=row.get("parameters", {}),
            source_field=row.get("source_field"),
            description=row.get("description", ""),
        )
        for row in metrics
    )

    return AssetClassScoringProfile(
        model_id=data["model_id"],
        scoring_profile=scoring_profile,
        normalization_profile_id=data["normalization_profile_id"],
        metric_rules=rules,
        description=data.get("description", ""),
    )


def load_asset_profile(path: str | Path) -> AssetClassScoringProfile:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load asset scoring profiles.") from exc

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(config_path)

    parsed = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise ValueError("Asset profile YAML root must be a mapping.")
    return asset_profile_from_mapping(parsed)


def load_asset_profiles(directory: str | Path) -> dict[str, AssetClassScoringProfile]:
    profile_directory = Path(directory)
    if not profile_directory.exists():
        raise FileNotFoundError(profile_directory)

    profiles: dict[str, AssetClassScoringProfile] = {}
    for path in sorted(profile_directory.glob("*.yaml")):
        profile = load_asset_profile(path)
        if profile.asset_class in profiles:
            raise ValueError(
                f"Duplicate asset-class profile: {profile.asset_class}."
            )
        profiles[profile.asset_class] = profile
    if not profiles:
        raise ValueError("No asset-class profile YAML files were found.")
    return profiles
