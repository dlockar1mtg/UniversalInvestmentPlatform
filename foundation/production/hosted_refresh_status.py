"""Authenticated refresh/data-health observability for the hosted UIP dashboard."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Mapping

from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

from foundation.production.security import APIKeyAuthenticator, Permission
from foundation.presentation.read_api import PresentationReadRepository

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "config" / "orchestration" / "r4_refresh_operations_registry.json"


def _load_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))


def _cron_value_matches(value: int, expression: str) -> bool:
    expression = expression.strip()
    if expression == "*":
        return True
    if "-" in expression:
        start, end = expression.split("-", 1)
        return int(start) <= value <= int(end)
    return value == int(expression)


def _next_cron_after(expression: str, now: datetime) -> datetime:
    parts = expression.split()
    if len(parts) != 5:
        raise ValueError(f"Unsupported cron expression: {expression}")
    minute_expr, hour_expr, dom_expr, month_expr, dow_expr = parts
    if dom_expr != "*" or month_expr != "*":
        raise ValueError(f"Unsupported cron day/month expression: {expression}")
    candidate = now.astimezone(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1)
    limit = candidate + timedelta(days=8)
    while candidate <= limit:
        cron_dow = (candidate.weekday() + 1) % 7
        if (
            _cron_value_matches(candidate.minute, minute_expr)
            and _cron_value_matches(candidate.hour, hour_expr)
            and _cron_value_matches(cron_dow, dow_expr)
        ):
            return candidate
        candidate += timedelta(minutes=1)
    raise ValueError(f"Unable to resolve next schedule for {expression}")


def _domain_schedule(domain_id: str, config: dict, now: datetime) -> dict:
    schedules: list[dict] = []
    daily = config.get("daily_schedule_utc")
    if daily:
        schedules.append({
            "kind": "daily",
            "mode": config.get("daily_mode"),
            "cron_utc": daily,
            "next_run_utc": _next_cron_after(str(daily), now).isoformat(),
        })
    weekly = config.get("weekly_full_refresh_schedule_utc")
    if weekly:
        schedules.append({
            "kind": "weekly_full",
            "mode": config.get("weekly_mode"),
            "cron_utc": weekly,
            "next_run_utc": _next_cron_after(str(weekly), now).isoformat(),
        })
    schedules.sort(key=lambda item: item["next_run_utc"])
    return {
        "domain_id": domain_id,
        "schedules": schedules,
        "next_scheduled_run_utc": schedules[0]["next_run_utc"] if schedules else None,
    }


def _age_days(value: object, now: datetime) -> int | None:
    if value in (None, ""):
        return None
    text = str(value)
    try:
        if len(text) == 10:
            observed = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        else:
            observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
        return max(0, int((now - observed.astimezone(timezone.utc)).total_seconds() // 86400))
    except ValueError:
        return None


def build_refresh_status(repository: PresentationReadRepository, *, now: datetime | None = None) -> dict:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    registry = _load_registry()
    health_by_domain = {str(item["domain_id"]): dict(item) for item in repository.domain_health()}
    items = []

    for domain_id, config in sorted(registry["domains"].items()):
        health = health_by_domain.get(domain_id, {})
        healthy = (
            health.get("certification_state") == "CERTIFIED"
            and health.get("import_registry_status") == "ACTIVE"
            and health.get("last_import_status") == "IMPORTED"
            and int(health.get("warning_count") or 0) == 0
            and int(health.get("error_count") or 0) == 0
        )
        schedule = _domain_schedule(domain_id, config, now)
        warnings = int(health.get("warning_count") or 0)
        errors = int(health.get("error_count") or 0)
        failure_summary = None
        if errors or warnings:
            failure_summary = str(health.get("status_message") or f"{errors} errors · {warnings} warnings")

        workflow = (
            config.get("workflow")
            or config.get("daily_workflow")
            or ""
        )
        items.append({
            "domain_id": domain_id,
            "health_state": "HEALTHY" if healthy else "REVIEW",
            "certification_state": health.get("certification_state"),
            "import_registry_status": health.get("import_registry_status"),
            "last_import_status": health.get("last_import_status"),
            "last_success_at_utc": health.get("last_imported_at_utc"),
            "last_run_id": health.get("last_run_id"),
            "last_import_id": health.get("last_import_id"),
            "data_as_of": health.get("last_data_as_of_date"),
            "data_age_days": _age_days(health.get("last_data_as_of_date"), now),
            "artifact_or_package_reference": health.get("last_package_id"),
            "authority_version": (
                health.get("contract_version")
                or health.get("platform_version")
                or health.get("registry_version")
            ),
            "workflow_name": Path(str(workflow)).name if workflow else None,
            "next_scheduled_run_utc": schedule["next_scheduled_run_utc"],
            "schedules": schedule["schedules"],
            "failure_summary": failure_summary,
            "last_good_state_status": "ACTIVE_CERTIFIED_STATE_PRESERVED" if healthy else "LAST_GOOD_STATE_REMAINS_ACTIVE",
            "recommendations_usable": bool(healthy),
            "warning_count": warnings,
            "error_count": errors,
            "status_message": health.get("status_message"),
            "refresh_request_available": False,
            "refresh_request_state": "SOURCE_OWNED_DISPATCH_NOT_YET_EXPOSED_IN_HOSTED_UI",
        })

    return {
        "generated_at_utc": now.isoformat(),
        "status": "HEALTHY" if items and all(item["health_state"] == "HEALTHY" for item in items) else "REVIEW",
        "items": items,
        "lifecycle": [
            "Requested",
            "Source Refresh",
            "Certification",
            "UIP Import",
            "Activation",
            "Complete",
        ],
        "refresh_execution_owner": "GITHUB_ACTIONS_SOURCE_OWNED",
        "refresh_is_model_retraining": False,
        "failed_cycle_preserves_last_good_certified_state": True,
        "manual_dispatch_available": False,
    }


def install_refresh_status_routes(
    app: FastAPI,
    credentials: Mapping[str, tuple[str, tuple[str, ...]]],
    repository: PresentationReadRepository,
) -> None:
    principals, hashes = {}, {}
    for principal_id, (credential, roles) in sorted(credentials.items()):
        principals[principal_id] = roles
        hashes[principal_id] = APIKeyAuthenticator.hash_credential(credential)
    authenticator = APIKeyAuthenticator(principals, hashes)

    def authorize(credential: str | None):
        principal = authenticator.authenticate(credential)
        if principal is None:
            return JSONResponse(
                {"error": {"code": "UNAUTHENTICATED", "message": "valid credentials are required"}},
                status_code=401,
            )
        if not principal.permits(Permission.RUN_READ):
            return JSONResponse(
                {"error": {"code": "FORBIDDEN", "message": "read permission is required"}},
                status_code=403,
            )
        return None

    @app.get("/v1/refresh/status")
    def refresh_status(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key)
        return denied or build_refresh_status(repository)
