"""Download my data: everything you have entered into the UIP, in one JSON file you keep.

GET /v1/my-data/export (read permission) returns, as an attachment:
  transactions        every certified buy and sell in the ledger
  manual_holdings     the current stock and ETF snapshots, each with its history
  external_accounts   Acorns and retirement statements, and the paycheck schedules
  household_plan      the current plan, and the list of saved versions
  net_worth_months    the month-by-month net-worth history

Market data is not included: the packages republish it every day. The file is the owner's own record, so the
UIP never writes it anywhere else.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import Header
from fastapi.responses import JSONResponse, Response

from .security import APIKeyAuthenticator, Permission

FORMAT = "uip-my-data-1"
PAGE = 500


def _transactions(repo) -> list:
    out, offset = [], 0
    while True:
        page = repo.list(limit=PAGE, offset=offset)
        out.extend(dict(t.document()) for t in page)
        if len(page) < PAGE:
            return out
        offset += PAGE


def build_export(*, transactions=None, manual=None, external=None, plans=None, history=None, now=None) -> dict:
    now = now or datetime.now(timezone.utc)
    doc: dict = {"format": FORMAT, "exported_at": now.isoformat(), "notes": []}
    doc["transactions"] = _transactions(transactions) if transactions is not None else None
    if manual is not None:
        holdings = []
        for item in manual.current():
            past = manual.history(item.symbol, item.account_id, 100)
            holdings.append({"current": item.document(), "history": [h.document() for h in past]})
        doc["manual_holdings"] = holdings
    else:
        doc["manual_holdings"] = None
    if external is not None:
        accounts = sorted(set(external.accounts()) | {"acorns"})
        doc["external_accounts"] = {
            "accounts": {a: [i.document() for i in external.history(a, 100)] for a in accounts},
            "schedules": external.schedules(),
        }
    else:
        doc["external_accounts"] = None
    if plans is not None:
        current = plans.current()
        doc["household_plan"] = {
            "current": None if current is None else {**current.summary(), "plan": current.plan},
            "versions": [v.summary() for v in plans.history(100)],
        }
    else:
        doc["household_plan"] = None
    doc["net_worth_months"] = history.months() if history is not None else None
    doc["notes"] = [k for k in ("transactions", "manual_holdings", "external_accounts", "household_plan", "net_worth_months")
                    if doc[k] is None]
    return doc


def install_data_export_routes(app, settings, **sources) -> None:
    principals, hashes = {}, {}
    for pid, (cred, roles) in sorted(settings.credentials.items()):
        principals[pid] = roles
        hashes[pid] = APIKeyAuthenticator.hash_credential(cred)
    auth = APIKeyAuthenticator(principals, hashes)

    @app.get("/v1/my-data/export")
    def export(x_api_key: str | None = Header(default=None)):
        principal = auth.authenticate(x_api_key)
        if principal is None:
            return JSONResponse({"error": {"code": "UNAUTHENTICATED", "message": "valid credentials are required"}}, status_code=401)
        if not principal.permits(Permission.RUN_READ):
            return JSONResponse({"error": {"code": "FORBIDDEN", "message": "permission is required"}}, status_code=403)
        doc = build_export(**sources)
        name = f"uip-my-data-{doc['exported_at'][:10]}.json"
        body = json.dumps(doc, indent=1, sort_keys=True, default=str)
        return Response(body, media_type="application/json",
                        headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})
