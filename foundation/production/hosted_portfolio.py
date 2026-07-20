"""Authenticated HTTP routes for bounded portfolio snapshot ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Mapping
from uuid import uuid4

from fastapi import Header, Request
from fastapi.responses import JSONResponse

from .http_service import HTTPServiceSettings
from .observability import OperationalEvent
from .portfolio import preview_portfolio_csv
from .portfolio_persistence import create_portfolio_snapshot
from .security import APIKeyAuthenticator, Permission


def _authenticator(settings: HTTPServiceSettings) -> APIKeyAuthenticator:
    principals, hashes = {}, {}
    for principal_id, (credential, roles) in sorted(settings.credentials.items()):
        principals[principal_id] = roles
        hashes[principal_id] = APIKeyAuthenticator.hash_credential(credential)
    return APIKeyAuthenticator(principals, hashes)


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _position_document(position) -> dict[str, object]:
    return dict(position.canonical())


def _snapshot_document(snapshot, *, include_positions: bool) -> dict[str, object]:
    document = dict(snapshot.summary())
    if include_positions:
        document["positions"] = [_position_document(item) for item in snapshot.positions]
    return document


def install_hosted_portfolio_routes(
    app,
    settings: HTTPServiceSettings,
    repository,
    *,
    maximum_csv_bytes: int = 262_144,
) -> None:
    if maximum_csv_bytes < 1024:
        raise ValueError("maximum CSV size must be at least 1024 bytes")
    authenticator = _authenticator(settings)
    app.state.portfolio_repository = repository

    def authorize(credential: str | None, permission: Permission):
        principal = authenticator.authenticate(credential)
        if principal is None:
            return None, _error("UNAUTHENTICATED", "valid credentials are required", 401)
        if not principal.permits(permission):
            return principal, _error("FORBIDDEN", "permission is required", 403)
        return principal, None

    def record(event_type: str, correlation_id: str, fields: Mapping[str, object]) -> None:
        if hasattr(app.state, "events"):
            app.state.events.record(OperationalEvent(event_type, datetime.now(timezone.utc), correlation_id, fields))

    def count(status: int) -> None:
        if hasattr(app.state, "metrics"):
            app.state.metrics.increment("portfolio_import_requests_total", {"status": str(status)})

    @app.post("/v1/portfolio/snapshots")
    async def import_snapshot(
        request: Request,
        x_api_key: str | None = Header(default=None),
        x_correlation_id: str | None = Header(default=None),
    ):
        correlation_id = x_correlation_id or str(uuid4())
        principal, denied = authorize(x_api_key, Permission.RUN_SUBMIT)
        if denied:
            count(denied.status_code)
            record("PORTFOLIO_IMPORT_REJECTED", correlation_id, {
                "principal_id": principal.principal_id if principal else "ANONYMOUS",
                "reason": denied.body.decode("utf-8"), "credential": x_api_key,
            })
            denied.headers["X-Correlation-ID"] = correlation_id
            return denied
        media_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if media_type not in {"text/csv", "application/csv"}:
            count(415)
            return _error("UNSUPPORTED_MEDIA_TYPE", "portfolio import requires text/csv", 415)
        length = request.headers.get("content-length")
        if length and int(length) > maximum_csv_bytes:
            count(413)
            return _error("PORTFOLIO_TOO_LARGE", "portfolio CSV exceeds the permitted size", 413)
        body = await request.body()
        if len(body) > maximum_csv_bytes:
            count(413)
            return _error("PORTFOLIO_TOO_LARGE", "portfolio CSV exceeds the permitted size", 413)
        try:
            text = body.decode("utf-8-sig", errors="strict")
        except UnicodeDecodeError:
            count(422)
            return _error("PORTFOLIO_ENCODING", "portfolio CSV must be UTF-8", 422)
        report = preview_portfolio_csv(text, is_text=True)
        if not report.valid:
            count(422)
            record("PORTFOLIO_IMPORT_REJECTED", correlation_id, {
                "principal_id": principal.principal_id, "error_count": len(report.errors),
                "credential": x_api_key,
            })
            return JSONResponse({
                "error": {"code": "PORTFOLIO_INVALID", "message": "portfolio CSV failed validation"},
                "errors": [
                    {"field": item.field, "message": item.message, "row_number": item.row_number}
                    for item in report.errors
                ],
            }, status_code=422, headers={"X-Correlation-ID": correlation_id})
        candidate = create_portfolio_snapshot(
            report.positions,
            metadata={"ingestion": "hosted-api", "principal_id": principal.principal_id},
        )
        try:
            repository.get(candidate.snapshot_id)
            existed = True
        except KeyError:
            existed = False
        persisted = repository.save(candidate)
        status = 200 if existed else 201
        count(status)
        record("PORTFOLIO_SNAPSHOT_REUSED" if existed else "PORTFOLIO_SNAPSHOT_CREATED", correlation_id, {
            "principal_id": principal.principal_id, "snapshot_id": persisted.snapshot_id,
            "fingerprint": persisted.fingerprint, "position_count": len(persisted.positions),
            "credential": x_api_key,
        })
        return JSONResponse(
            {"created": not existed, "snapshot": _snapshot_document(persisted, include_positions=False)},
            status_code=status, headers={"X-Correlation-ID": correlation_id},
        )

    @app.get("/v1/portfolio/snapshots/current")
    def current_snapshot(x_api_key: str | None = Header(default=None)):
        _, denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        snapshot = repository.latest()
        if snapshot is None:
            return _error("PORTFOLIO_NOT_FOUND", "no portfolio snapshot is available", 404)
        return _snapshot_document(snapshot, include_positions=True)

    @app.get("/v1/portfolio/snapshots")
    def snapshot_history(limit: int = 20, x_api_key: str | None = Header(default=None)):
        _, denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        try:
            snapshots = repository.history(limit)
        except ValueError:
            return _error("INVALID_LIMIT", "history limit must be between 1 and 100", 422)
        return {"items": [_snapshot_document(item, include_positions=False) for item in snapshots]}
