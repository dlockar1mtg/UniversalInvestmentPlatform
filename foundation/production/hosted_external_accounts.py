"""Authenticated manual external account routes: Acorns snapshots and retirement statements.

GET  /v1/external-accounts/performance?account_id=acorns  history for one account (Acorns by default)
GET  /v1/external-accounts/summary                        every account: latest statements, paycheck schedule,
                                                          and today's estimate (statement + paychecks since)
POST /v1/external-accounts/performance                    record a snapshot (operator)
PUT  /v1/external-accounts/schedule                       set or clear an account's paycheck deposits (operator)

An account id is a kind ("acorns", "retirement-401k", "ira", "hsa", "pension") or "kind:name-slug" when a person
holds several accounts of one kind.
"""
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from fastapi import Header, Request
from fastapi.responses import JSONResponse
from .observability import OperationalEvent
from .security import APIKeyAuthenticator, Permission
from .external_account_performance import KINDS, create_snapshot, estimate, kind_of, monthly_equivalent, validate_schedule

AUTHORITY = "MANUAL_USER_ENTERED_EXTERNAL_ACCOUNT_PERFORMANCE"


def _account(value) -> str:
    account = str(value if value not in (None, "") else "acorns").strip().lower()
    kind_of(account)
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
    def record(name,correlation,payload):
        if hasattr(app.state,"events"): app.state.events.record(OperationalEvent(name,datetime.now(timezone.utc),correlation,payload))
    @app.get("/v1/external-accounts/performance")
    def read(limit:int=20,account_id:str="acorns",x_api_key:str|None=Header(default=None)):
        _,denied=authorize(x_api_key,Permission.RUN_READ)
        if denied:return denied
        try:
            account=_account(account_id); items=repository.history(account,limit)
        except ValueError as exc:return JSONResponse({"error":{"code":"INVALID_REQUEST","message":str(exc)}},status_code=422)
        label,category=KINDS[kind_of(account)]
        return {"account_id":account,"provider":"Acorns" if account=="acorns" else (items[0].provider if items else label),"account_label":label,
                "category":category,"items":[i.document() for i in items],"authority_state":AUTHORITY}
    @app.get("/v1/external-accounts/summary")
    def summary(limit:int=24,today:str|None=None,x_api_key:str|None=Header(default=None)):
        _,denied=authorize(x_api_key,Permission.RUN_READ)
        if denied:return denied
        try:
            day=date.fromisoformat(today) if today else datetime.now(timezone.utc).date()
            schedules=repository.schedules()
            ids=sorted(set(repository.accounts())|{"acorns"},key=lambda a:(list(KINDS).index(kind_of(a)),a))
            accounts=[]
            for a in ids:
                kind=kind_of(a); label,category=KINDS[kind]; items=repository.history(a,limit); sched=schedules.get(a)
                if not items and a!="acorns": continue
                accounts.append({"account_id":a,"account_kind":kind,"account_label":label,"category":category,
                                 "name":items[0].provider if items else label,"items":[i.document() for i in items],
                                 "schedule":None if not sched else {**sched,"monthly_equivalent":monthly_equivalent(sched["per_paycheck"],sched["every_days"])},
                                 "estimate":estimate(items[0],sched,day) if items else None})
        except ValueError as exc:return JSONResponse({"error":{"code":"INVALID_REQUEST","message":str(exc)}},status_code=422)
        retirement=[a for a in accounts if a["category"]=="retirement" and a["items"]]
        return {"as_of_date":day.isoformat(),"accounts":accounts,
                "retirement_value":str(sum((Decimal(a["estimate"]["value"]) for a in retirement),Decimal(0))),
                "retirement_statement_value":str(sum((Decimal(a["items"][0]["current_value"]) for a in retirement),Decimal(0))),
                "retirement_accounts_entered":len(retirement),"authority_state":AUTHORITY}
    @app.post("/v1/external-accounts/performance")
    async def write(request:Request,x_api_key:str|None=Header(default=None),x_correlation_id:str|None=Header(default=None)):
        correlation=x_correlation_id or str(uuid4()); principal,denied=authorize(x_api_key,Permission.RUN_SUBMIT)
        if denied: denied.headers["X-Correlation-ID"]=correlation; return denied
        try:
            body=await request.json()
            if not isinstance(body,dict): raise ValueError("body must be a JSON object")
            account=_account(body.get("account_id"))
            provider="Acorns" if account=="acorns" else (str(body.get("provider") or "").strip() or KINDS[kind_of(account)][0])
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
        record("EXTERNAL_ACCOUNT_PERFORMANCE_RECORDED",correlation,{"account_id":account,"snapshot_id":persisted.snapshot_id,"principal_id":principal.principal_id})
        return JSONResponse({"created":existed is None or existed.fingerprint!=persisted.fingerprint,"snapshot":persisted.document()},status_code=201,headers={"X-Correlation-ID":correlation})
    @app.put("/v1/external-accounts/schedule")
    async def schedule(request:Request,x_api_key:str|None=Header(default=None),x_correlation_id:str|None=Header(default=None)):
        correlation=x_correlation_id or str(uuid4()); principal,denied=authorize(x_api_key,Permission.RUN_SUBMIT)
        if denied: denied.headers["X-Correlation-ID"]=correlation; return denied
        try:
            body=await request.json()
            if not isinstance(body,dict): raise ValueError("body must be a JSON object")
            account=_account(body.get("account_id"))
            if KINDS[kind_of(account)][1]!="retirement": raise ValueError("paycheck deposits apply to retirement accounts only")
            if account not in repository.accounts(): raise ValueError("enter a statement for this account first")
            sched=None if body.get("clear") else validate_schedule(body.get("per_paycheck"),body.get("every_days",14),body.get("next_paycheck"))
            repository.save_schedule(account,sched,principal.principal_id)
        except (ValueError,InvalidOperation,TypeError) as exc:
            return JSONResponse({"error":{"code":"EXTERNAL_ACCOUNT_INVALID","message":str(exc)}},status_code=422,headers={"X-Correlation-ID":correlation})
        record("EXTERNAL_ACCOUNT_SCHEDULE_SET",correlation,{"account_id":account,"cleared":sched is None,"principal_id":principal.principal_id})
        return JSONResponse({"account_id":account,"schedule":sched},status_code=200,headers={"X-Correlation-ID":correlation})
