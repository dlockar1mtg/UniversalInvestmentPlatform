"""Stable JSON, dashboard, and audit outputs for monitoring orchestration."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import io
import json
from types import MappingProxyType
from typing import Mapping

from .orchestrator import MonitoringOrchestrationResult


DASHBOARD_COLUMNS = (
    "monitoring_run_id", "monitoring_status", "source_run_id", "opportunity_id",
    "drift_severity", "drift_reason_codes", "outcome_status", "execution_variance",
    "position_variance", "target_shortfall", "trigger_disposition", "trigger_severity",
    "trigger_reason_codes", "eligible_at",
)

AUDIT_COLUMNS = (
    "monitoring_run_id", "sequence", "opportunity_id", "stage", "status",
    "evidence_json",
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
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _freeze(values: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType({str(key): values[key] for key in sorted(values, key=str)})


def _csv(rows: tuple[Mapping[str, object], ...], columns: tuple[str, ...]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=columns, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _fingerprint(document: Mapping[str, object]) -> str:
    encoded = json.dumps(
        _jsonable(document), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class MonitoringOutputPackage:
    monitoring_run_id: str
    package_fingerprint: str
    dashboard_rows: tuple[Mapping[str, object], ...]
    audit_rows: tuple[Mapping[str, object], ...]
    json_text: str
    dashboard_csv: str
    audit_csv: str


def build_monitoring_output(
    result: MonitoringOrchestrationResult,
    *,
    indent: int | None = 2,
) -> MonitoringOutputPackage:
    run = result.result
    source_run_id = result.control.source_run_id
    signals_by_id: dict[str, list] = {}
    for signal in result.drift.signals:
        signals_by_id.setdefault(signal.opportunity_id or "PORTFOLIO", []).append(signal)
    outcomes_by_id = {
        item.opportunity_id: item for item in (result.outcomes.lines if result.outcomes else ())
    }
    identifiers = sorted(set(signals_by_id) | set(outcomes_by_id)) or ["PORTFOLIO"]
    dashboard: list[Mapping[str, object]] = []
    for opportunity_id in identifiers:
        signals = sorted(
            signals_by_id.get(opportunity_id, ()),
            key=lambda item: (item.category.value, item.metric_name, item.reason_code),
        )
        outcome = outcomes_by_id.get(opportunity_id)
        severity_order = {"NONE": 0, "WATCH": 1, "MATERIAL": 2, "CRITICAL": 3}
        drift_severity = max(
            (item.severity.value for item in signals),
            key=lambda value: severity_order[value],
            default="NONE",
        )
        dashboard.append(_freeze({
            "monitoring_run_id": run.monitoring_run_id,
            "monitoring_status": run.status.value,
            "source_run_id": source_run_id,
            "opportunity_id": opportunity_id,
            "drift_severity": drift_severity,
            "drift_reason_codes": "|".join(sorted(item.reason_code for item in signals)),
            "outcome_status": outcome.status.value if outcome else "",
            "execution_variance": str(outcome.execution_variance) if outcome else "",
            "position_variance": str(outcome.position_variance) if outcome else "",
            "target_shortfall": str(outcome.target_shortfall) if outcome else "",
            "trigger_disposition": run.trigger.disposition.value,
            "trigger_severity": run.trigger.severity.value,
            "trigger_reason_codes": "|".join(run.trigger.reason_codes),
            "eligible_at": run.trigger.eligible_at.isoformat(),
        }))

    audit: list[Mapping[str, object]] = []
    sequence = 1
    for artifact in result.artifacts:
        audit.append(_freeze({
            "monitoring_run_id": run.monitoring_run_id,
            "sequence": sequence,
            "opportunity_id": "",
            "stage": artifact.stage,
            "status": artifact.status,
            "evidence_json": json.dumps(_jsonable(artifact.evidence), sort_keys=True, separators=(",", ":")),
        }))
        sequence += 1
    for signal in result.drift.signals:
        audit.append(_freeze({
            "monitoring_run_id": run.monitoring_run_id,
            "sequence": sequence,
            "opportunity_id": signal.opportunity_id or "PORTFOLIO",
            "stage": "DRIFT_SIGNAL",
            "status": signal.severity.value,
            "evidence_json": json.dumps({
                "baseline_value": str(signal.baseline_value), "category": signal.category.value,
                "delta": str(signal.delta), "metric_name": signal.metric_name,
                "observed_value": str(signal.observed_value), "reason_code": signal.reason_code,
            }, sort_keys=True, separators=(",", ":")),
        }))
        sequence += 1
    for missing in result.drift.missing_metrics:
        audit.append(_freeze({
            "monitoring_run_id": run.monitoring_run_id,
            "sequence": sequence,
            "opportunity_id": missing.opportunity_id or "PORTFOLIO",
            "stage": "MISSING_METRIC",
            "status": missing.reason_code,
            "evidence_json": json.dumps({
                "category": missing.category, "metric_name": missing.metric_name,
            }, sort_keys=True, separators=(",", ":")),
        }))
        sequence += 1
    if result.outcomes:
        for line in result.outcomes.lines:
            audit.append(_freeze({
                "monitoring_run_id": run.monitoring_run_id,
                "sequence": sequence,
                "opportunity_id": line.opportunity_id,
                "stage": "OUTCOME_LINE",
                "status": line.status.value,
                "evidence_json": json.dumps({
                    "executed_amount": str(line.executed_amount),
                    "execution_variance": str(line.execution_variance),
                    "position_variance": str(line.position_variance),
                    "reason_codes": [item.value for item in line.reason_codes],
                    "target_shortfall": str(line.target_shortfall),
                }, sort_keys=True, separators=(",", ":")),
            }))
            sequence += 1

    core = {
        "schema_version": "5.5.5",
        "monitoring_run_id": run.monitoring_run_id,
        "monitoring_status": run.status.value,
        "source_run_id": source_run_id,
        "policy_fingerprint": run.policy_fingerprint,
        "output_fingerprint": run.output_fingerprint,
        "drift_fingerprint": result.drift.detection_fingerprint,
        "outcome_fingerprint": result.outcomes.result_fingerprint if result.outcomes else None,
        "control_fingerprint": result.control.decision_fingerprint,
        "trigger": {
            "disposition": run.trigger.disposition.value,
            "severity": run.trigger.severity.value,
            "reason_codes": list(run.trigger.reason_codes),
            "eligible_at": run.trigger.eligible_at.isoformat(),
        },
        "dashboard_rows": [_jsonable(item) for item in dashboard],
        "audit_rows": [_jsonable(item) for item in audit],
    }
    package_fingerprint = _fingerprint(core)
    document = {**core, "package_fingerprint": package_fingerprint}
    json_text = json.dumps(
        document, sort_keys=True, indent=indent,
        separators=(",", ":") if indent is None else None,
    )
    dashboard_rows = tuple(dashboard)
    audit_rows = tuple(audit)
    return MonitoringOutputPackage(
        run.monitoring_run_id, package_fingerprint, dashboard_rows, audit_rows,
        json_text, _csv(dashboard_rows, DASHBOARD_COLUMNS), _csv(audit_rows, AUDIT_COLUMNS),
    )


def validate_monitoring_output(package: MonitoringOutputPackage) -> None:
    document = json.loads(package.json_text)
    supplied = document.pop("package_fingerprint")
    if supplied != package.package_fingerprint or _fingerprint(document) != supplied:
        raise ValueError("monitoring output package fingerprint mismatch")
    dashboard = tuple(csv.DictReader(io.StringIO(package.dashboard_csv)))
    audit = tuple(csv.DictReader(io.StringIO(package.audit_csv)))
    if len(dashboard) != len(package.dashboard_rows):
        raise ValueError("monitoring dashboard CSV cardinality mismatch")
    if len(audit) != len(package.audit_rows):
        raise ValueError("monitoring audit CSV cardinality mismatch")
    if [int(item["sequence"]) for item in audit] != list(range(1, len(audit) + 1)):
        raise ValueError("monitoring audit sequence is not contiguous")
    if document["monitoring_run_id"] != package.monitoring_run_id or any(
        item["monitoring_run_id"] != package.monitoring_run_id
        for item in (*dashboard, *audit)
    ):
        raise ValueError("monitoring output run identity mismatch")
