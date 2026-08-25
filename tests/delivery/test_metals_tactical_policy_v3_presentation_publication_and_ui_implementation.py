from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_extension_is_bound_to_certified_postwrite_database_and_adds_tactical_state_surface():
    extension = json.loads(read("config/presentation/dash_read_1_metals_tactical_extension.json"))
    assert extension["version"] == "1.1.0"
    assert extension["source_database_sha256"] == "9588eab0820f5299982b4f5837056f5750675bc839a0bcb13f166dce13ecef6f"
    assert extension["controls"]["tactical_posture_authorized"] is True
    assert len(extension["surfaces"]) == 7
    tactical = extension["surfaces"]["tactical_state"]
    assert tactical["source"] == "metals_tactical_state_current"
    assert tactical["asset_identity"] == "universal_asset_id"


def test_projection_preserves_prior_surfaces_and_adds_tactical_state_without_bil_opportunity_projection():
    source = read("foundation/presentation/metals_tactical_projection.py")
    for relation in (
        "metals_forecast_model_component_current",
        "metals_regime_probability_current",
        "metals_uncertainty_adjusted_view_current",
        "metals_recommendation_change_current",
        "metals_data_freshness_current",
        "metals_platform_health_current",
    ):
        assert relation in source
    assert "metals_tactical_state_current" in source
    assert 'if bool(row.get("is_reference_control")):' in source
    assert '_record("tactical_state", asset_id, asset_id, row)' in source


def test_publication_builder_continues_to_use_single_metals_projection_extension_point():
    source = read("foundation/presentation/publication_model.py")
    assert "from .metals_tactical_projection import build_metals_tactical_records" in source
    assert "records.extend(build_metals_tactical_records(repository_root, connection, source_sha256))" in source


def test_ui_helper_keeps_tactical_state_separate_from_long_term_authorities():
    source = read("foundation/production/dashboard_assets/metals_tactical_ui.js")
    assert 'const RECORD_TYPE="tactical_state"' in source
    assert 'const DOMAIN="metals"' in source
    assert "No tactical overlay" in source
    assert "not a negative long-term thesis" in source
    assert "sell signal" in source
    assert "zero expected return" in source
    assert "allocation instruction" in source
    assert "does not replace the certified long-term recommendation" in source
    assert "forecast, risk evidence, or execution controls" in source


def test_ui_helper_fails_closed_for_missing_unknown_and_reference_control_state():
    source = read("foundation/production/dashboard_assets/metals_tactical_ui.js")
    assert "Tactical state unavailable" in source
    assert "No certified tactical-state record is available" in source
    assert "Reference/control vehicle; not an opportunity recommendation." in source
    assert "window.UIPMetalsTactical" in source


def test_live_dashboard_wiring_requires_separate_bounded_activation_authorization_and_remains_unexecuted():
    dashboard = read("foundation/production/dashboard_assets/dashboard.html")
    assert "/dashboard/assets/metals_tactical_ui.js" in dashboard

    implementation_authorization = json.loads(
        read("config/metals/tactical_policy_v3_presentation_activation_authorization.json")
    )
    assert implementation_authorization["authorization_boundary"]["presentation_activation_authorized"] is False
    assert implementation_authorization["authorization_boundary"]["presentation_activation_executed"] is False
    assert implementation_authorization["authorization_boundary"]["analytical_database_write_authorized"] is False

    live_authorization = json.loads(
        read("config/metals/tactical_policy_v3_live_presentation_activation_authorization.json")
    )
    assert live_authorization["authorization_decision"] == "AUTHORIZE_ONE_BOUNDED_METALS_V3_LIVE_PRESENTATION_ACTIVATION"
    assert live_authorization["execution_limit"] == 1
    assert live_authorization["execution_is_one_time"] is True
    assert live_authorization["authorization_boundary"]["live_presentation_activation_authorized"] is True
    assert live_authorization["authorization_boundary"]["live_presentation_activation_executed"] is False
    assert live_authorization["authorization_boundary"]["analytical_database_write_authorized"] is False
