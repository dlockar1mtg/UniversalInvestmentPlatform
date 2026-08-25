from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HTTP = (ROOT / "foundation" / "production" / "http_service.py").read_text(encoding="utf-8")
HTML = (ROOT / "foundation" / "production" / "dashboard_assets" / "dashboard.html").read_text(encoding="utf-8")
CLI = (ROOT / "scripts" / "activate_metals_tactical_policy_v3_live_presentation.py").read_text(encoding="utf-8")


def test_metals_tactical_asset_route_is_wired():
    assert '@app.get("/dashboard/assets/metals_tactical_ui.js"' in HTTP
    assert 'FileResponse(assets / "metals_tactical_ui.js"' in HTTP


def test_dashboard_loads_metals_tactical_ui():
    assert '<script src="/dashboard/assets/metals_tactical_ui.js" defer></script>' in HTML


def test_activation_cli_is_bound_to_certified_authorization():
    assert "METALS-TACTICAL-POLICY-V3-LIVE-PRESENTATION-ACTIVATION-AUTHORIZATION-1" in CLI
    assert "AUTHORIZE_ONE_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION" in CLI
    assert "execution_limit" in CLI
    assert "execution_is_one_time" in CLI


def test_activation_cli_requires_exact_certified_publication():
    assert 'EXPECTED_DB_SHA = "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"' in CLI
    assert 'EXPECTED_FINGERPRINT = "21a3e3c8a1e73b7370d23f0704081f7ac01f28609bed22f94d00d4f4c2e7c126"' in CLI
    assert "EXPECTED_RECORD_COUNT = 4181" in CLI
    assert "EXPECTED_TACTICAL_COUNT = 10" in CLI


def test_activation_cli_reads_duckdb_only():
    assert "duckdb.connect(str(database), read_only=True)" in CLI
    assert "INSERT INTO" not in CLI
    assert "UPDATE " not in CLI
    assert "DELETE FROM" not in CLI


def test_activation_cli_uses_existing_fail_closed_publication_service():
    assert "validate_publication_bundle(publication)" in CLI
    assert "publish_presentation_bundle(store, publication)" in CLI
    assert "previous = store.active_metadata()" in CLI
    assert "active = store.active_metadata()" in CLI


def test_activation_cli_rejects_reference_control_as_opportunity():
    assert 'get("is_reference_control") is True' in CLI
    assert "Reference/control row entered tactical opportunity projection." in CLI


def test_activation_cli_reports_no_analytical_write():
    assert '"analytical_database_write": False' in CLI
