from __future__ import annotations

from pathlib import Path


def test_production_promotion_script_has_fail_closed_guards() -> None:
    root = Path(__file__).resolve().parents[2]
    script = (root / "scripts" / "promote_metals_native_evidence_production.py").read_text(encoding="utf-8")

    required = [
        "--expected-sha256",
        "--package-root",
        "--backup-root",
        "Backup checksum does not match authoritative database before mutation.",
        "Partial prior promotion detected for current package",
        "NOOP_ALREADY_PROMOTED",
        "PRODUCTION_PROMOTION",
        "automatic_execution_authorized",
        "VERIFY_AND_PUBLISH_METALS_TACTICAL_EVIDENCE",
    ]

    for marker in required:
        assert marker in script


def test_metals_tactical_schema_migration_is_canonical_011() -> None:
    root = Path(__file__).resolve().parents[2]
    migration = root / "foundation" / "import_engine" / "sql" / "011_metals_tactical_evidence_authority.sql"
    assert migration.is_file()

    sql = migration.read_text(encoding="utf-8")
    assert "metals_forecast_model_component_history" in sql
    assert "metals_regime_probability_history" in sql
    assert "metals_uncertainty_adjusted_view_history" in sql
    assert "metals_recommendation_change_history" in sql
    assert "metals_data_freshness_history" in sql
    assert "metals_platform_health_history" in sql
