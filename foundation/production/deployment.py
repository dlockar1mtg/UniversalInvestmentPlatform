"""Release manifests, schema migrations, startup gates, and backups."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sqlite3
from typing import Mapping

from .config import ProductionRuntimeConfig
from .observability import HealthReport, evaluate_health
from .persistence import SQLiteProductionRepository
from .scheduling import SQLiteJobRepository
from .security import SecretReference


@dataclass(frozen=True)
class SchemaMigration:
    migration_id: str
    sql: str

    def __post_init__(self) -> None:
        if not self.migration_id.strip() or not self.sql.strip():
            raise ValueError("migration identity and SQL are required")

    @property
    def checksum(self) -> str:
        return sha256(self.sql.encode()).hexdigest()


@dataclass(frozen=True)
class DeploymentManifest:
    release_version: str
    source_revision: str
    artifact_fingerprint: str
    environment: str
    migrations: tuple[SchemaMigration, ...] = ()
    required_secrets: tuple[SecretReference, ...] = ()

    def __post_init__(self) -> None:
        if not all((self.release_version.strip(), self.source_revision.strip(), self.artifact_fingerprint.strip())):
            raise ValueError("release, source revision, and artifact fingerprint are required")
        if self.environment not in {"development", "test", "staging", "production"}:
            raise ValueError("unsupported deployment environment")
        ids = [item.migration_id for item in self.migrations]
        if len(ids) != len(set(ids)):
            raise ValueError("migration identifiers must be unique")

    @property
    def fingerprint(self) -> str:
        payload = {
            "artifact_fingerprint": self.artifact_fingerprint, "environment": self.environment,
            "migrations": sorted((item.migration_id, item.checksum) for item in self.migrations),
            "release_version": self.release_version,
            "required_secrets": sorted(item.name for item in self.required_secrets),
            "source_revision": self.source_revision,
        }
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class MigrationCoordinator:
    def __init__(self, database_path: str | Path):
        self.database_path = str(database_path)

    def apply(self, migrations: tuple[SchemaMigration, ...]) -> tuple[str, ...]:
        applied = []
        with closing(sqlite3.connect(self.database_path)) as db:
            db.execute("CREATE TABLE IF NOT EXISTS production_schema_migrations (migration_id TEXT PRIMARY KEY, checksum TEXT NOT NULL, applied_at TEXT NOT NULL)")
            for migration in sorted(migrations, key=lambda item: item.migration_id):
                row = db.execute("SELECT checksum FROM production_schema_migrations WHERE migration_id=?", (migration.migration_id,)).fetchone()
                if row:
                    if row[0] != migration.checksum:
                        raise ValueError("applied migration checksum mismatch")
                    continue
                db.executescript(migration.sql)
                db.execute("INSERT INTO production_schema_migrations VALUES (?,?,datetime('now'))", (migration.migration_id, migration.checksum))
                applied.append(migration.migration_id)
            db.commit()
        return tuple(applied)


@dataclass(frozen=True)
class StartupResult:
    manifest_fingerprint: str
    applied_migrations: tuple[str, ...]
    health: HealthReport


def bootstrap_production(
    config: ProductionRuntimeConfig, manifest: DeploymentManifest,
    secret_source: Mapping[str, str],
) -> StartupResult:
    if config.environment != manifest.environment:
        raise ValueError("runtime and deployment environments must match")
    for reference in manifest.required_secrets:
        reference.resolve(secret_source)
    config.database_path.parent.mkdir(parents=True, exist_ok=True)
    config.artifact_directory.mkdir(parents=True, exist_ok=True)
    SQLiteProductionRepository(config.database_path).initialize()
    SQLiteJobRepository(config.database_path).initialize()
    applied = MigrationCoordinator(config.database_path).apply(manifest.migrations)

    def database_ready() -> bool:
        with closing(sqlite3.connect(config.database_path)) as db:
            return db.execute("PRAGMA quick_check").fetchone()[0] == "ok"

    health = evaluate_health({
        "artifact_directory": lambda: config.artifact_directory.is_dir(),
        "database": database_ready,
    })
    if not health.ready:
        raise RuntimeError("production startup readiness checks failed")
    return StartupResult(manifest.fingerprint, applied, health)


class DatabaseBackupManager:
    def __init__(self, source_database: str | Path):
        self.source_database = Path(source_database)

    def create_backup(self, destination: str | Path) -> str:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.source_database)) as source, closing(sqlite3.connect(target)) as backup:
            source.backup(backup)
        data = target.read_bytes()
        if not data:
            raise RuntimeError("database backup is empty")
        return sha256(data).hexdigest()

    @staticmethod
    def verify(path: str | Path) -> bool:
        try:
            with closing(sqlite3.connect(path)) as db:
                return db.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        except sqlite3.DatabaseError:
            return False

    @staticmethod
    def restore(backup: str | Path, destination: str | Path) -> None:
        source, target = Path(backup), Path(destination)
        if target.exists():
            raise FileExistsError("restore destination already exists")
        if not DatabaseBackupManager.verify(source):
            raise ValueError("backup database failed integrity verification")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
