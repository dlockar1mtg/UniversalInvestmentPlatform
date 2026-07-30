from __future__ import annotations

import argparse
import sys
import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.import_engine.migrations import (
    discover_ordered_migrations,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_statements(text: str, keyword: str) -> list[str]:
    pattern = re.compile(
        rf"\b{re.escape(keyword)}\b.*?;",
        flags=re.IGNORECASE | re.DOTALL,
    )
    return [re.sub(r"\s+", " ", match.group(0)).strip() for match in pattern.finditer(text)]


def normalize_sql(value: str | None) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", value).strip().rstrip(";")


def object_inventory(connection: duckdb.DuckDBPyConnection) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT table_schema, table_name, table_type
        FROM information_schema.tables
        WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
        ORDER BY table_schema, table_name
        """
    ).fetchall()

    view_sql = {
        (schema_name, view_name): normalize_sql(sql)
        for schema_name, view_name, sql in connection.execute(
            """
            SELECT schema_name, view_name, sql
            FROM duckdb_views()
            WHERE internal = false
            """
        ).fetchall()
    }

    constraints: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for (
        schema_name,
        table_name,
        constraint_type,
        constraint_text,
        expression,
    ) in connection.execute(
        """
        SELECT
            schema_name,
            table_name,
            constraint_type,
            constraint_text,
            expression
        FROM duckdb_constraints()
        ORDER BY schema_name, table_name, constraint_index
        """
    ).fetchall():
        constraints.setdefault((schema_name, table_name), []).append(
            {
                "type": constraint_type,
                "text": normalize_sql(constraint_text),
                "expression": normalize_sql(expression),
            }
        )

    indexes: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for (
        schema_name,
        table_name,
        index_name,
        is_unique,
        expressions,
        sql,
    ) in connection.execute(
        """
        SELECT
            schema_name,
            table_name,
            index_name,
            is_unique,
            expressions,
            sql
        FROM duckdb_indexes()
        ORDER BY schema_name, table_name, index_name
        """
    ).fetchall():
        indexes.setdefault((schema_name, table_name), []).append(
            {
                "name": index_name,
                "unique": bool(is_unique),
                "expressions": normalize_sql(expressions),
                "sql": normalize_sql(sql),
            }
        )

    result: list[dict[str, Any]] = []
    for schema_name, object_name, object_type in rows:
        columns = connection.execute(
            """
            SELECT column_name, data_type, is_nullable, ordinal_position
            FROM information_schema.columns
            WHERE table_schema = ?
              AND table_name = ?
            ORDER BY ordinal_position
            """,
            [schema_name, object_name],
        ).fetchall()

        key = (schema_name, object_name)

        result.append(
            {
                "schema": schema_name,
                "name": object_name,
                "qualified_name": f"{schema_name}.{object_name}",
                "type": object_type,
                "columns": [
                    {
                        "name": name,
                        "type": data_type,
                        "nullable": nullable == "YES",
                        "position": position,
                    }
                    for name, data_type, nullable, position in columns
                ],
                "constraints": constraints.get(key, []),
                "indexes": indexes.get(key, []),
                "view_definition": view_sql.get(key),
            }
        )

    return result


def inspect_sql(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "filename": path.name,
        "sha256": sha256(path),
        "size_bytes": path.stat().st_size,
        "create_tables": extract_statements(text, "CREATE TABLE"),
        "create_views": extract_statements(text, "CREATE VIEW"),
        "create_or_replace_views": extract_statements(text, "CREATE OR REPLACE VIEW"),
        "alter_tables": extract_statements(text, "ALTER TABLE"),
        "drop_statements": extract_statements(text, "DROP"),
    }


def compare_objects(
    baseline: list[dict[str, Any]],
    reconstructed: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_map = {item["qualified_name"]: item for item in baseline}
    reconstructed_map = {item["qualified_name"]: item for item in reconstructed}

    missing = sorted(set(baseline_map) - set(reconstructed_map))
    extra = sorted(set(reconstructed_map) - set(baseline_map))

    changed: list[dict[str, Any]] = []
    for name in sorted(set(baseline_map) & set(reconstructed_map)):
        left = baseline_map[name]
        right = reconstructed_map[name]
        compared_fields = [
            "type",
            "columns",
            "constraints",
            "indexes",
            "view_definition",
        ]

        differing_fields = [
            field
            for field in compared_fields
            if left.get(field) != right.get(field)
        ]

        if differing_fields:
            changed.append(
                {
                    "qualified_name": name,
                    "differing_fields": differing_fields,
                    "baseline": {
                        field: left.get(field)
                        for field in differing_fields
                    },
                    "reconstructed": {
                        field: right.get(field)
                        for field in differing_fields
                    },
                }
            )

    return {
        "missing_from_reconstruction": missing,
        "extra_in_reconstruction": extra,
        "definition_mismatches": changed,
        "matches": not missing and not extra and not changed,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# UIP Ordered Migration Chain Reconciliation Report",
        "",
        "## Inspection scope",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Current database: `{report['current_database']['path']}`",
            f"- Current database SHA-256 before inspection: "
            f"`{report['current_database']['sha256_before']}`",
            f"- Current database SHA-256 after inspection: "
            f"`{report['current_database']['sha256_after']}`",
        "- Current database opened read-only: `true`",
        "- Reconstruction database: temporary disposable DuckDB file",
        "",
        "## Active migration chain",
        "",
        "| Order | File | SHA-256 | Size |",
        "|---:|---|---|---:|",
    ]

    for migration in report["active_migrations"]:
        lines.append(
            f"| {migration['order']} | `{migration['path']}` | "
            f"`{migration['sha256']}` | {migration['size_bytes']} |"
        )

    lines.extend(
        [
            "",
            "## Preserved non-authoritative SQL evidence",
            "",
        ]
    )

    for evidence in report["preserved_evidence"]:
        lines.append(
            f"- `{evidence['path']}` — SHA-256 `{evidence['sha256']}`"
        )

    lines.extend(
        [
            "",
            "## Backup comparison",
            "",
            f"- Canonical `002` equals preserved backup: "
            f"`{str(report['backup_comparison']['identical']).lower()}`",
            f"- Canonical-only lines: `{report['backup_comparison']['canonical_only_line_count']}`",
            f"- Backup-only lines: `{report['backup_comparison']['backup_only_line_count']}`",
            "",
            "## Temporary baseline upgrade",
            "",
            f"- Execution result: `{report['temporary_upgrade']['status']}`",
            f"- Executed files: `{report['temporary_upgrade']['executed_files']}`",
            f"- Baseline objects: `{report['current_database']['object_count']}`",
            f"- Upgraded objects: `{report['temporary_upgrade']['object_count']}`",
            "",
            "## Fresh reconstruction",
            "",
            f"- Execution result: `{report['reconstruction']['status']}`",
            f"- Executed files: `{report['reconstruction']['executed_files']}`",
            f"- Reconstructed objects: `{report['reconstruction']['object_count']}`",
            "",
            "## Schema comparison",
            "",
            f"- Exact object, column, constraint, index, and view-definition match: "
            f"`{str(report['schema_comparison']['matches']).lower()}`",
            "",
            "### Missing from reconstruction",
            "",
        ]
    )

    missing = report["schema_comparison"]["missing_from_reconstruction"]
    lines.extend([f"- `{name}`" for name in missing] or ["- None"])

    lines.extend(["", "### Extra in reconstruction", ""])
    extra = report["schema_comparison"]["extra_in_reconstruction"]
    lines.extend([f"- `{name}`" for name in extra] or ["- None"])

    lines.extend(["", "### Definition mismatches", ""])
    mismatches = report["schema_comparison"]["definition_mismatches"]
    if mismatches:
        for mismatch in mismatches:
            lines.append(f"- `{mismatch['qualified_name']}`")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Reconciliation disposition",
            "",
            f"`{report['disposition']}`",
            "",
            "No production database changes were made.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help=(
            "Optional existing DuckDB baseline. Defaults to "
            "data/universal/universal_investment.duckdb under --repo."
        ),
    )
    args = parser.parse_args()

    repo = args.repo.resolve()
    sql_dir = repo / "foundation" / "import_engine" / "sql"
    current_db = (
        args.database.resolve()
        if args.database
        else (
            repo
            / "data"
            / "universal"
            / "universal_investment.duckdb"
        )
    )
    output_dir = repo / "docs" / "project_control" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    migrations = discover_ordered_migrations(repo)
    active_paths = [
        migration.path
        for migration in migrations
    ]

    backup_name = (
        "002_audit_registry_integration_before_1_3_6_2_"
        "20260717_085304.sql"
    )
    backup_path = sql_dir / backup_name

    for path in [*active_paths, current_db]:
        if not path.exists():
            raise RuntimeError(f"Required path missing: {path}")

    current_connection = duckdb.connect(str(current_db), read_only=True)
    try:
        current_objects = object_inventory(current_connection)
    finally:
        current_connection.close()

    canonical_002_lines = set(
        active_paths[1].read_text(
            encoding="utf-8"
        ).splitlines()
    )

    backup_002_lines = (
        set(
            backup_path.read_text(
                encoding="utf-8"
            ).splitlines()
        )
        if backup_path.exists()
        else set()
    )

    production_sha256_before = sha256(current_db)

    reconstruction_status = "PASS"
    reconstruction_error = None
    reconstructed_objects: list[dict[str, Any]] = []
    reconstructed_executed_files = 0

    upgrade_status = "PASS"
    upgrade_error = None
    upgraded_objects: list[dict[str, Any]] = []
    upgrade_executed_files = 0

    temp_dir = Path(
        tempfile.mkdtemp(
            prefix="uip_migration_reconcile_"
        )
    )
    fresh_db = temp_dir / "fresh_reconstruction.duckdb"
    upgraded_db = temp_dir / "upgraded_copy.duckdb"

    try:
        shutil.copy2(current_db, upgraded_db)

        upgrade_connection = duckdb.connect(
            str(upgraded_db)
        )
        try:
            upgrade_connection.execute(
                "BEGIN TRANSACTION"
            )

            for migration_path in active_paths:
                sql = migration_path.read_text(
                    encoding="utf-8"
                )
                upgrade_connection.execute(sql)
                upgrade_executed_files += 1

            upgrade_connection.execute("COMMIT")
            upgraded_objects = object_inventory(
                upgrade_connection
            )
        except Exception as exc:
            upgrade_status = "FAIL"
            upgrade_error = repr(exc)

            try:
                upgrade_connection.execute("ROLLBACK")
            except Exception:
                pass
        finally:
            upgrade_connection.close()

        reconstruction_connection = duckdb.connect(
            str(fresh_db)
        )
        try:
            reconstruction_connection.execute(
                "BEGIN TRANSACTION"
            )

            for migration_path in active_paths:
                sql = migration_path.read_text(
                    encoding="utf-8"
                )
                reconstruction_connection.execute(sql)
                reconstructed_executed_files += 1

            reconstruction_connection.execute("COMMIT")
            reconstructed_objects = object_inventory(
                reconstruction_connection
            )
        except Exception as exc:
            reconstruction_status = "FAIL"
            reconstruction_error = repr(exc)

            try:
                reconstruction_connection.execute(
                    "ROLLBACK"
                )
            except Exception:
                pass
        finally:
            reconstruction_connection.close()
    finally:
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )

    production_sha256_after = sha256(current_db)
    production_database_modified = (
        production_sha256_before
        != production_sha256_after
    )

    upgrade_to_fresh_comparison = compare_objects(
        upgraded_objects,
        reconstructed_objects,
    )
    baseline_to_upgrade_comparison = compare_objects(
        current_objects,
        upgraded_objects,
    )

    if production_database_modified:
        disposition = (
            "PRODUCTION_DATABASE_HASH_CHANGED_REQUIRES_REPAIR"
        )
    elif upgrade_status != "PASS":
        disposition = (
            "MIGRATION_UPGRADE_EXECUTION_FAILURE_REQUIRES_REPAIR"
        )
    elif reconstruction_status != "PASS":
        disposition = (
            "MIGRATION_CHAIN_EXECUTION_FAILURE_REQUIRES_REPAIR"
        )
    elif not upgrade_to_fresh_comparison["matches"]:
        disposition = (
            "UPGRADED_AND_FRESH_SCHEMA_DRIFT_REQUIRES_RECONCILIATION"
        )
    else:
        disposition = (
            "MIGRATION_CHAIN_REPRODUCES_UPGRADED_SCHEMA"
        )

    report = {
        "generated_at_utc": (
            datetime.now(timezone.utc).isoformat()
        ),
        "current_database": {
            "path": (
                current_db.relative_to(repo).as_posix()
                if current_db.is_relative_to(repo)
                else str(current_db)
            ),
            "sha256_before": production_sha256_before,
            "sha256_after": production_sha256_after,
            "size_bytes": current_db.stat().st_size,
            "object_count": len(current_objects),
            "objects": current_objects,
        },
        "active_migrations": [
            {
                "order": migration.order,
                "path": migration.path.relative_to(
                    repo
                ).as_posix(),
                **inspect_sql(migration.path),
            }
            for migration in migrations
        ],
        "preserved_evidence": (
            [
                {
                    "path": backup_path.relative_to(
                        repo
                    ).as_posix(),
                    **inspect_sql(backup_path),
                }
            ]
            if backup_path.exists()
            else []
        ),
        "backup_comparison": {
            "available": backup_path.exists(),
            "identical": (
                sha256(active_paths[1])
                == sha256(backup_path)
                if backup_path.exists()
                else None
            ),
            "canonical_only_line_count": len(
                canonical_002_lines
                - backup_002_lines
            ),
            "backup_only_line_count": len(
                backup_002_lines
                - canonical_002_lines
            ),
            "canonical_only_lines": sorted(
                canonical_002_lines
                - backup_002_lines
            ),
            "backup_only_lines": sorted(
                backup_002_lines
                - canonical_002_lines
            ),
        },
        "temporary_upgrade": {
            "status": upgrade_status,
            "error": upgrade_error,
            "executed_files": upgrade_executed_files,
            "object_count": len(upgraded_objects),
            "objects": upgraded_objects,
        },
        "reconstruction": {
            "status": reconstruction_status,
            "error": reconstruction_error,
            "executed_files": (
                reconstructed_executed_files
            ),
            "object_count": len(
                reconstructed_objects
            ),
            "objects": reconstructed_objects,
        },
        "baseline_to_upgrade_comparison": (
            baseline_to_upgrade_comparison
        ),
        "schema_comparison": (
            upgrade_to_fresh_comparison
        ),
        "disposition": disposition,
        "production_database_modified": (
            production_database_modified
        ),
    }

    json_path = output_dir / "uip_migration_chain_reconciliation.json"
    md_path = output_dir / "UIP_MIGRATION_CHAIN_RECONCILIATION.md"

    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"TEMPORARY UPGRADE: {upgrade_status}")
    if upgrade_error:
        print(f"UPGRADE ERROR: {upgrade_error}")

    print(f"FRESH RECONSTRUCTION: {reconstruction_status}")
    if reconstruction_error:
        print(
            f"RECONSTRUCTION ERROR: "
            f"{reconstruction_error}"
        )

    print(
        f"PRODUCTION BASELINE OBJECTS: "
        f"{len(current_objects)}"
    )
    print(
        f"TEMPORARY UPGRADED OBJECTS: "
        f"{len(upgraded_objects)}"
    )
    print(
        f"FRESH RECONSTRUCTED OBJECTS: "
        f"{len(reconstructed_objects)}"
    )
    print(
        "UPGRADED VS FRESH SCHEMA MATCH: "
        f"{upgrade_to_fresh_comparison['matches']}"
    )
    print(
        "PRODUCTION DATABASE MODIFIED: "
        f"{production_database_modified}"
    )
    print(f"DISPOSITION: {disposition}")
    print(f"REPORT: {md_path}")
    print(f"JSON: {json_path}")

    passed = (
        upgrade_status == "PASS"
        and reconstruction_status == "PASS"
        and upgrade_to_fresh_comparison["matches"]
        and not production_database_modified
    )

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
