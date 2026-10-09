from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from foundation.production.live_security import LiveSecuritySettings, install_live_security


def application(settings):
    app = FastAPI()
    install_live_security(app, settings)
    @app.get("/ready")
    def ready():
        return {"ready": True}
    @app.post("/echo")
    async def echo():
        return {"accepted": True}
    return TestClient(app)


def test_environment_policy_rejects_unsafe_production_configuration():
    with pytest.raises(ValueError, match="HTTPS"):
        LiveSecuritySettings("production", ("*",), False)
    settings = LiveSecuritySettings.from_environment({
        "UIIP_ENVIRONMENT": "production", "UIIP_ALLOWED_HOSTS": "invest.example.com",
        "UIIP_REQUIRE_HTTPS": "true", "UIIP_MAX_REQUEST_BYTES": "4096",
    })
    assert settings.allowed_hosts == ("invest.example.com",) and settings.require_https


def test_unknown_hosts_and_insecure_transport_are_rejected():
    service = application(LiveSecuritySettings("staging", ("stage.example.com",), True))
    assert service.get("/ready", headers={"Host": "evil.example.com", "X-Forwarded-Proto": "https"}).status_code == 400
    response = service.get("/ready", headers={"Host": "stage.example.com"})
    assert response.status_code == 400 and response.json()["error"]["code"] == "HTTPS_REQUIRED"


def test_security_headers_are_applied_to_accepted_responses():
    service = application(LiveSecuritySettings("staging", ("stage.example.com",), True))
    response = service.get("/ready", headers={"Host": "stage.example.com", "X-Forwarded-Proto": "https"})
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["strict-transport-security"].startswith("max-age=")
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    # images only from the TCGplayer CDN (Secret Lair product images); nothing else widened
    assert "img-src 'self' https://tcgplayer-cdn.tcgplayer.com;" in response.headers["content-security-policy"]


def test_oversized_requests_are_rejected_before_handler_execution():
    service = application(LiveSecuritySettings("development", ("testserver",), False, 1024))
    response = service.post("/echo", content=b"x" * 1025)
    assert response.status_code == 413 and response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_a_bad_or_missing_length_cannot_slip_past_the_size_limit():
    service = application(LiveSecuritySettings("development", ("testserver",), False, 1024))
    response = service.post("/echo", content=b"{}", headers={"Content-Length": "abc"})
    assert response.status_code == 400 and response.json()["error"]["code"] == "BAD_CONTENT_LENGTH"
    chunks = (part for part in (b"x" * 600, b"x" * 600))
    response = service.post("/echo", content=chunks)          # a generator body is sent chunked, with no length
    assert response.status_code == 411 and response.json()["error"]["code"] == "LENGTH_REQUIRED"
    assert service.post("/echo", content=b"{}").status_code == 200
