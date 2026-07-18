"""Run registry, reproducibility verification, and atomic recovery planning."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from hashlib import sha256
import json
from typing import Mapping

from .contracts import OrchestrationRunStatus, OrchestrationStage, StageStatus, UniversalRunRequest
from .orchestrator import (
    EndToEndOrchestrationResult,
    OrchestrationEnginePolicy,
    run_universal_orchestration,
)


def _portable(value):
    if isinstance(value, Mapping):
        return {str(key): _portable(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [_portable(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "__dataclass_fields__"):
        return {
            name: _portable(getattr(value, name))
            for name in value.__dataclass_fields__
        }
    return value


def _hash(value: object) -> str:
    encoded = json.dumps(
        _portable(value), sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def request_fingerprint(request: UniversalRunRequest) -> str:
    """Fingerprint semantic inputs without depending on opportunity input order."""
    payload = {
        "run_id": request.run_id,
        "requested_at": request.requested_at,
        "source_decision_batch_id": request.source_decision_batch_id,
        "portfolio": {
            "snapshot_id": request.portfolio.snapshot_id,
            "as_of": request.portfolio.as_of,
            "currency": request.portfolio.currency,
            "metadata": request.portfolio.metadata,
            "positions": sorted(request.portfolio.positions, key=lambda item: item.opportunity_id),
        },
        "capital": request.capital,
        "opportunities": sorted(request.opportunities, key=lambda item: item.opportunity_id),
        "policy_fingerprint": request.policies.fingerprint,
    }
    return _hash(payload)


@dataclass(frozen=True)
class StageCheckpoint:
    stage: OrchestrationStage
    status: StageStatus
    processed_count: int
    failed_count: int
    evidence_fingerprint: str


@dataclass(frozen=True)
class RunAttempt:
    attempt_number: int
    status: OrchestrationRunStatus
    policy_fingerprint: str
    output_fingerprint: str | None
    checkpoints: tuple[StageCheckpoint, ...]
    result: EndToEndOrchestrationResult

    def __post_init__(self) -> None:
        if self.attempt_number < 1:
            raise ValueError("attempt_number must be positive")


@dataclass(frozen=True)
class RegisteredRun:
    run_id: str
    request_fingerprint: str
    policy_fingerprint: str
    request: UniversalRunRequest
    attempts: tuple[RunAttempt, ...] = ()

    @property
    def latest_attempt(self) -> RunAttempt | None:
        return self.attempts[-1] if self.attempts else None


class RecoveryAction(str, Enum):
    RETURN_COMPLETED = "RETURN_COMPLETED"
    REPLAY_FROM_ATOMIC_START = "REPLAY_FROM_ATOMIC_START"


@dataclass(frozen=True)
class RecoveryPlan:
    run_id: str
    action: RecoveryAction
    prior_attempts: int
    last_passed_stage: OrchestrationStage | None
    reason_code: str


@dataclass(frozen=True)
class ReproducibilityReport:
    run_id: str
    reference_attempt: int
    replay_attempt: int
    request_fingerprint_matches: bool
    policy_fingerprint_matches: bool
    output_fingerprint_matches: bool
    checkpoint_fingerprints_match: bool

    @property
    def reproducible(self) -> bool:
        return all((
            self.request_fingerprint_matches,
            self.policy_fingerprint_matches,
            self.output_fingerprint_matches,
            self.checkpoint_fingerprints_match,
        ))


def _checkpoints(result: EndToEndOrchestrationResult) -> tuple[StageCheckpoint, ...]:
    return tuple(
        StageCheckpoint(
            record.stage,
            record.status,
            record.processed_count,
            record.failed_count,
            _hash(record.evidence),
        )
        for record in result.run.stage_records
    )


class InMemoryRunRegistry:
    """Deterministic reference registry; persistence adapters can wrap this API."""

    def __init__(self) -> None:
        self._runs: dict[str, RegisteredRun] = {}

    def register(self, request: UniversalRunRequest) -> RegisteredRun:
        fingerprint = request_fingerprint(request)
        existing = self._runs.get(request.run_id)
        if existing is not None:
            if existing.request_fingerprint != fingerprint:
                raise ValueError("run_id already exists with different immutable inputs")
            return existing
        registered = RegisteredRun(
            request.run_id, fingerprint, request.policies.fingerprint, request
        )
        self._runs[request.run_id] = registered
        return registered

    def get(self, run_id: str) -> RegisteredRun:
        try:
            return self._runs[run_id]
        except KeyError as exc:
            raise KeyError(f"unknown orchestration run: {run_id}") from exc

    def list_runs(self) -> tuple[RegisteredRun, ...]:
        return tuple(self._runs[key] for key in sorted(self._runs))

    def record(self, result: EndToEndOrchestrationResult) -> RegisteredRun:
        registered = self.get(result.run.run_id)
        if result.run.policy_fingerprint != registered.policy_fingerprint:
            raise ValueError("result policy fingerprint does not match registered run")
        attempt = RunAttempt(
            len(registered.attempts) + 1,
            result.run.status,
            result.run.policy_fingerprint,
            result.run.output_fingerprint,
            _checkpoints(result),
            result,
        )
        updated = RegisteredRun(
            registered.run_id,
            registered.request_fingerprint,
            registered.policy_fingerprint,
            registered.request,
            (*registered.attempts, attempt),
        )
        self._runs[registered.run_id] = updated
        return updated

    def execute(
        self, request: UniversalRunRequest, policy: OrchestrationEnginePolicy
    ) -> EndToEndOrchestrationResult:
        registered = self.register(request)
        latest = registered.latest_attempt
        if latest is not None and latest.status in {
            OrchestrationRunStatus.COMPLETED,
            OrchestrationRunStatus.COMPLETED_WITH_QUARANTINE,
        }:
            return latest.result
        result = run_universal_orchestration(request, policy)
        self.record(result)
        return result

    def recovery_plan(self, run_id: str) -> RecoveryPlan:
        registered = self.get(run_id)
        latest = registered.latest_attempt
        if latest is None:
            return RecoveryPlan(
                run_id, RecoveryAction.REPLAY_FROM_ATOMIC_START, 0, None,
                "REGISTERED_NOT_EXECUTED",
            )
        passed = tuple(
            item.stage for item in latest.checkpoints if item.status is StageStatus.PASSED
        )
        if latest.status in {
            OrchestrationRunStatus.COMPLETED,
            OrchestrationRunStatus.COMPLETED_WITH_QUARANTINE,
        }:
            return RecoveryPlan(
                run_id, RecoveryAction.RETURN_COMPLETED, len(registered.attempts),
                passed[-1] if passed else None, "TERMINAL_RESULT_REUSABLE",
            )
        return RecoveryPlan(
            run_id, RecoveryAction.REPLAY_FROM_ATOMIC_START, len(registered.attempts),
            passed[-1] if passed else None, "FAILED_ATTEMPT_REQUIRES_ATOMIC_REPLAY",
        )

    def recover(
        self, run_id: str, policy: OrchestrationEnginePolicy
    ) -> EndToEndOrchestrationResult:
        registered = self.get(run_id)
        plan = self.recovery_plan(run_id)
        if plan.action is RecoveryAction.RETURN_COMPLETED:
            return registered.latest_attempt.result
        result = run_universal_orchestration(registered.request, policy)
        self.record(result)
        return result

    def verify_reproducibility(
        self, run_id: str, policy: OrchestrationEnginePolicy
    ) -> ReproducibilityReport:
        registered = self.get(run_id)
        reference = registered.latest_attempt
        if reference is None:
            raise ValueError("run must have an attempt before reproducibility verification")
        replay = run_universal_orchestration(registered.request, policy)
        updated = self.record(replay)
        replay_attempt = updated.latest_attempt
        return ReproducibilityReport(
            run_id,
            reference.attempt_number,
            replay_attempt.attempt_number,
            request_fingerprint(registered.request) == registered.request_fingerprint,
            replay.run.policy_fingerprint == registered.policy_fingerprint,
            replay.run.output_fingerprint == reference.output_fingerprint,
            replay_attempt.checkpoints == reference.checkpoints,
        )
