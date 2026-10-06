"""MTG freshness: the registry gets a data date even though the MTG binding imports no status row."""
from __future__ import annotations

import csv
from pathlib import Path

import duckdb

from foundation.import_engine.audit import synchronize_successful_import
from foundation.import_engine.config import ImportEngineConfig
from scripts.publish_latest_domain_artifacts import mtg_data_as_of_date


def _write_forecasts(package: Path, observed: list[str]) -> None:
    package.mkdir(parents=True, exist_ok=True)
    with (package / "forecasts.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["asset_id", "market_observed_at_utc"])
        writer.writeheader()
        for index, value in enumerate(observed):
            writer.writerow({"asset_id": f"a{index}", "market_observed_at_utc": value})


def test_data_as_of_is_newest_market_observation(tmp_path):
    package = tmp_path / "latest"
    _write_forecasts(
        package,
        ["2026-10-04T12:00:00+00:00", "", "2026-10-05T13:20:11.123+00:00", "not-a-date"],
    )
    summary = {"live_overlay": {"status": "PASS", "applied_at_utc": "2026-10-06T12:40:00+00:00"}}

    assert mtg_data_as_of_date(package, summary) == "2026-10-05"


def test_data_as_of_falls_back_to_overlay_time(tmp_path):
    package = tmp_path / "latest"
    _write_forecasts(package, ["", ""])
    summary = {"live_overlay": {"status": "PASS", "applied_at_utc": "2026-10-06T12:40:00+00:00"}}

    assert mtg_data_as_of_date(package, summary) == "2026-10-06"
    assert mtg_data_as_of_date(tmp_path / "missing", summary) == "2026-10-06"
    assert mtg_data_as_of_date(tmp_path / "missing", {}) is None


def _registry_database(tmp_path: Path) -> ImportEngineConfig:
    config = ImportEngineConfig(
        repository_root=tmp_path,
        database_path=tmp_path / "uip.duckdb",
        schema_root=tmp_path / "schemas",
        integration_root=tmp_path / "integration",
        validation_root=tmp_path / "validation",
    )
    connection = duckdb.connect(str(config.database_path))
    try:
        connection.execute(
            """
            CREATE TABLE universal_imports (
                import_id VARCHAR PRIMARY KEY, package_id VARCHAR, platform_id VARCHAR,
                run_id VARCHAR, adapter_version VARCHAR, contract_version VARCHAR,
                import_status VARCHAR, completed_at_utc TIMESTAMP,
                imported_row_count BIGINT, warning_count BIGINT, error_count BIGINT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE platform_status_history (
                _import_id VARCHAR, platform_name VARCHAR, platform_version VARCHAR,
                data_as_of_date DATE, status_message VARCHAR
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE universal_platform_registry (
                platform_id VARCHAR PRIMARY KEY, platform_name VARCHAR,
                platform_version VARCHAR, adapter_version VARCHAR, contract_version VARCHAR,
                registry_status VARCHAR NOT NULL, last_package_id VARCHAR,
                last_run_id VARCHAR, last_import_id VARCHAR, last_import_status VARCHAR,
                last_imported_at_utc TIMESTAMP, last_data_as_of_date DATE,
                total_successful_imports BIGINT DEFAULT 0,
                total_failed_imports BIGINT DEFAULT 0, total_rows_imported BIGINT DEFAULT 0,
                warning_count BIGINT DEFAULT 0, error_count BIGINT DEFAULT 0,
                status_message VARCHAR, created_at_utc TIMESTAMP NOT NULL,
                updated_at_utc TIMESTAMP NOT NULL
            )
            """
        )
        for import_id, platform in (("imp-mtg", "mtg"), ("imp-crypto", "crypto")):
            connection.execute(
                "INSERT INTO universal_imports VALUES (?, ?, ?, 'run', 'a', '1.0.0', 'IMPORTED', now(), 3, 0, 0)",
                [import_id, f"pkg-{platform}", platform],
            )
        connection.execute(
            "INSERT INTO platform_status_history VALUES ('imp-crypto', 'Crypto', '3', DATE '2026-10-05', 'ok')"
        )
    finally:
        connection.close()
    return config


def _registry_date(config: ImportEngineConfig, platform: str):
    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        value = connection.execute(
            "SELECT last_data_as_of_date FROM universal_platform_registry WHERE platform_id = ?",
            [platform],
        ).fetchone()[0]
    finally:
        connection.close()
    return None if value is None else value.isoformat()


def test_registry_uses_fallback_only_without_status_date(tmp_path):
    config = _registry_database(tmp_path)

    synchronize_successful_import(config, import_id="imp-mtg", fallback_data_as_of_date="2026-10-06")
    synchronize_successful_import(config, import_id="imp-crypto", fallback_data_as_of_date="2026-10-06")

    assert _registry_date(config, "mtg") == "2026-10-06"
    assert _registry_date(config, "crypto") == "2026-10-05"


def test_registry_without_fallback_keeps_unknown_date(tmp_path):
    config = _registry_database(tmp_path)

    synchronize_successful_import(config, import_id="imp-mtg")

    assert _registry_date(config, "mtg") is None
