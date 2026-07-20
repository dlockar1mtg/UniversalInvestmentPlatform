"""Versioned transport-independent production API boundary."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from typing import Mapping

from .contracts import AuditEvent, ProductionRun
from .persistence import SQLiteProductionRepository


@dataclass(frozen=True)
class APIResponse:
    status_code: int
    body: Mapping[str, object]


class ProductionAPI:
    """Handle stable v1 API requests without coupling to a web framework."""

    def __init__(self, repository: SQLiteProductionRepository):
        self.repository = repository

    @staticmethod
    def _error(status: int, code: str, message: str) -> APIResponse:
        return APIResponse(status, {"error": {"code": code, "message": message}})

    def handle(self, method: str, path: str, body: bytes | str | None = None) -> APIResponse:
        method = method.upper()
        if method == "POST" and path == "/v1/runs":
            return self._submit(body)
        prefix = "/v1/runs/"
        if method == "GET" and path.startswith(prefix):
            run_id = path[len(prefix):]
            if not run_id or "/" in run_id:
                return self._error(404, "NOT_FOUND", "resource was not found")
            try:
                return APIResponse(200, self._run_document(self.repository.get_run(run_id)))
            except KeyError:
                return self._error(404, "RUN_NOT_FOUND", "run does not exist")
        return self._error(404, "NOT_FOUND", "resource was not found")

    def _submit(self, body: bytes | str | None) -> APIResponse:
        try:
            document = json.loads(body or "")
            required = ("run_id", "source_phase", "policy_fingerprint", "requested_at", "payload")
            if not isinstance(document, dict) or any(key not in document for key in required):
                raise ValueError("required fields are missing")
            payload = json.dumps(document["payload"], sort_keys=True, separators=(",", ":"))
            request_fingerprint = sha256(payload.encode()).hexdigest()
            run = ProductionRun(
                str(document["run_id"]), str(document["source_phase"]), request_fingerprint,
                str(document["policy_fingerprint"]), datetime.fromisoformat(document["requested_at"]),
                metadata={"api_version": "v1"},
            )
            registered = self.repository.register_run(run)
            if not self.repository.audit_events(run.run_id):
                self.repository.append_audit_event(AuditEvent(
                    f"{run.run_id}:registered", run.run_id, 1, "API_RUN_REGISTERED",
                    run.created_at, {"request_fingerprint": request_fingerprint},
                ))
            return APIResponse(202, self._run_document(registered))
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self._error(400, "INVALID_REQUEST", str(exc))

    @staticmethod
    def _run_document(run: ProductionRun) -> Mapping[str, object]:
        return {
            "api_version": "v1", "run_id": run.run_id,
            "source_phase": run.source_phase, "status": run.status.value,
            "request_fingerprint": run.request_fingerprint,
            "policy_fingerprint": run.policy_fingerprint,
            "created_at": run.created_at.isoformat(),
        }
