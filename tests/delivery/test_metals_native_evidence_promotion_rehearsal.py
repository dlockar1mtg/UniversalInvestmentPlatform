from __future__ import annotations

from pathlib import Path

import duckdb

from foundation.import_engine.migrations import discover_ordered_migrations


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "foundation" / "import_engine" / "sql" / "011_metals_tactical_evidence_authority.sql"
SCRIPT = ROOT / "scripts" / "rehearse_metals_native_evidence_promotion.py"


def test_metals_tactical_evidence_migration_is_canonical_and_valid() -> None:
    migrations = discover_ordered_migrations(ROOT)
    assert migrations[-1].filename == "011_metals_tactical_evidence_authority.sql"
    assert MIGRATION.is_file()
    assert SCRIPT.is_file()

    connection = duckdb.connect(":memory:")
    try:
        connection.execute(MIGRATION.read_text(encoding="utf-8"))
        expected = {
            "metals_forecast_model_component_current",
            "metals_regime_probability_current",
            "metals_uncertainty_adjusted_view_current",
            "metals_recommendation_change_current",
            "metals_data_freshness_current",
            "metals_platform_health_current",
        }
        rows = connection.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        names = {str(row[0]) for row in rows}
        assert expected <= names
    finally:
        connection.close()


def test_rehearsal_is_copy_only_and_does_not_authorize_execution() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert "shutil.copy2(args.database, rehearsal_db)" in text
    assert "production_database_mutated\": False" in text
    assert "AUTHORIZE_PRODUCTION_METALS_NATIVE_EVIDENCE_PROMOTION" in text
    assert "automatic" not in text.lower()
