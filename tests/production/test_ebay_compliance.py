from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from foundation.production.ebay_compliance import (
    EbayComplianceSettings,
    install_ebay_compliance_routes,
)


ENDPOINT = "https://uiip-free-staging.onrender.com/api/compliance/ebay/account-deletion"
TOKEN = "A" * 64


def build_client() -> tuple[TestClient, EbayComplianceSettings]:
    settings = EbayComplianceSettings(TOKEN, ENDPOINT)
    app = FastAPI()
    install_ebay_compliance_routes(app, settings)
    return TestClient(app), settings


def test_settings_validate_environment() -> None:
    settings = EbayComplianceSettings.from_environment(
        {
            "EBAY_DELETION_VERIFICATION_TOKEN": TOKEN,
            "EBAY_DELETION_ENDPOINT_URL": ENDPOINT,
        }
    )
    assert settings.verification_token == TOKEN
    assert settings.endpoint_url == ENDPOINT


@pytest.mark.parametrize(
    "values",
    [
        {},
        {
            "EBAY_DELETION_VERIFICATION_TOKEN": "short",
            "EBAY_DELETION_ENDPOINT_URL": ENDPOINT,
        },
        {
            "EBAY_DELETION_VERIFICATION_TOKEN": "!" * 64,
            "EBAY_DELETION_ENDPOINT_URL": ENDPOINT,
        },
        {
            "EBAY_DELETION_VERIFICATION_TOKEN": TOKEN,
            "EBAY_DELETION_ENDPOINT_URL": "http://example.test/callback",
        },
    ],
)
def test_settings_reject_invalid_values(values: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        EbayComplianceSettings.from_environment(values)


def test_get_returns_expected_challenge_response() -> None:
    client, settings = build_client()
    response = client.get(
        "/api/compliance/ebay/account-deletion",
        params={"challenge_code": "challenge-123"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "challengeResponse": settings.challenge_response("challenge-123")
    }


def test_get_requires_challenge_code() -> None:
    client, _ = build_client()
    response = client.get("/api/compliance/ebay/account-deletion")
    assert response.status_code == 422


def test_post_acknowledges_notification() -> None:
    client, _ = build_client()
    response = client.post(
        "/api/compliance/ebay/account-deletion",
        json={"metadata": {"topic": "MARKETPLACE_ACCOUNT_DELETION"}},
    )
    assert response.status_code == 200
    assert response.json() == {
        "received": True,
        "notification_type": "MARKETPLACE_ACCOUNT_DELETION",
    }


def test_post_accepts_non_json_body() -> None:
    client, _ = build_client()
    response = client.post(
        "/api/compliance/ebay/account-deletion",
        content=b"not-json",
        headers={"content-type": "text/plain"},
    )
    assert response.status_code == 200
    assert response.json()["received"] is True
