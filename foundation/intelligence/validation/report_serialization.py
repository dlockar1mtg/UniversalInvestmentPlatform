"""JSON and CSV serialization for validation reports."""

from __future__ import annotations

import csv
import json
from dataclasses import fields, is_dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from .validation_reporting import ExecutiveValidationReport


def _convert(value: Any) -> Any:
    """Recursively convert immutable validation records to JSON-safe values."""
    if isinstance(value, Decimal):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _convert(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(key): _convert(item)
            for key, item in value.items()
        }
    if isinstance(value, (tuple, list)):
        return [_convert(item) for item in value]
    if isinstance(value, set):
        return sorted(_convert(item) for item in value)
    if hasattr(value, "value"):
        return _convert(value.value)
    return value


def executive_report_to_dict(
    report: ExecutiveValidationReport,
) -> dict[str, Any]:
    payload = _convert(report)
    if not isinstance(payload, dict):
        raise TypeError("Executive report serialization must produce a dictionary.")
    return payload


def executive_report_to_json(
    report: ExecutiveValidationReport,
    *,
    indent: int = 2,
) -> str:
    return json.dumps(
        executive_report_to_dict(report),
        indent=indent,
        sort_keys=True,
    )


def write_executive_report_json(
    report: ExecutiveValidationReport,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        executive_report_to_json(report) + "\n",
        encoding="utf-8",
    )
    return output_path


def write_scorecards_csv(
    report: ExecutiveValidationReport,
    path: str | Path,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "asset_class",
        "model_id",
        "model_version",
        "horizon_days",
        "certification_status",
        "validation_grade",
        "validation_score",
        "rank",
        "headline",
        "key_strengths",
        "key_risks",
        "warnings",
    ]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for scorecard in report.scorecards:
            writer.writerow(
                {
                    "asset_class": scorecard.asset_class,
                    "model_id": scorecard.model_id,
                    "model_version": scorecard.model_version,
                    "horizon_days": scorecard.horizon_days,
                    "certification_status": scorecard.certification_status,
                    "validation_grade": scorecard.validation_grade,
                    "validation_score": str(scorecard.validation_score),
                    "rank": scorecard.rank,
                    "headline": scorecard.headline,
                    "key_strengths": " | ".join(scorecard.key_strengths),
                    "key_risks": " | ".join(scorecard.key_risks),
                    "warnings": " | ".join(scorecard.warnings),
                }
            )
    return output_path
