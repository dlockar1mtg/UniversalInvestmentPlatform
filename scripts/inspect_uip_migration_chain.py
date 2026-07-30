from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb


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
        f"- Current database SHA-256: `{report['current_database']['sha256']}`",
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
            "## Fresh reconstruction",
            "",
            f"- Execution result: `{report['reconstruction']['status']}`",
            f"- Executed files: `{report['reconstruction']['executed_files']}`",
            f"- Reconstructed objects: `{report['reconstruction']['object_count']}`",
            f"- Current objects: `{report['current_database']['object_count']}`",
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
    args = parser.parse_args()

    repo = args.repo.resolve()
    sql_dir = repo / "foundation" / "import_engine" / "sql"
    current_db = repo / "data" / "universal" / "universal_investment.duckdb"
    output_dir = repo / "docs" / "project_control" / "generated"
    output_dir.mkdir(parents=True, exist_ok=True)

    active_names = [
        "001_initialize_universal_database.sql",
        "002_audit_registry_integration.sql",
        "003_health_status_latest_attempt.sql",
    ]
    backup_name = "002_audit_registry_integration_before_1_3_6_2_20260717_085304.sql"

    active_paths = [sql_dir / name for name in active_names]
    backup_path = sql_dir / backup_name

    for path in [*active_paths, backup_path, current_db]:
        if not path.exists():
            raise RuntimeError(f"Required path missing: {path}")

    current_connection = duckdb.connect(str(current_db), read_only=True)
    try:
        current_objects = object_inventory(current_connection)
    finally:
        current_connection.close()

    canonical_002_lines = set(active_paths[1].read_text(encoding="utf-8").splitlines())
    backup_002_lines = set(backup_path.read_text(encoding="utf-8").splitlines())

    reconstruction_status = "PASS"
    reconstruction_error = None
    reconstructed_objects: list[dict[str, Any]] = []
    executed_files = 0

    temp_dir = Path(tempfile.mkdtemp(prefix="uip_migration_reconcile_"))
    temp_db = temp_dir / "reconstructed.duckdb"

    try:
        connection = duckdb.connect(str(temp_db))
        try:
            for migration_path in active_paths:
                sql = migration_path.read_text(encoding="utf-8")
                connection.execute(sql)
                executed_files += 1
            reconstructed_objects = object_inventory(connection)
        except Exception as exc:
            reconstruction_status = "FAIL"
            reconstruction_error = repr(exc)
        finally:
            connection.close()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    comparison = compare_objects(current_objects, reconstructed_objects)

    if reconstruction_status != "PASS":
        disposition = "MIGRATION_CHAIN_EXECUTION_FAILURE_REQUIRES_REPAIR"
    elif comparison["matches"]:
        disposition = "MIGRATION_CHAIN_REPRODUCES_CURRENT_SCHEMA"
    else:
        disposition = "MIGRATION_CHAIN_DRIFT_DETECTED_REQUIRES_RECONCILIATION"

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "current_database": {
            "path": current_db.relative_to(repo).as_posix(),
            "sha256": sha256(current_db),
            "size_bytes": current_db.stat().st_size,
            "object_count": len(current_objects),
            "objects": current_objects,
        },
        "active_migrations": [
            {
                "order": index,
                "path": path.relative_to(repo).as_posix(),
                **inspect_sql(path),
            }
            for index, path in enumerate(active_paths, start=1)
        ],
        "preserved_evidence": [
            {
                "path": backup_path.relative_to(repo).as_posix(),
                **inspect_sql(backup_path),
            }
        ],
        "backup_comparison": {
            "identical": sha256(active_paths[1]) == sha256(backup_path),
            "canonical_only_line_count": len(canonical_002_lines - backup_002_lines),
            "backup_only_line_count": len(backup_002_lines - canonical_002_lines),
            "canonical_only_lines": sorted(canonical_002_lines - backup_002_lines),
            "backup_only_lines": sorted(backup_002_lines - canonical_002_lines),
        },
        "reconstruction": {
            "status": reconstruction_status,
            "error": reconstruction_error,
            "executed_files": executed_files,
            "object_count": len(reconstructed_objects),
            "objects": reconstructed_objects,
        },
        "schema_comparison": comparison,
        "disposition": disposition,
        "production_database_modified": False,
    }

    json_path = output_dir / "uip_migration_chain_reconciliation.json"
    md_path = output_dir / "UIP_MIGRATION_CHAIN_RECONCILIATION.md"

    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"RECONSTRUCTION: {reconstruction_status}")
    if reconstruction_error:
        print(f"ERROR: {reconstruction_error}")
    print(f"CURRENT OBJECTS: {len(current_objects)}")
    print(f"RECONSTRUCTED OBJECTS: {len(reconstructed_objects)}")
    print(f"SCHEMA MATCH: {comparison['matches']}")
    print(f"DISPOSITION: {disposition}")
    print(f"REPORT: {md_path}")
    print(f"JSON: {json_path}")
    return 0 if reconstruction_status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
