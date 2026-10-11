"""Authenticated net-worth routes.

GET  /v1/net-worth          today's net worth (investments, retirement, bank, house fund, home equity) and every
                            month kept so far; refreshes this month's row when it is over 6 hours old
POST /v1/net-worth/capture  store this month's row now (operator)

The daily free-staging cycle also captures (job type net_worth_snapshot), so a month is kept even when nobody opens
the dashboard.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Header
from fastapi.responses import JSONResponse

from .net_worth import capture, compute_net_worth
from .security import APIKeyAuthenticator, Permission

STALE_AFTER = timedelta(hours=6)


def install_net_worth_routes(app, settings, history, **sources) -> None:
    principals, hashes = {}, {}
    for pid, (cred, roles) in sorted(settings.credentials.items()):
        principals[pid] = roles
        hashes[pid] = APIKeyAuthenticator.hash_credential(cred)
    auth = APIKeyAuthenticator(principals, hashes)

    def authorize(key, permission):
        principal = auth.authenticate(key)
        if principal is None:
            return JSONResponse({"error": {"code": "UNAUTHENTICATED", "message": "valid credentials are required"}}, status_code=401)
        if not principal.permits(permission):
            return JSONResponse({"error": {"code": "FORBIDDEN", "message": "permission is required"}}, status_code=403)
        return None

    @app.get("/v1/net-worth")
    def read(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        now = datetime.now(timezone.utc)
        months = history.months()
        this_month = now.strftime("%Y-%m")
        row = next((m for m in months if m["month"] == this_month), None)
        fresh = row is not None and now - datetime.fromisoformat(row["captured_at"]) < STALE_AFTER
        if fresh:
            current = compute_net_worth(**sources)
        else:                                   # keep the history moving whenever the dashboard is opened
            current = capture(history, **sources)["snapshot"]
            months = history.months()
        return {"current": current, "months": months, "authority_state": "DERIVED_FROM_UIP_HOLDINGS_STATEMENTS_AND_PLAN"}

    @app.post("/v1/net-worth/capture")
    def write(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key, Permission.RUN_SUBMIT)
        if denied:
            return denied
        return capture(history, **sources)
