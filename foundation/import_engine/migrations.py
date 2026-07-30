"""Discovery and transactional execution of ordered UIP migrations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import duckdb

from foundation.import_engine.config import ImportEngineConfig


CANONICAL_MIGRATION_PATTERN = re.compile(
    r"^(?P<order>\d{3})_[a-z0-9_]+\.sql$"
)

MIGRATION_DIRECTORY = Path(
    "foundation/import_engine/sql"
)


@dataclass(frozen=True)
class Migration:
    """One canonical ordered database migration."""

    order: int
    filename: str
    path: Path


def discover_ordered_migrations(
    repository_root: Path,
) -> tuple[Migration, ...]:
    """Return canonical migrations in numeric filename order."""

    sql_directory = (
        repository_root.resolve()
        / MIGRATION_DIRECTORY
    )

    if not sql_directory.is_dir():
        raise FileNotFoundError(
            f"Migration directory not found: {sql_directory}"
        )

    migrations: list[Migration] = []

    for path in sql_directory.glob("*.sql"):
        match = CANONICAL_MIGRATION_PATTERN.fullmatch(path.name)

        if match is None:
            continue

        lowered = path.name.lower()

        if "_before_" in lowered or "_backup_" in lowered:
            continue

        migrations.append(
            Migration(
                order=int(match.group("order")),
                filename=path.name,
                path=path,
            )
        )

    migrations.sort(
        key=lambda item: (
            item.order,
            item.filename.lower(),
        )
    )

    if not migrations:
        raise RuntimeError(
            f"No canonical migrations found in {sql_directory}"
        )

    orders = [migration.order for migration in migrations]

    if len(orders) != len(set(orders)):
        raise RuntimeError(
            "Duplicate migration order prefixes found."
        )

    if orders != sorted(orders):
        raise RuntimeError(
            "Migration order is not sorted."
        )

    return tuple(migrations)


def apply_ordered_migrations(
    config: ImportEngineConfig,
) -> tuple[str, ...]:
    """Apply the full canonical migration chain transactionally."""

    config.ensure_directories()

    migrations = discover_ordered_migrations(
        config.repository_root
    )

    connection = duckdb.connect(
        str(config.database_path)
    )

    try:
        connection.execute("BEGIN TRANSACTION")

        for migration in migrations:
            sql = migration.path.read_text(
                encoding="utf-8"
            )
            connection.execute(sql)

        connection.execute("COMMIT")
    except Exception:
        try:
            connection.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        connection.close()

    return tuple(
        migration.filename
        for migration in migrations
    )
