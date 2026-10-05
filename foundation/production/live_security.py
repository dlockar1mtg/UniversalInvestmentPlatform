"""Production HTTP hardening with explicit environment policy."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping

from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass(frozen=True)
class LiveSecuritySettings:
    environment: str = "development"
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost", "testserver")
    require_https: bool = False
    maximum_request_bytes: int = 1_048_576

    def __post_init__(self) -> None:
        if self.environment not in {"development", "staging", "production"}:
            raise ValueError("environment must be development, staging, or production")
        normalized = tuple(sorted({host.strip().lower() for host in self.allowed_hosts if host.strip()}))
        if not normalized or self.maximum_request_bytes < 1024:
            raise ValueError("allowed hosts and a safe request limit are required")
        if self.environment == "production" and ("*" in normalized or not self.require_https):
            raise ValueError("production requires explicit hosts and HTTPS")
        object.__setattr__(self, "allowed_hosts", normalized)

    @classmethod
    def from_environment(cls, values: Mapping[str, str] = os.environ) -> "LiveSecuritySettings":
        environment = values.get("UIIP_ENVIRONMENT", "development").lower()
        hosts = tuple(values.get("UIIP_ALLOWED_HOSTS", "127.0.0.1,localhost,testserver").split(","))
        https = values.get("UIIP_REQUIRE_HTTPS", "false").lower() in {"1", "true", "yes"}
        maximum = int(values.get("UIIP_MAX_REQUEST_BYTES", "1048576"))
        return cls(environment, hosts, https, maximum)


def install_live_security(app, settings: LiveSecuritySettings) -> None:
    @app.middleware("http")
    async def enforce_live_security(request: Request, call_next):
        host = request.headers.get("host", "").split(":", 1)[0].lower()
        if host not in settings.allowed_hosts:
            return JSONResponse({"error": {"code": "HOST_REJECTED", "message": "request host is not permitted"}}, status_code=400)
        forwarded = request.headers.get("x-forwarded-proto", "").lower()
        if settings.require_https and request.url.scheme != "https" and forwarded != "https":
            return JSONResponse({"error": {"code": "HTTPS_REQUIRED", "message": "secure transport is required"}}, status_code=400)
        length = request.headers.get("content-length")
        if length and int(length) > settings.maximum_request_bytes:
            return JSONResponse({"error": {"code": "REQUEST_TOO_LARGE", "message": "request exceeds the permitted size"}}, status_code=413)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self'; img-src 'self' https://tcgplayer-cdn.tcgplayer.com; script-src 'self'; object-src 'none'; frame-ancestors 'none'"
        response.headers["Cache-Control"] = "no-store"
        if settings.require_https:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
