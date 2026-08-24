from pathlib import Path


def test_metals_tactical_evidence_production_verifier_contract() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "verify_metals_tactical_evidence_production.py"
    text = script.read_text(encoding="utf-8")

    required = [
        "metals_forecast_model_component_current",
        "metals_regime_probability_current",
        "metals_uncertainty_adjusted_view_current",
        "metals_recommendation_change_current",
        "metals_data_freshness_current",
        "metals_platform_health_current",
        "EXPECTED_PACKAGE_ID",
        "EXPECTED_IMPORT_ID",
        "EXPECTED_MANIFEST_SHA256",
        "component weights do not reconcile",
        "regime probabilities do not reconcile",
        "uncertainty-adjusted return arithmetic",
        "automatic execution",
        "AUTHORIZE_METALS_PRESENTATION_CONTRACT_EXPANSION",
    ]

    for token in required:
        assert token in text

    assert "read_only=True" in text
    assert "automatic_execution_authorized\": False" in text
