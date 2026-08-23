"""Authenticated append-only transaction API for UIP application state."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping
from uuid import uuid4

from fastapi import Header, Request
from fastapi.responses import JSONResponse

from .http_service import HTTPServiceSettings
from .observability import OperationalEvent
from .security import APIKeyAuthenticator, Permission
from .transactions import TransactionType, create_transaction


def _authenticator(settings: HTTPServiceSettings) -> APIKeyAuthenticator:
    principals, hashes = {}, {}
    for principal_id, (credential, roles) in sorted(settings.credentials.items()):
        principals[principal_id] = roles
        hashes[principal_id] = APIKeyAuthenticator.hash_credential(credential)
    return APIKeyAuthenticator(principals, hashes)


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message}}, status_code=status)


def _document(item) -> dict[str, object]:
    return dict(item.document())


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("occurred_at is required")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("occurred_at must include timezone")
    return parsed


def _optional_decimal(value: object) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def install_hosted_transaction_routes(app, settings: HTTPServiceSettings, repository) -> None:
    authenticator = _authenticator(settings)
    app.state.transaction_repository = repository

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

    @app.post("/v1/transactions")
    async def append_transaction(
        request: Request,
        x_api_key: str | None = Header(default=None),
        x_correlation_id: str | None = Header(default=None),
    ):
        correlation_id = x_correlation_id or str(uuid4())
        principal, denied = authorize(x_api_key, Permission.RUN_SUBMIT)
        if denied:
            denied.headers["X-Correlation-ID"] = correlation_id
            return denied
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("transaction body must be a JSON object")
            item = create_transaction(
                transaction_type=body.get("transaction_type", ""),
                domain_id=str(body.get("domain_id", "")),
                asset_id=str(body.get("asset_id", "")),
                occurred_at=_parse_datetime(body.get("occurred_at")),
                quantity=body.get("quantity", ""),
                price_per_unit=_optional_decimal(body.get("price_per_unit")),
                fees=body.get("fees", "0"),
                currency=str(body.get("currency", "USD")),
                account_id=str(body.get("account_id", "")),
                destination_account_id=body.get("destination_account_id"),
                venue=str(body.get("venue", "")),
                external_reference=str(body.get("external_reference", "")),
                notes=str(body.get("notes", "")),
                recorded_by=principal.principal_id,
                corrects_transaction_id=body.get("corrects_transaction_id"),
                correction_reason=body.get("correction_reason"),
                metadata={"source": "hosted-dashboard"},
            )
            repository.append(item)
        except (ValueError, InvalidOperation, KeyError) as exc:
            record("TRANSACTION_REJECTED", correlation_id, {
                "principal_id": principal.principal_id,
                "reason": str(exc),
                "credential": x_api_key,
            })
            response = _error("TRANSACTION_INVALID", str(exc), 422)
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        record("TRANSACTION_RECORDED", correlation_id, {
            "principal_id": principal.principal_id,
            "transaction_id": item.transaction_id,
            "transaction_type": item.transaction_type.value,
            "domain_id": item.domain_id,
            "asset_id": item.asset_id,
            "corrects_transaction_id": item.corrects_transaction_id,
            "credential": x_api_key,
        })
        return JSONResponse(
            {"transaction": _document(item)},
            status_code=201,
            headers={"X-Correlation-ID": correlation_id},
        )

    @app.get("/v1/transactions")
    def list_transactions(
        limit: int = 100,
        offset: int = 0,
        x_api_key: str | None = Header(default=None),
    ):
        _, denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        try:
            items = repository.list(limit=limit, offset=offset)
        except ValueError as exc:
            return _error("INVALID_WINDOW", str(exc), 422)
        return {"items": [_document(item) for item in items], "limit": limit, "offset": offset}

    @app.get("/v1/transactions/{transaction_id}")
    def get_transaction(transaction_id: str, x_api_key: str | None = Header(default=None)):
        _, denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        try:
            item = repository.get(transaction_id)
        except KeyError:
            return _error("TRANSACTION_NOT_FOUND", "transaction was not found", 404)
        return _document(item)
