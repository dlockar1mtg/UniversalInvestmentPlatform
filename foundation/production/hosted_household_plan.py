"""Authenticated routes for the household plan (the Homestead page).

GET  /v1/household-plan                    the current plan and its rolled-forward months
POST /v1/household-plan                    save a new version (operator)
POST /v1/household-plan/import             preview a workbook import (operator; saves nothing)
POST /v1/household-plan/projection         the house ranges, with live holdings
POST /v1/household-plan/retirement-path    the early-retirement path, with live holdings and retirement statements
POST /v1/household-plan/home               owner mode: value, loan, equity, PMI, refinance and payment checks
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Header, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .household_plan import HouseholdPlanError, create_version, import_workbook, normalize_plan, roll_forward
from .household_projection import project
from .retirement_path import retirement_path
from .home_owner import home_status
from .observability import OperationalEvent
from .security import APIKeyAuthenticator, Permission

MAX_WORKBOOK_BYTES = 5 * 1024 * 1024


def install_household_plan_routes(app, settings, repository):
    principals, hashes = {}, {}
    for pid, (credential, roles) in sorted(settings.credentials.items()):
        principals[pid] = roles
        hashes[pid] = APIKeyAuthenticator.hash_credential(credential)
    auth = APIKeyAuthenticator(principals, hashes)
    app.state.household_plan_repository = repository

    def authorize(key, permission):
        principal = auth.authenticate(key)
        if principal is None:
            return None, JSONResponse({"error": {"code": "UNAUTHENTICATED", "message": "valid credentials are required"}}, status_code=401)
        if not principal.permits(permission):
            return principal, JSONResponse({"error": {"code": "FORBIDDEN", "message": "permission is required"}}, status_code=403)
        return principal, None

    def invalid(exc, correlation=None):
        headers = {"X-Correlation-ID": correlation} if correlation else None
        return JSONResponse({"error": {"code": "HOUSEHOLD_PLAN_INVALID", "message": str(exc)}}, status_code=422, headers=headers)

    def record(kind, correlation, detail):
        if hasattr(app.state, "events"):
            app.state.events.record(OperationalEvent(kind, datetime.now(timezone.utc), correlation, detail))

    @app.get("/v1/household-plan")
    def read_plan(x_api_key: str | None = Header(default=None)):
        _, denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        current = repository.current()
        if current is None:
            return {"available": False}
        return {"available": True, "version": current.summary(), "plan": current.plan, "rows": roll_forward(current.plan),
                "history": [v.summary() for v in repository.history(10)]}

    @app.post("/v1/household-plan")
    async def save_plan(request: Request, x_api_key: str | None = Header(default=None),
                        x_correlation_id: str | None = Header(default=None)):
        correlation = x_correlation_id or str(uuid4())
        principal, denied = authorize(x_api_key, Permission.RUN_SUBMIT)
        if denied:
            return denied
        try:
            body = await request.json()
            plan = body.get("plan") if isinstance(body, dict) else None
            version = repository.save(create_version(plan, principal.principal_id))
        except (HouseholdPlanError, ValueError) as exc:
            return invalid(exc, correlation)
        record("HOUSEHOLD_PLAN_SAVED", correlation, {"version_id": version.version_id, "principal_id": principal.principal_id})
        return JSONResponse({"version": version.summary(), "plan": version.plan, "rows": roll_forward(version.plan)},
                            status_code=201, headers={"X-Correlation-ID": correlation})

    @app.post("/v1/household-plan/import")
    async def preview_import(request: Request, x_api_key: str | None = Header(default=None)):
        """Read an uploaded workbook into a plan for review. Nothing is saved until the plan is posted."""
        _, denied = authorize(x_api_key, Permission.RUN_SUBMIT)
        if denied:
            return denied
        data = await request.body()
        if not data:
            return invalid("choose the workbook file to import")
        if len(data) > MAX_WORKBOOK_BYTES:
            return invalid("the workbook is larger than 5 MB")
        try:
            plan = import_workbook(data)
        except HouseholdPlanError as exc:
            return invalid(exc)
        return {"plan": plan, "rows": roll_forward(plan), "source": plan["source"], "saved": False}

    @app.post("/v1/household-plan/projection")
    async def projection(request: Request, x_api_key: str | None = Header(default=None)):
        _, denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        current = repository.current()
        if current is None:
            return {"available": False}
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - an empty body means no live holdings
            body = {}
        body = body if isinstance(body, dict) else {}
        plan = current.plan
        if isinstance(body.get("settings"), dict):           # try a setting without saving it
            try:
                plan = normalize_plan({**plan, "settings": {**plan["settings"], **body["settings"]}})
            except HouseholdPlanError as exc:
                return invalid(exc)
        month = str(body.get("as_of_month") or datetime.now(timezone.utc).strftime("%Y-%m"))
        holdings = body.get("holdings") if isinstance(body.get("holdings"), dict) else None
        try:
            result = project(plan, as_of_month=month, holdings=holdings)
        except ValueError as exc:
            return invalid(exc)
        return {"available": True, "version": current.summary(), **result}

    @app.post("/v1/household-plan/retirement-path")
    async def retirement(request: Request, x_api_key: str | None = Header(default=None)):
        _, denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        current = repository.current()
        if current is None:
            return {"available": False}
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001 - an empty body means no live figures
            body = {}
        body = body if isinstance(body, dict) else {}
        plan = current.plan
        if isinstance(body.get("retirement"), dict):          # try retirement inputs without saving them
            try:
                plan = normalize_plan({**plan, "settings": {**plan["settings"], "retirement": body["retirement"]}})
            except HouseholdPlanError as exc:
                return invalid(exc)
        month = str(body.get("as_of_month") or datetime.now(timezone.utc).strftime("%Y-%m"))
        holdings = body.get("holdings") if isinstance(body.get("holdings"), dict) else None
        deposits = body.get("deposits") if isinstance(body.get("deposits"), dict) else None
        try:
            start = float(body.get("retirement_start") or 0)
            monthly = float(body.get("retirement_monthly") or 0)
            home_value = float(body["home_value"]) if body.get("home_value") else None
            result = await run_in_threadpool(          # a few seconds of simulation; keep the server answering
                lambda: retirement_path(plan, as_of_month=month, holdings=holdings, retirement_start=start,
                                        retirement_monthly=monthly, deposits=deposits, home_value=home_value))
        except (TypeError, ValueError) as exc:
            return invalid(exc)
        return {"available": True, "version": current.summary(), **result}

    @app.post("/v1/household-plan/home")
    async def owned_home(request: Request, x_api_key: str | None = Header(default=None)):
        _, denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        current = repository.current()
        if current is None:
            return {"available": False}
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            body = {}
        body = body if isinstance(body, dict) else {}
        plan = current.plan
        if isinstance(body.get("home"), dict):                # preview a purchase without saving it
            try:
                plan = normalize_plan({**plan, "settings": {**plan["settings"], "home": body["home"]}})
            except HouseholdPlanError as exc:
                return invalid(exc)
        home = plan["settings"].get("home")
        if not home:
            return {"available": True, "owned": False}
        month = str(body.get("as_of_month") or datetime.now(timezone.utc).strftime("%Y-%m"))
        r = plan["settings"].get("retirement")
        keep_until = None
        if r and r.get("sell_home_at_retirement"):
            k = int(r["age_as_of"][:4]) * 12 + int(r["age_as_of"][5:7]) - 1 + (r["retire_age"] - r["age"]) * 12
            keep_until = f"{k // 12}-{k % 12 + 1:02d}"
        try:
            hpi = float(body["hpi_now"]) if body.get("hpi_now") else None
            rate = float(body["rate_now"]) if body.get("rate_now") else None
            status = home_status(home, as_of_month=max(month, home["closing_month"]), hpi_now=hpi, rate_now=rate, keep_until=keep_until)
        except (TypeError, ValueError) as exc:
            return invalid(exc)
        return {"available": True, "owned": True, "preview": isinstance(body.get("home"), dict), "home": home, **status}
