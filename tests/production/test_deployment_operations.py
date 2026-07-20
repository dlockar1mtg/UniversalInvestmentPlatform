from dataclasses import replace
from datetime import datetime, timezone

import pytest

from foundation.production import (
    DatabaseBackupManager, DeploymentManifest, MigrationCoordinator, ProductionRun,
    ProductionRuntimeConfig, SQLiteProductionRepository, SchemaMigration, SecretReference,
    ShutdownController, bootstrap_production, collect_operational_status,
)

NOW = datetime(2026, 7, 20, tzinfo=timezone.utc)


def config(tmp_path, environment="test"):
    return ProductionRuntimeConfig(environment, tmp_path / "data" / "production.sqlite3", tmp_path / "artifacts")


def manifest(environment="test", migrations=()):
    return DeploymentManifest("6.5.0", "revision-1", "a" * 64, environment, migrations, (SecretReference("UIIP_API_KEY"),))


def test_deployment_fingerprint_is_order_invariant_and_change_sensitive():
    one, two = SchemaMigration("001", "CREATE TABLE one(id INTEGER);"), SchemaMigration("002", "CREATE TABLE two(id INTEGER);")
    first = manifest(migrations=(one, two))
    second = manifest(migrations=(two, one))
    assert first.fingerprint == second.fingerprint
    assert replace(first, source_revision="revision-2").fingerprint != first.fingerprint


def test_migrations_are_ordered_idempotent_and_checksum_protected(tmp_path):
    coordinator = MigrationCoordinator(tmp_path / "database.sqlite3")
    migrations = (SchemaMigration("002", "CREATE TABLE second(id INTEGER);"), SchemaMigration("001", "CREATE TABLE first(id INTEGER);"))
    assert coordinator.apply(migrations) == ("001", "002")
    assert coordinator.apply(tuple(reversed(migrations))) == ()
    with pytest.raises(ValueError, match="checksum mismatch"):
        coordinator.apply((SchemaMigration("001", "CREATE TABLE changed(id INTEGER);"),))


def test_bootstrap_initializes_storage_migrations_and_readiness(tmp_path):
    runtime = config(tmp_path)
    result = bootstrap_production(runtime, manifest(migrations=(SchemaMigration("001", "CREATE TABLE release_marker(value TEXT);"),)), {"UIIP_API_KEY": "secret"})
    assert result.health.live and result.health.ready
    assert result.applied_migrations == ("001",)
    assert runtime.database_path.is_file() and runtime.artifact_directory.is_dir()


def test_bootstrap_fails_closed_for_environment_or_secret_mismatch(tmp_path):
    with pytest.raises(ValueError, match="environments must match"):
        bootstrap_production(config(tmp_path), manifest("staging"), {"UIIP_API_KEY": "secret"})
    with pytest.raises(ValueError, match="secret reference"):
        bootstrap_production(config(tmp_path), manifest(), {})


def test_database_backup_verification_and_restore_preserve_runs(tmp_path):
    runtime = config(tmp_path)
    bootstrap_production(runtime, manifest(), {"UIIP_API_KEY": "secret"})
    repo = SQLiteProductionRepository(runtime.database_path)
    repo.register_run(ProductionRun("run-1", "5.5", "a" * 64, "b" * 64, NOW))
    manager = DatabaseBackupManager(runtime.database_path)
    backup, restored = tmp_path / "backup.sqlite3", tmp_path / "restored.sqlite3"
    assert len(manager.create_backup(backup)) == 64 and manager.verify(backup)
    manager.restore(backup, restored)
    assert SQLiteProductionRepository(restored).get_run("run-1").run_id == "run-1"
    backup.unlink()
    assert not backup.exists()


def test_diagnostics_and_shutdown_are_deterministic_and_first_signal_wins(tmp_path):
    runtime = config(tmp_path)
    bootstrap_production(runtime, manifest(), {"UIIP_API_KEY": "secret"})
    first = collect_operational_status(runtime)
    second = collect_operational_status(runtime)
    assert first == second and first.database_available and first.artifact_directory_available
    shutdown = ShutdownController()
    shutdown.request("deployment")
    shutdown.request("later-signal")
    assert shutdown.requested and shutdown.reason == "deployment"
