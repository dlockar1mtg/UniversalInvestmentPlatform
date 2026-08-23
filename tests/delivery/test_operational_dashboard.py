from pathlib import Path

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from foundation.production.dashboard import DashboardSettings
from foundation.production.http_service import HTTPServiceSettings, create_http_app
from foundation.production.persistence import SQLiteProductionRepository


def client(tmp_path):
    repository = SQLiteProductionRepository(tmp_path / "dashboard.sqlite3")
    repository.initialize()
    settings = HTTPServiceSettings(credentials={
        "viewer": ("view-key", ("viewer",)), "operator": ("operate-key", ("operator",)),
    })
    dashboard = DashboardSettings(tmp_path / "holdings.csv", True, True)
    return TestClient(create_http_app(settings, repository, dashboard))


def test_dashboard_shell_and_assets_are_public_but_contain_no_credentials(tmp_path):
    service = client(tmp_path)
    page = service.get("/dashboard")
    assert page.status_code == 200
    assert "Universal Investment Platform" in page.text
    for label in ("Home", "Recommendations", "Portfolio", "Transactions", "Refresh", "Operations"):
        assert f'>{label}<' in page.text
    assert "view-key" not in page.text and "operate-key" not in page.text
    assert service.get("/dashboard/assets/dashboard.css").status_code == 200
    assert service.get("/dashboard/assets/dashboard.js").status_code == 200
    picker = service.get("/dashboard/assets/governed_asset_picker.js")
    assert picker.status_code == 200
    assert "Select certified domain" in picker.text
    assert "/v1/presentation/assets?domain=" in picker.text
    assert "Connect to load certified domains" in picker.text
    assert 'authForm.addEventListener("submit",()=>setTimeout(loadDomains,0))' in picker.text
    assert 'refreshButton.addEventListener("click",()=>setTimeout(loadDomains,0))' in picker.text
    assert "const exactExisting=matches.get(query)" in picker.text
    assert "Governed asset selected." in picker.text
    assert "clearTimeout(searchTimer)" in picker.text
    assert "assetInput.dataset.assetId!==String(selected.asset_id)" in picker.text


def test_dashboard_data_requires_read_permission(tmp_path):
    service = client(tmp_path)
    assert service.get("/v1/dashboard/summary").status_code == 401
    assert service.get("/v1/dashboard/summary", headers={"X-API-Key": "bad"}).status_code == 401
    assert service.get("/v1/dashboard/summary", headers={"X-API-Key": "view-key"}).status_code == 200


def test_environment_credentials_enable_dashboard_authentication(tmp_path):
    settings = HTTPServiceSettings.from_environment({
        "UIIP_DATABASE_BACKEND": "sqlite", "UIIP_SQLITE_PATH": str(tmp_path / "environment.sqlite3"),
        "UIIP_API_CREDENTIALS_JSON": '{"viewer":{"credential":"environment-key","roles":["viewer"]}}',
    })
    service = TestClient(create_http_app(settings))
    assert service.get("/v1/dashboard/summary", headers={"X-API-Key": "environment-key"}).status_code == 200
    with pytest.raises(ValueError, match="CREDENTIALS_JSON"):
        HTTPServiceSettings.from_environment({"UIIP_API_CREDENTIALS_JSON": "[]"})


def test_summary_reports_readiness_without_exposing_secret_values(tmp_path):
    service = client(tmp_path)
    response = service.get("/v1/dashboard/summary", headers={"X-API-Key": "view-key"})
    document = response.json()
    assert document["service"] == {"live": True, "ready": True}
    assert document["integrations"] == {"alpha_vantage": True, "fred": True, "portfolio_csv": False}
    assert "view-key" not in response.text


def test_dashboard_activity_reflects_redacted_gateway_events(tmp_path):
    service = client(tmp_path)
    service.get("/v1/runs/missing", headers={"X-API-Key": "view-key", "X-Correlation-ID": "dashboard-audit"})
    events = service.get("/v1/dashboard/events", headers={"X-API-Key": "view-key"}).json()["items"]
    summary = service.get("/v1/dashboard/summary", headers={"X-API-Key": "view-key"}).json()
    assert events[0]["correlation_id"] == "dashboard-audit"
    assert events[0]["fields"]["credential"] == "[REDACTED]"
    assert summary["activity"]["api_requests"] == 1


def test_metric_endpoint_returns_stable_counter_documents(tmp_path):
    service = client(tmp_path)
    service.get("/v1/runs/missing", headers={"X-API-Key": "view-key"})
    metrics = service.get("/v1/dashboard/metrics", headers={"X-API-Key": "view-key"}).json()
    assert metrics["counters"][0]["name"] == "production_api_requests_total"
    assert metrics["counters"][0]["labels"] == {"method": "GET", "status": "404"}
    assert metrics["counters"][0]["value"] == 1


def test_dashboard_javascript_has_loading_error_empty_and_session_only_key_states(tmp_path):
    script = client(tmp_path).get("/dashboard/assets/dashboard.js").text
    assert "Loading certified presentation authority" in script
    assert "No operational events recorded yet" in script
    assert "sessionStorage" in script and "localStorage" not in script
    assert "response.ok" in script
