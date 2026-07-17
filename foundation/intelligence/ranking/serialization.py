"""Stable JSON, CSV, dashboard, and audit outputs for portfolio ranking."""

from __future__ import annotations

import csv
from decimal import Decimal
from enum import Enum
import io
import json
from typing import Mapping

from .orchestrator import PortfolioRankingBatchResult


RANKING_COLUMNS = (
    "batch_id",
    "batch_fingerprint",
    "rank",
    "opportunity_id",
    "priority_score",
    "priority_tier",
    "disposition",
    "reason_code",
    "competed_with",
    "headline",
    "summary",
    "portfolio_statement",
    "positive_drivers",
    "limiting_drivers",
)

AUDIT_COLUMNS = (
    "batch_id",
    "batch_fingerprint",
    "sequence",
    "opportunity_id",
    "stage",
    "evidence_json",
)


def _jsonable(value: object) -> object:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def ranking_dashboard_rows(
    result: PortfolioRankingBatchResult,
) -> tuple[dict[str, object], ...]:
    """Return one flat dashboard-ready record per ranked opportunity."""
    explanations = {item.opportunity_id: item for item in result.explanations}
    priority_tiers: dict[str, object] = {}
    for artifact in result.artifacts:
        if artifact.stage == "PRIORITY":
            priority_tiers[artifact.opportunity_id] = artifact.evidence.get("tier", "")

    rows: list[dict[str, object]] = []
    for outcome in result.outcomes:
        explanation = explanations[outcome.opportunity_id]
        rows.append(
            {
                "batch_id": result.batch_id,
                "batch_fingerprint": result.batch_fingerprint,
                "rank": outcome.rank,
                "opportunity_id": outcome.opportunity_id,
                "priority_score": str(outcome.priority_score),
                "priority_tier": priority_tiers.get(outcome.opportunity_id, ""),
                "disposition": outcome.disposition.value,
                "reason_code": outcome.reason_code.value,
                "competed_with": outcome.competed_with or "",
                "headline": explanation.headline,
                "summary": explanation.summary,
                "portfolio_statement": explanation.portfolio_statement,
                "positive_drivers": "|".join(
                    item.factor_name for item in explanation.positive_drivers
                ),
                "limiting_drivers": "|".join(
                    item.factor_name for item in explanation.limiting_drivers
                ),
            }
        )
    return tuple(rows)


def ranking_audit_rows(
    result: PortfolioRankingBatchResult,
) -> tuple[dict[str, object], ...]:
    """Return one record per ordered intermediate artifact."""
    return tuple(
        {
            "batch_id": result.batch_id,
            "batch_fingerprint": result.batch_fingerprint,
            "sequence": artifact.sequence,
            "opportunity_id": artifact.opportunity_id,
            "stage": artifact.stage,
            "evidence_json": json.dumps(
                _jsonable(artifact.evidence), sort_keys=True, separators=(",", ":")
            ),
        }
        for artifact in result.artifacts
    )


def _csv_text(rows: tuple[dict[str, object], ...], columns: tuple[str, ...]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def ranking_dashboard_csv(result: PortfolioRankingBatchResult) -> str:
    return _csv_text(ranking_dashboard_rows(result), RANKING_COLUMNS)


def ranking_audit_csv(result: PortfolioRankingBatchResult) -> str:
    return _csv_text(ranking_audit_rows(result), AUDIT_COLUMNS)


def ranking_batch_dict(result: PortfolioRankingBatchResult) -> dict[str, object]:
    explanations = {item.opportunity_id: item for item in result.explanations}
    return {
        "schema_version": "5.2.9",
        "batch_id": result.batch_id,
        "batch_fingerprint": result.batch_fingerprint,
        "ranking": [
            {
                "rank": outcome.rank,
                "opportunity_id": outcome.opportunity_id,
                "priority_score": str(outcome.priority_score),
                "disposition": outcome.disposition.value,
                "reason_code": outcome.reason_code.value,
                "competed_with": outcome.competed_with,
                "explanation": {
                    "headline": explanations[outcome.opportunity_id].headline,
                    "summary": explanations[outcome.opportunity_id].summary,
                    "portfolio_statement": explanations[outcome.opportunity_id].portfolio_statement,
                    "positive_drivers": [
                        {
                            "factor_name": driver.factor_name,
                            "factor_value": str(driver.factor_value),
                            "direction": driver.direction,
                            "statement": driver.statement,
                        }
                        for driver in explanations[outcome.opportunity_id].positive_drivers
                    ],
                    "limiting_drivers": [
                        {
                            "factor_name": driver.factor_name,
                            "factor_value": str(driver.factor_value),
                            "direction": driver.direction,
                            "statement": driver.statement,
                        }
                        for driver in explanations[outcome.opportunity_id].limiting_drivers
                    ],
                    "audit_evidence": _jsonable(
                        explanations[outcome.opportunity_id].audit_evidence
                    ),
                },
            }
            for outcome in result.outcomes
        ],
        "audit_records": list(ranking_audit_rows(result)),
    }


def ranking_batch_json(result: PortfolioRankingBatchResult, *, indent: int | None = 2) -> str:
    """Serialize the complete batch using deterministic key ordering."""
    return json.dumps(
        ranking_batch_dict(result),
        sort_keys=True,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )
