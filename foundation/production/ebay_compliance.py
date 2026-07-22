"""eBay marketplace account-deletion compliance endpoint.

The endpoint supports eBay's verification challenge and acknowledges account
closure/deletion notifications without exposing the verification secret.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
from typing import Any, Mapping

from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse


DEFAULT_PATH = "/api/compliance/ebay/account-deletion"


@dataclass(frozen=True)
class EbayComplianceSettings:
    """Environment-backed eBay compliance configuration."""

    verification_token: str
    endpoint_url: str

    @classmethod
    def from_environment(
        cls,
        values: Mapping[str, str] = os.environ,
    ) -> "EbayComplianceSettings":
        token = values.get("EBAY_DELETION_VERIFICATION_TOKEN", "").strip()
        endpoint_url = values.get("EBAY_DELETION_ENDPOINT_URL", "").strip()
        if not token:
            raise ValueError("EBAY_DELETION_VERIFICATION_TOKEN is required")
        if not 32 <= len(token) <= 80:
            raise ValueError("eBay verification token must be 32 to 80 characters")
        if not all(character.isalnum() or character in "_-" for character in token):
            raise ValueError("eBay verification token contains unsupported characters")
        if not endpoint_url.startswith("https://"):
            raise ValueError("EBAY_DELETION_ENDPOINT_URL must use HTTPS")
        return cls(token, endpoint_url)

    def challenge_response(self, challenge_code: str) -> str:
        payload = f"{challenge_code}{self.verification_token}{self.endpoint_url}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _notification_summary(payload: Any) -> dict[str, Any]:
    """Return a minimal, privacy-conscious acknowledgement summary."""

    if not isinstance(payload, dict):
        return {"received": True, "notification_type": "unknown"}
    metadata = payload.get("metadata")
    notification_type = None
    if isinstance(metadata, dict):
        notification_type = metadata.get("topic") or metadata.get("schemaVersion")
    return {
        "received": True,
        "notification_type": str(notification_type or "marketplace_account_deletion"),
    }


def install_ebay_compliance_routes(
    app: FastAPI,
    settings: EbayComplianceSettings,
    *,
    path: str = DEFAULT_PATH,
) -> None:
    """Install public eBay challenge and notification routes."""

    @app.get(path, include_in_schema=False)
    def verify(challenge_code: str = Query(..., min_length=1)):
        return {"challengeResponse": settings.challenge_response(challenge_code)}

    @app.post(path, include_in_schema=False)
    async def receive_notification(request: Request):
        try:
            payload = await request.json()
        except Exception:
            payload = None
        return JSONResponse(_notification_summary(payload), status_code=200)


def constant_time_equal(left: str, right: str) -> bool:
    """Exposed for future signature validation without timing leaks."""

    return hmac.compare_digest(left, right)
