"""Unified explanations and deterministic outputs for orchestration runs."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import io
import json
from types import MappingProxyType
from typing import Mapping

from .orchestrator import EndToEndOrchestrationResult


DASHBOARD_COLUMNS = (
    "run_id", "run_status", "opportunity_id", "rank", "priority_score",
    "ranking_disposition", "ranking_reason", "allocated_amount", "allocation_status",
    "execution_amount", "quarantine_stage", "quarantine_reason", "headline", "summary",
)

AUDIT_COLUMNS = (
    "run_id", "sequence", "opportunity_id", "stage", "status", "evidence_json",
)


def _jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _jsonable(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _freeze(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): values[key] for key in sorted(values, key=str)})


def _fingerprint(value: object) -> str:
    encoded = json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _csv(rows: tuple[Mapping[str, object], ...], columns: tuple[str, ...]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


@dataclass(frozen=True)
class UnifiedOpportunityExplanation:
    opportunity_id: str
    headline: str
    summary: str
    ranking_statement: str
    allocation_statement: str
    execution_statement: str
    quarantine_statement: str
    evidence: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.opportunity_id.strip() or not self.headline.strip():
            raise ValueError("explanation identifiers and headline must not be blank")
        object.__setattr__(self, "evidence", _freeze(self.evidence))


@dataclass(frozen=True)
class UnifiedOutputPackage:
    run_id: str
    run_status: str
    orchestration_fingerprint: str | None
    package_fingerprint: str
    explanations: tuple[UnifiedOpportunityExplanation, ...]
    dashboard_rows: tuple[Mapping[str, object], ...]
    audit_rows: tuple[Mapping[str, object], ...]
    json_text: str
    dashboard_csv: str
    audit_csv: str


def build_unified_output(
    result: EndToEndOrchestrationResult,
    *,
    indent: int | None = 2,
) -> UnifiedOutputPackage:
    """Build one stable operator and machine output without recalculation."""
    run = result.run
    ranking_outcomes = {
        item.opportunity_id: item for item in (result.ranking.outcomes if result.ranking else ())
    }
    ranking_explanations = {
        item.opportunity_id: item for item in (result.ranking.explanations if result.ranking else ())
    }
    allocation_lines = {
        item.opportunity_id: item
        for item in (
            result.optimization.capital_result.lines if result.optimization else ()
        )
    }
    objective_results = {item.opportunity_id: item for item in result.objective_results}
    quarantine = {item.opportunity_id: item for item in run.quarantined}
    execution_amounts: dict[str, Decimal] = {}
    if result.execution_plan:
        for instruction in result.execution_plan.instructions:
            if instruction.opportunity_id and instruction.action.value == "PURCHASE":
                execution_amounts[instruction.opportunity_id] = (
                    execution_amounts.get(instruction.opportunity_id, Decimal("0"))
                    + instruction.amount
                )

    identifiers = sorted(set(ranking_outcomes) | set(allocation_lines) | set(quarantine))
    explanations: list[UnifiedOpportunityExplanation] = []
    dashboard: list[Mapping[str, object]] = []
    for opportunity_id in identifiers:
        ranked = ranking_outcomes.get(opportunity_id)
        ranking_explanation = ranking_explanations.get(opportunity_id)
        line = allocation_lines.get(opportunity_id)
        objective = objective_results.get(opportunity_id)
        quarantined = quarantine.get(opportunity_id)

        if ranked:
            ranking_statement = (
                f"Rank {ranked.rank}; {ranked.disposition.value}; "
                f"priority {ranked.priority_score}; reason {ranked.reason_code.value}."
            )
        else:
            ranking_statement = "No valid ranking outcome was produced."
        if line:
            allocation_statement = (
                f"{line.status.value}: allocated {line.allocated_amount} of "
                f"{line.requested_amount}; reasons "
                f"{', '.join(item.value for item in line.reason_codes)}."
            )
        else:
            allocation_statement = "No allocation outcome was produced."
        execution_amount = execution_amounts.get(opportunity_id, Decimal("0"))
        execution_statement = (
            f"Execution purchases total {execution_amount}."
            if line else "No execution instruction was produced."
        )
        quarantine_statement = (
            f"Quarantined at {quarantined.stage.value}: {quarantined.reason_code} — "
            f"{quarantined.message}"
            if quarantined else "Not quarantined."
        )

        if quarantined:
            headline = f"{opportunity_id} quarantined during orchestration"
            summary = quarantine_statement
        elif line and line.allocated_amount > 0:
            headline = f"{opportunity_id} selected and funded"
            summary = f"{ranking_statement} {allocation_statement}"
        elif ranked:
            headline = ranking_explanation.headline
            summary = f"{ranking_explanation.summary} {allocation_statement}"
        else:
            headline = f"{opportunity_id} did not complete orchestration"
            summary = quarantine_statement

        explanation = UnifiedOpportunityExplanation(
            opportunity_id,
            headline,
            summary,
            ranking_statement,
            allocation_statement,
            execution_statement,
            quarantine_statement,
            {
                "objective_utility": str(objective.objective_utility) if objective else "",
                "output_fingerprint": run.output_fingerprint or "",
                "policy_fingerprint": run.policy_fingerprint,
                "ranking_fingerprint": result.ranking.batch_fingerprint if result.ranking else "",
            },
        )
        explanations.append(explanation)
        dashboard.append(_freeze({
            "run_id": run.run_id,
            "run_status": run.status.value,
            "opportunity_id": opportunity_id,
            "rank": ranked.rank if ranked else "",
            "priority_score": str(ranked.priority_score) if ranked else "",
            "ranking_disposition": ranked.disposition.value if ranked else "",
            "ranking_reason": ranked.reason_code.value if ranked else "",
            "allocated_amount": str(line.allocated_amount) if line else "",
            "allocation_status": line.status.value if line else "",
            "execution_amount": str(execution_amount) if line else "",
            "quarantine_stage": quarantined.stage.value if quarantined else "",
            "quarantine_reason": quarantined.reason_code if quarantined else "",
            "headline": headline,
            "summary": summary,
        }))

    audit: list[Mapping[str, object]] = []
    sequence = 1
    for record in run.stage_records:
        audit.append(_freeze({
            "run_id": run.run_id,
            "sequence": sequence,
            "opportunity_id": "",
            "stage": record.stage.value,
            "status": record.status.value,
            "evidence_json": json.dumps(_jsonable(record.evidence), sort_keys=True, separators=(",", ":")),
        }))
        sequence += 1
    if result.ranking:
        for artifact in result.ranking.artifacts:
            audit.append(_freeze({
                "run_id": run.run_id,
                "sequence": sequence,
                "opportunity_id": artifact.opportunity_id,
                "stage": f"RANKING_{artifact.stage}",
                "status": "PRESERVED",
                "evidence_json": json.dumps(_jsonable(artifact.evidence), sort_keys=True, separators=(",", ":")),
            }))
            sequence += 1
    for item in run.quarantined:
        audit.append(_freeze({
            "run_id": run.run_id,
            "sequence": sequence,
            "opportunity_id": item.opportunity_id,
            "stage": f"QUARANTINE_{item.stage.value}",
            "status": item.failure_scope.value,
            "evidence_json": json.dumps({"reason_code": item.reason_code, "message": item.message}, sort_keys=True, separators=(",", ":")),
        }))
        sequence += 1

    capital_summary = None
    if result.optimization:
        capital = result.optimization.capital_result
        capital_summary = {
            "gross_capital": str(capital.gross_capital),
            "reserved_capital": str(capital.reserved_capital),
            "allocated_capital": str(capital.allocated_capital),
            "residual_capital": str(capital.residual_capital),
            "capital_conserved": capital.gross_capital
            == capital.reserved_capital + capital.allocated_capital + capital.residual_capital,
        }
    core = {
        "schema_version": "5.4.5",
        "run_id": run.run_id,
        "run_status": run.status.value,
        "policy_fingerprint": run.policy_fingerprint,
        "orchestration_fingerprint": run.output_fingerprint,
        "ranking_batch_id": result.ranking.batch_id if result.ranking else None,
        "ranking_fingerprint": result.ranking.batch_fingerprint if result.ranking else None,
        "capital_summary": capital_summary,
        "opportunity_count": len(explanations),
        "quarantine_count": len(run.quarantined),
        "explanations": [_jsonable(item) for item in explanations],
        "dashboard_rows": [_jsonable(item) for item in dashboard],
        "audit_rows": [_jsonable(item) for item in audit],
    }
    package_fingerprint = _fingerprint(core)
    document = {**core, "package_fingerprint": package_fingerprint}
    json_text = json.dumps(
        document,
        sort_keys=True,
        indent=indent,
        separators=(",", ":") if indent is None else None,
    )
    dashboard_rows = tuple(dashboard)
    audit_rows = tuple(audit)
    return UnifiedOutputPackage(
        run.run_id,
        run.status.value,
        run.output_fingerprint,
        package_fingerprint,
        tuple(explanations),
        dashboard_rows,
        audit_rows,
        json_text,
        _csv(dashboard_rows, DASHBOARD_COLUMNS),
        _csv(audit_rows, AUDIT_COLUMNS),
    )


def validate_unified_output(package: UnifiedOutputPackage) -> None:
    """Fail closed when serialized cardinality, identity, or fingerprint drifts."""
    document = json.loads(package.json_text)
    supplied = document.pop("package_fingerprint")
    if supplied != package.package_fingerprint or _fingerprint(document) != supplied:
        raise ValueError("unified output package fingerprint mismatch")
    dashboard = tuple(csv.DictReader(io.StringIO(package.dashboard_csv)))
    audit = tuple(csv.DictReader(io.StringIO(package.audit_csv)))
    if len(dashboard) != len(package.dashboard_rows):
        raise ValueError("dashboard CSV cardinality mismatch")
    if len(audit) != len(package.audit_rows):
        raise ValueError("audit CSV cardinality mismatch")
    if document["run_id"] != package.run_id or any(
        row["run_id"] != package.run_id for row in (*dashboard, *audit)
    ):
        raise ValueError("unified output run identity mismatch")
