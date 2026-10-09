"""Authenticated manual external account routes: Acorns snapshots and retirement statements.

GET  /v1/external-accounts/performance?account_id=acorns  history for one account (Acorns by default)
GET  /v1/external-accounts/summary                        latest snapshot and history for every account
POST /v1/external-accounts/performance                    record a snapshot (operator)
"""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from fastapi import Header, Request
from fastapi.responses import JSONResponse
from .observability import OperationalEvent
from .security import APIKeyAuthenticator, Permission
from .external_account_performance import ACCOUNTS, create_snapshot

AUTHORITY = "MANUAL_USER_ENTERED_EXTERNAL_ACCOUNT_PERFORMANCE"


def _account(value) -> str:
    account = str(value if value not in (None, "") else "acorns").strip().lower()
    if account not in ACCOUNTS:
        raise ValueError(f"account_id must be one of: {', '.join(ACCOUNTS)}")
    return account


def install_external_account_performance_routes(app, settings, repository):
    principals, hashes = {}, {}
    for pid,(cred,roles) in sorted(settings.credentials.items()): principals[pid]=roles; hashes[pid]=APIKeyAuthenticator.hash_credential(cred)
    auth=APIKeyAuthenticator(principals,hashes); app.state.external_account_performance_repository=repository
    def authorize(key,permission):
        p=auth.authenticate(key)
        if p is None:return None,JSONResponse({"error":{"code":"UNAUTHENTICATED","message":"valid credentials are required"}},status_code=401)
        if not p.permits(permission):return p,JSONResponse({"error":{"code":"FORBIDDEN","message":"permission is required"}},status_code=403)
        return p,None
    @app.get("/v1/external-accounts/performance")
    def read(limit:int=20,account_id:str="acorns",x_api_key:str|None=Header(default=None)):
        _,denied=authorize(x_api_key,Permission.RUN_READ)
        if denied:return denied
        try:
            account=_account(account_id); items=repository.history(account,limit)
        except ValueError as exc:return JSONResponse({"error":{"code":"INVALID_REQUEST","message":str(exc)}},status_code=422)
        label,category=ACCOUNTS[account]
        return {"account_id":account,"provider":"Acorns" if account=="acorns" else (items[0].provider if items else label),"account_label":label,
                "category":category,"items":[i.document() for i in items],"authority_state":AUTHORITY}
    @app.get("/v1/external-accounts/summary")
    def summary(limit:int=24,x_api_key:str|None=Header(default=None)):
        _,denied=authorize(x_api_key,Permission.RUN_READ)
        if denied:return denied
        try: accounts=[{"account_id":a,"account_label":label,"category":category,"items":[i.document() for i in repository.history(a,limit)]}
                       for a,(label,category) in ACCOUNTS.items()]
        except ValueError as exc:return JSONResponse({"error":{"code":"INVALID_LIMIT","message":str(exc)}},status_code=422)
        latest=[a["items"][0] for a in accounts if a["items"]]
        retirement=[i for i in latest if i["category"]=="retirement"]
        return {"accounts":accounts,"retirement_value":str(sum((Decimal(i["current_value"]) for i in retirement),Decimal(0))),
                "retirement_accounts_entered":len(retirement),"authority_state":AUTHORITY}
    @app.post("/v1/external-accounts/performance")
    async def write(request:Request,x_api_key:str|None=Header(default=None),x_correlation_id:str|None=Header(default=None)):
        correlation=x_correlation_id or str(uuid4()); principal,denied=authorize(x_api_key,Permission.RUN_SUBMIT)
        if denied: denied.headers["X-Correlation-ID"]=correlation; return denied
        try:
            body=await request.json()
            if not isinstance(body,dict): raise ValueError("body must be a JSON object")
            account=_account(body.get("account_id"))
            provider="Acorns" if account=="acorns" else (str(body.get("provider") or "").strip() or ACCOUNTS[account][0])
            as_of=datetime.fromisoformat(str(body.get("as_of","")).replace("Z","+00:00"))
            if as_of.tzinfo is None: raise ValueError("as_of must include timezone")
            current=Decimal(str(body.get("current_value","")))
            raw_basis=body.get("contributed_basis")
            if raw_basis in (None,"") and account!="acorns": raw_basis="0"
            basis=Decimal(str(raw_basis if raw_basis is not None else ""))
            if not current.is_finite() or not basis.is_finite(): raise ValueError("values must be finite numbers")
            item=create_snapshot(account_id=account,provider=provider,as_of=as_of,current_value=current,contributed_basis=basis,recorded_by=principal.principal_id,notes=str(body.get("notes","")).strip()[:500])
            existed=repository.latest(account)
            persisted=repository.save(item)
        except (ValueError,InvalidOperation,KeyError) as exc:
            return JSONResponse({"error":{"code":"EXTERNAL_ACCOUNT_INVALID","message":str(exc)}},status_code=422,headers={"X-Correlation-ID":correlation})
        if hasattr(app.state,"events"): app.state.events.record(OperationalEvent("EXTERNAL_ACCOUNT_PERFORMANCE_RECORDED",datetime.now(timezone.utc),correlation,{"account_id":account,"snapshot_id":persisted.snapshot_id,"principal_id":principal.principal_id}))
        return JSONResponse({"created":existed is None or existed.fingerprint!=persisted.fingerprint,"snapshot":persisted.document()},status_code=201,headers={"X-Correlation-ID":correlation})
