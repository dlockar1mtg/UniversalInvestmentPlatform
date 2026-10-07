"""Authenticated routes for the household plan (the Homestead page)."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Header, Request
from fastapi.responses import JSONResponse

from .household_plan import HouseholdPlanError, create_version, import_workbook, normalize_plan, roll_forward
from .household_projection import project
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
