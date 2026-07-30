from __future__ import annotations

from pathlib import Path

import duckdb

from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.migrations import (
    discover_ordered_migrations,
)


ROOT = Path(__file__).resolve().parents[1]


def _config(database_path: Path) -> ImportEngineConfig:
    base = ImportEngineConfig.from_repository_root(ROOT)

    return ImportEngineConfig(
        repository_root=ROOT,
        database_path=database_path,
        schema_root=base.schema_root,
        integration_root=base.integration_root,
        validation_root=base.validation_root,
    )


def _objects(database_path: Path) -> dict[str, str]:
    connection = duckdb.connect(
        str(database_path),
        read_only=True,
    )

    try:
        rows = connection.execute(
            """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
            """
        ).fetchall()
    finally:
        connection.close()

    return {
        str(name): str(object_type)
        for name, object_type in rows
    }


def test_discovers_all_canonical_migrations() -> None:
    migrations = discover_ordered_migrations(ROOT)

    assert [
        migration.filename
        for migration in migrations
    ] == [
        "001_initialize_universal_database.sql",
        "002_audit_registry_integration.sql",
        "003_health_status_latest_attempt.sql",
        "004_historical_performance.sql",
    ]


def test_fresh_database_contains_historical_objects(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "fresh.duckdb"

    initialize_database(_config(database_path))

    objects = _objects(database_path)

    assert (
        objects["historical_performance_history"]
        == "BASE TABLE"
    )
    assert (
        objects["historical_performance_current"]
        == "VIEW"
    )
    assert len(objects) == 25


def test_upgrade_from_first_three_migrations(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "upgrade.duckdb"

    migrations = discover_ordered_migrations(ROOT)
    first_three = migrations[:3]

    connection = duckdb.connect(str(database_path))

    try:
        for migration in first_three:
            connection.execute(
                migration.path.read_text(
                    encoding="utf-8"
                )
            )
    finally:
        connection.close()

    before = _objects(database_path)

    assert len(before) == 23
    assert "historical_performance_history" not in before

    initialize_database(_config(database_path))

    after = _objects(database_path)

    assert len(after) == 25
    assert (
        after["historical_performance_history"]
        == "BASE TABLE"
    )
    assert (
        after["historical_performance_current"]
        == "VIEW"
    )


def test_full_chain_is_idempotent(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "idempotent.duckdb"
    config = _config(database_path)

    initialize_database(config)
    first = _objects(database_path)

    initialize_database(config)
    second = _objects(database_path)

    assert first == second
    assert len(second) == 25


def test_failed_migration_rolls_back_full_chain(
    tmp_path: Path,
) -> None:
    repository = tmp_path / "repository"
    sql_directory = (
        repository
        / "foundation"
        / "import_engine"
        / "sql"
    )
    sql_directory.mkdir(parents=True)

    (sql_directory / "001_create_table.sql").write_text(
        "CREATE TABLE rollback_probe (value INTEGER);",
        encoding="utf-8",
    )
    (sql_directory / "002_fail.sql").write_text(
        "THIS IS NOT VALID SQL;",
        encoding="utf-8",
    )

    database_path = tmp_path / "rollback.duckdb"
    base = ImportEngineConfig.from_repository_root(ROOT)

    config = ImportEngineConfig(
        repository_root=repository,
        database_path=database_path,
        schema_root=base.schema_root,
        integration_root=base.integration_root,
        validation_root=base.validation_root,
    )

    import pytest

    with pytest.raises(Exception):
        initialize_database(config)

    connection = duckdb.connect(str(database_path))

    try:
        objects = connection.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
              AND table_name = 'rollback_probe'
            """
        ).fetchall()
    finally:
        connection.close()

    assert objects == []

