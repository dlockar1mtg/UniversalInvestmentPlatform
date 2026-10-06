"""Authenticated routes for manual stock and ETF holding snapshots."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from fastapi import Header, Request
from fastapi.responses import JSONResponse

from .manual_holdings import create_manual_holding_snapshot
from .observability import OperationalEvent
from .security import APIKeyAuthenticator, Permission


def mark_to_market(documents, prices):
    """Value ETF snapshots at the latest package close (shares x close), keeping the entered snapshot.

    Holdings without a usable close keep their manually entered value. The entered value stays
    available as snapshot_current_value; nothing is written back to the stored snapshot.
    """
    marked = []
    for doc in documents:
        doc = dict(doc)
        price = prices.get(str(doc.get("symbol", "")).upper()) if doc.get("asset_type") == "ETF" else None
        doc["snapshot_current_value"] = doc["current_value"]
        doc["snapshot_current_price"] = doc.get("current_price")
        if price is None:
            doc.update({"valuation_source": "MANUAL_SNAPSHOT", "valuation_as_of": doc.get("as_of")})
            marked.append(doc)
            continue
        shares, basis = Decimal(doc["shares"]), Decimal(doc["cost_basis"])
        close = Decimal(str(price["close"]))
        value = (shares * close).quantize(Decimal("0.01"))
        gain = value - basis
        doc.update({
            "current_value": str(value), "current_price": str(close), "gain_loss": str(gain),
            "return_pct": None if basis == 0 else str(gain / basis * Decimal(100)),
            "valuation_source": "ETF_PACKAGE_CLOSE", "valuation_as_of": price.get("as_of_date"),
            "valuation_quality": price.get("quality_status"), "valuation_freshness": price.get("freshness_state"),
            "valuation_package_id": price.get("package_id"),
        })
        marked.append(doc)
    return marked


def install_manual_holding_routes(app, settings, repository, market_prices=None):
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
        try:
            prices = market_prices() if market_prices is not None else {}
        except Exception:
            prices = {}                                    # pricing is best-effort; snapshots still serve
        documents = mark_to_market([item.document() for item in items], prices or {})
        total_value = sum((Decimal(doc["current_value"]) for doc in documents), Decimal("0"))
        total_basis = sum((item.cost_basis for item in items), Decimal("0"))
        marked = [doc for doc in documents if doc["valuation_source"] == "ETF_PACKAGE_CLOSE"]
        return {
            "items": documents,
            "position_count": len(items),
            "current_value": str(total_value),
            "snapshot_current_value": str(sum((item.current_value for item in items), Decimal("0"))),
            "cost_basis": str(total_basis),
            "gain_loss": str(total_value - total_basis),
            "marked_position_count": len(marked),
            "valuation_as_of": max((doc["valuation_as_of"] for doc in marked if doc.get("valuation_as_of")), default=None),
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
