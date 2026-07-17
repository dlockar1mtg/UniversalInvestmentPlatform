"""Serialize score explanations for APIs, logs, and persistence."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from .explanation import ScoreExplanation


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "value"):
        return value.value
    raise TypeError(f"Unsupported JSON type: {type(value).__name__}")


def explanation_to_dict(explanation: ScoreExplanation) -> dict[str, Any]:
    """Convert an explanation to a JSON-safe dictionary."""
    return {
        "asset_id": explanation.asset_id,
        "model_id": explanation.model_id,
        "model_version": explanation.model_version,
        "final_score": str(explanation.final_score),
        "score_band": explanation.score_band,
        "headline": explanation.headline,
        "summary": explanation.summary,
        "positive_drivers": list(explanation.positive_drivers),
        "negative_drivers": list(explanation.negative_drivers),
        "contributions": [
            {
                "dimension": item.dimension.value,
                "dimension_score": str(item.dimension_score),
                "normalized_weight": str(item.normalized_weight),
                "weighted_contribution": str(item.weighted_contribution),
                "rank": item.rank,
                "direction": item.direction,
            }
            for item in explanation.contributions
        ],
        "adjustments": [
            {
                "name": item.name,
                "input_score": str(item.input_score),
                "multiplier": str(item.multiplier),
                "output_score": str(item.output_score),
                "impact_points": str(item.impact_points),
                "explanation": item.explanation,
            }
            for item in explanation.adjustments
        ],
        "missing_data_impacts": [
            {
                "dimension": item.dimension.value,
                "coverage_ratio": str(item.coverage_ratio),
                "omitted_from_score": item.omitted_from_score,
                "message": item.message,
            }
            for item in explanation.missing_data_impacts
        ],
        "warnings": list(explanation.warnings),
        "audit_record": dict(explanation.audit_record),
    }


def explanation_to_json(
    explanation: ScoreExplanation,
    *,
    indent: int = 2,
) -> str:
    """Serialize an explanation to stable JSON."""
    return json.dumps(
        explanation_to_dict(explanation),
        indent=indent,
        sort_keys=True,
        default=_json_default,
    )


def write_explanation_json(
    explanation: ScoreExplanation,
    path: str | Path,
) -> Path:
    """Write an explanation audit artifact to disk."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        explanation_to_json(explanation) + "\n",
        encoding="utf-8",
    )
    return output_path
