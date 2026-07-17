"""Certification report serialization and persistence."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .certification_contracts import (
    CertificationGate,
    CertificationGateResult,
    CertificationStatus,
    ForecastCertificationRecord,
    ForecastCertificationReport,
)


def certification_report_to_dict(
    report: ForecastCertificationReport,
) -> dict[str, Any]:
    """Convert a certification report to a JSON-safe mapping."""

    return {
        "generated_at": report.generated_at.isoformat(),
        "records": [
            {
                "certification_id": record.certification_id,
                "model_key": record.model_key,
                "status": record.status.value,
                "certified_at": record.certified_at.isoformat(),
                "effective_date": record.effective_date.isoformat(),
                "expires_on": record.expires_on.isoformat(),
                "score": record.score,
                "reasons": list(record.reasons),
                "restrictions": list(record.restrictions),
                "metadata": dict(record.metadata),
                "gates": [
                    {
                        "gate": gate.gate.value,
                        "passed": gate.passed,
                        "conditional": gate.conditional,
                        "observed_value": gate.observed_value,
                        "required_value": gate.required_value,
                        "explanation": gate.explanation,
                    }
                    for gate in record.gates
                ],
            }
            for record in sorted(
                report.records,
                key=lambda value: value.model_key,
            )
        ],
    }


def certification_report_to_json(
    report: ForecastCertificationReport,
) -> str:
    """Serialize a certification report deterministically."""

    return json.dumps(
        certification_report_to_dict(report),
        sort_keys=True,
        separators=(",", ":"),
    )


def certification_report_from_dict(
    payload: dict[str, Any],
) -> ForecastCertificationReport:
    """Rehydrate a certification report."""

    records = tuple(
        ForecastCertificationRecord(
            certification_id=item["certification_id"],
            model_key=item["model_key"],
            status=CertificationStatus(item["status"]),
            certified_at=datetime.fromisoformat(
                item["certified_at"]
            ),
            effective_date=date.fromisoformat(
                item["effective_date"]
            ),
            expires_on=date.fromisoformat(item["expires_on"]),
            score=float(item["score"]),
            reasons=tuple(item.get("reasons", [])),
            restrictions=tuple(item.get("restrictions", [])),
            metadata=item.get("metadata", {}),
            gates=tuple(
                CertificationGateResult(
                    gate=CertificationGate(gate["gate"]),
                    passed=bool(gate["passed"]),
                    conditional=bool(gate["conditional"]),
                    observed_value=gate.get("observed_value"),
                    required_value=gate.get("required_value"),
                    explanation=gate["explanation"],
                )
                for gate in item["gates"]
            ),
        )
        for item in payload["records"]
    )
    return ForecastCertificationReport(
        records=records,
        generated_at=datetime.fromisoformat(payload["generated_at"]),
    )


def save_certification_report(
    report: ForecastCertificationReport,
    path: str | Path,
) -> None:
    """Persist certification output atomically."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_text(
        certification_report_to_json(report),
        encoding="utf-8",
    )
    temporary.replace(destination)


def load_certification_report(
    path: str | Path,
) -> ForecastCertificationReport:
    """Load a certification report from disk."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return certification_report_from_dict(payload)
