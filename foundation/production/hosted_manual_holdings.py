"""Authenticated routes for manual stock and ETF holding snapshots."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from fastapi import Header, Request
from fastapi.responses import JSONResponse

from .manual_holdings import create_manual_holding_snapshot
from .observability import OperationalEvent
from .security import APIKeyAuthenticator, Permission


def install_manual_holding_routes(app, settings, repository):
    principals, hashes = {}, {}
    for pid, (credential, roles) in sorted(settings.credentials.items()):
        principals[pid] = roles
        hashes[pid] = APIKeyAuthenticator.hash_credential(credential)
    auth = APIKeyAuthenticator(principals, hashes)
    app.state.manual_holding_repository = repository

    def authorize(key, permission):
        principal = auth.authenticate(key)
        if principal is None:
            return None, JSONResponse(
                {"error": {"code": "UNAUTHENTICATED", "message": "valid credentials are required"}},
                status_code=401,
            )
        if not principal.permits(permission):
            return principal, JSONResponse(
                {"error": {"code": "FORBIDDEN", "message": "permission is required"}},
                status_code=403,
            )
        return principal, None

    @app.get("/v1/manual-holdings")
    def read_current(x_api_key: str | None = Header(default=None)):
        _, denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        items = repository.current()
        total_value = sum((item.current_value for item in items), Decimal("0"))
        total_basis = sum((item.cost_basis for item in items), Decimal("0"))
        return {
            "items": [item.document() for item in items],
            "position_count": len(items),
            "current_value": str(total_value),
            "cost_basis": str(total_basis),
            "gain_loss": str(total_value - total_basis),
            "authority_state": "MANUAL_USER_ENTERED_EXTERNAL_HOLDINGS",
        }

    @app.get("/v1/manual-holdings/history")
    def read_history(
        symbol: str,
        account_id: str,
        limit: int = 20,
        x_api_key: str | None = Header(default=None),
    ):
        _, denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        try:
            items = repository.history(symbol, account_id, limit)
        except ValueError as exc:
            return JSONResponse(
                {"error": {"code": "INVALID_LIMIT", "message": str(exc)}},
                status_code=422,
            )
        return {"items": [item.document() for item in items]}

    @app.post("/v1/manual-holdings")
    async def write(
        request: Request,
        x_api_key: str | None = Header(default=None),
        x_correlation_id: str | None = Header(default=None),
    ):
        correlation = x_correlation_id or str(uuid4())
        principal, denied = authorize(x_api_key, Permission.RUN_SUBMIT)
        if denied:
            denied.headers["X-Correlation-ID"] = correlation
            return denied
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise ValueError("body must be a JSON object")
            as_of = datetime.fromisoformat(str(body.get("as_of", "")).replace("Z", "+00:00"))
            if as_of.tzinfo is None:
                raise ValueError("as_of must include timezone")
            item = create_manual_holding_snapshot(
                symbol=str(body.get("symbol", "")),
                asset_name=str(body.get("asset_name", "")),
                asset_type=str(body.get("asset_type", "ETF")),
                account_id=str(body.get("account_id", "brokerage")),
                as_of=as_of,
                shares=Decimal(str(body.get("shares", ""))),
                cost_basis=Decimal(str(body.get("cost_basis", ""))),
                current_value=Decimal(str(body.get("current_value", ""))),
                recorded_by=principal.principal_id,
                notes=str(body.get("notes", "")),
            )
            persisted = repository.save(item)
        except (ValueError, InvalidOperation, KeyError) as exc:
            return JSONResponse(
                {"error": {"code": "MANUAL_HOLDING_INVALID", "message": str(exc)}},
                status_code=422,
                headers={"X-Correlation-ID": correlation},
            )
        if hasattr(app.state, "events"):
            app.state.events.record(
                OperationalEvent(
                    "MANUAL_HOLDING_RECORDED",
                    datetime.now(timezone.utc),
                    correlation,
                    {
                        "symbol": persisted.symbol,
                        "account_id": persisted.account_id,
                        "snapshot_id": persisted.snapshot_id,
                        "principal_id": principal.principal_id,
                    },
                )
            )
        return JSONResponse(
            {"snapshot": persisted.document()},
            status_code=201,
            headers={"X-Correlation-ID": correlation},
        )
