"""Authenticated manual external account performance routes."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Mapping
from uuid import uuid4
from fastapi import Header, Request
from fastapi.responses import JSONResponse
from .http_service import HTTPServiceSettings
from .observability import OperationalEvent
from .security import APIKeyAuthenticator, Permission
from .external_account_performance import create_snapshot

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
    def read(limit:int=20,x_api_key:str|None=Header(default=None)):
        _,denied=authorize(x_api_key,Permission.RUN_READ)
        if denied:return denied
        try: items=repository.history("acorns",limit)
        except ValueError as exc:return JSONResponse({"error":{"code":"INVALID_LIMIT","message":str(exc)}},status_code=422)
        return {"account_id":"acorns","provider":"Acorns","items":[i.document() for i in items],"authority_state":"MANUAL_USER_ENTERED_EXTERNAL_ACCOUNT_PERFORMANCE"}
    @app.post("/v1/external-accounts/performance")
    async def write(request:Request,x_api_key:str|None=Header(default=None),x_correlation_id:str|None=Header(default=None)):
        correlation=x_correlation_id or str(uuid4()); principal,denied=authorize(x_api_key,Permission.RUN_SUBMIT)
        if denied: denied.headers["X-Correlation-ID"]=correlation; return denied
        try:
            body=await request.json()
            if not isinstance(body,dict): raise ValueError("body must be a JSON object")
            if str(body.get("account_id","acorns")).strip().lower()!="acorns": raise ValueError("only account_id=acorns is supported")
            as_of=datetime.fromisoformat(str(body.get("as_of","")).replace("Z","+00:00"))
            if as_of.tzinfo is None: raise ValueError("as_of must include timezone")
            current=Decimal(str(body.get("current_value",""))); basis=Decimal(str(body.get("contributed_basis","")))
            item=create_snapshot(account_id="acorns",provider="Acorns",as_of=as_of,current_value=current,contributed_basis=basis,recorded_by=principal.principal_id,notes=str(body.get("notes","")).strip())
            existed=repository.latest("acorns")
            persisted=repository.save(item)
        except (ValueError,InvalidOperation,KeyError) as exc:
            return JSONResponse({"error":{"code":"EXTERNAL_ACCOUNT_INVALID","message":str(exc)}},status_code=422,headers={"X-Correlation-ID":correlation})
        if hasattr(app.state,"events"): app.state.events.record(OperationalEvent("EXTERNAL_ACCOUNT_PERFORMANCE_RECORDED",datetime.now(timezone.utc),correlation,{"account_id":"acorns","snapshot_id":persisted.snapshot_id,"principal_id":principal.principal_id}))
        return JSONResponse({"created":existed is None or existed.fingerprint!=persisted.fingerprint,"snapshot":persisted.document()},status_code=201,headers={"X-Correlation-ID":correlation})
