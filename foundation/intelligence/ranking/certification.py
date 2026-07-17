"""Formal certification for the Phase 5.2 portfolio-ranking subsystem."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from enum import Enum
import io
import json
from typing import Iterable

from .competition import CompetitionPolicy
from .orchestrator import PortfolioRankingItem, run_portfolio_ranking
from .serialization import ranking_audit_csv, ranking_batch_json, ranking_dashboard_csv


class CertificationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class CertificationCheck:
    check_id: str
    status: CertificationStatus
    evidence: str


@dataclass(frozen=True)
class Phase52CertificationReport:
    phase: str
    status: CertificationStatus
    batch_id: str
    batch_fingerprint: str | None
    checks: tuple[CertificationCheck, ...]

    @property
    def passed(self) -> bool:
        return self.status is CertificationStatus.PASSED

    def to_dict(self) -> dict[str, object]:
        return {
            "phase": self.phase,
            "status": self.status.value,
            "batch_id": self.batch_id,
            "batch_fingerprint": self.batch_fingerprint,
            "checks": [
                {
                    "check_id": check.check_id,
                    "status": check.status.value,
                    "evidence": check.evidence,
                }
                for check in self.checks
            ],
        }

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent)


def _check(check_id: str, condition: bool, success: str, failure: str) -> CertificationCheck:
    return CertificationCheck(
        check_id,
        CertificationStatus.PASSED if condition else CertificationStatus.FAILED,
        success if condition else failure,
    )


def certify_phase_5_2(
    items: Iterable[PortfolioRankingItem],
    policy: CompetitionPolicy,
    *,
    batch_id: str = "phase-5.2-certification",
) -> Phase52CertificationReport:
    """Run deterministic, boundary, cross-asset, and output certification."""
    materialized = tuple(items)
    checks: list[CertificationCheck] = []
    groups = {item.group_key for item in materialized}
    checks.append(
        _check(
            "CROSS_ASSET_COVERAGE",
            len(groups) >= 2,
            f"Certified {len(groups)} portfolio groups: {', '.join(sorted(groups))}.",
            "Certification requires at least two distinct portfolio groups.",
        )
    )
    try:
        first = run_portfolio_ranking(batch_id, materialized, policy)
        repeated = run_portfolio_ranking(batch_id, materialized, policy)
        reversed_result = run_portfolio_ranking(batch_id, reversed(materialized), policy)
    except Exception as exc:  # certification converts pipeline failure into evidence
        checks.append(
            CertificationCheck("BATCH_EXECUTION", CertificationStatus.FAILED, str(exc))
        )
        return Phase52CertificationReport(
            "5.2", CertificationStatus.FAILED, batch_id, None, tuple(checks)
        )

    checks.append(_check("BATCH_EXECUTION", True, "Batch executed successfully.", ""))
    checks.append(
        _check(
            "REPEAT_DETERMINISM",
            first == repeated,
            "Repeated execution produced identical results.",
            "Repeated execution changed the batch result.",
        )
    )
    checks.append(
        _check(
            "INPUT_ORDER_INVARIANCE",
            first.batch_fingerprint == reversed_result.batch_fingerprint
            and first.outcomes == reversed_result.outcomes
            and first.explanations == reversed_result.explanations,
            "Reversing input order preserved fingerprint, ranking, and explanations.",
            "Input order changed a certified output.",
        )
    )
    expected_ranks = list(range(1, len(materialized) + 1))
    checks.append(
        _check(
            "STABLE_RANK_BOUNDARY",
            [outcome.rank for outcome in first.outcomes] == expected_ranks,
            f"Ranks are contiguous from 1 through {len(materialized)}.",
            "Ranks are not unique and contiguous.",
        )
    )
    selected = first.selected
    group_counts: dict[str, int] = {}
    by_id = {item.opportunity_id: item for item in materialized}
    for outcome in selected:
        group = by_id[outcome.opportunity_id].group_key
        group_counts[group] = group_counts.get(group, 0) + 1
    within_group_limit = policy.max_selected_per_group is None or all(
        count <= policy.max_selected_per_group for count in group_counts.values()
    )
    checks.append(
        _check(
            "CAPACITY_BOUNDARIES",
            len(selected) <= policy.max_selected and within_group_limit,
            "Batch and group selection capacities were respected.",
            "A selection capacity boundary was exceeded.",
        )
    )
    valid_dispositions = {"SELECTED", "DEFERRED", "SUPPRESSED", "EXCLUDED"}
    checks.append(
        _check(
            "DISPOSITION_INTEGRITY",
            len(first.outcomes) == len(materialized)
            and all(outcome.disposition.value in valid_dispositions for outcome in first.outcomes),
            "Every opportunity received one valid disposition.",
            "An opportunity is missing or has an invalid disposition.",
        )
    )
    expected_stages = {
        "COMPARABILITY", "PORTFOLIO_CONTEXT", "FACTORS", "PRIORITY", "COMPETITION", "EXPLANATION"
    }
    artifact_complete = len(first.artifacts) == len(materialized) * 6
    for opportunity_id in by_id:
        artifact_complete = artifact_complete and {
            artifact.stage for artifact in first.artifacts if artifact.opportunity_id == opportunity_id
        } == expected_stages
    checks.append(
        _check(
            "AUDIT_ARTIFACT_COMPLETENESS",
            artifact_complete,
            "Every opportunity preserved all six ordered stage artifacts.",
            "One or more stage artifacts are missing or duplicated.",
        )
    )
    try:
        json_payload = json.loads(ranking_batch_json(first))
        dashboard_rows = list(csv.DictReader(io.StringIO(ranking_dashboard_csv(first))))
        audit_rows = list(csv.DictReader(io.StringIO(ranking_audit_csv(first))))
        serialization_valid = (
            json_payload["batch_fingerprint"] == first.batch_fingerprint
            and len(json_payload["ranking"]) == len(materialized)
            and len(dashboard_rows) == len(materialized)
            and len(audit_rows) == len(materialized) * 6
        )
    except Exception:
        serialization_valid = False
    checks.append(
        _check(
            "SERIALIZATION_INTEGRITY",
            serialization_valid,
            "JSON, dashboard CSV, and audit CSV preserve batch cardinality and fingerprint.",
            "One or more serialized outputs failed integrity validation.",
        )
    )
    status = (
        CertificationStatus.PASSED
        if all(check.status is CertificationStatus.PASSED for check in checks)
        else CertificationStatus.FAILED
    )
    return Phase52CertificationReport(
        "5.2", status, batch_id, first.batch_fingerprint, tuple(checks)
    )
