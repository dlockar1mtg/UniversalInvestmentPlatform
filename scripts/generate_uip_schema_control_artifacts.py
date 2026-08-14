from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb
import yaml


@dataclass(frozen=True)
class Paths:
    repo: Path
    database: Path
    sql_dir: Path
    manifest: Path
    dictionary: Path
    catalog_md: Path
    catalog_json: Path


CORE_DATASET_DESCRIPTIONS = {
    "asset_master_history": (
        "Append-only canonical history of assets published by source domains. "
        "Each row represents an observed asset record for a platform run."
    ),
    "asset_master_current": (
        "Current canonical asset view derived from asset_master_history."
    ),
    "forecasts_history": (
        "Append-only history of source and UIP forecast observations."
    ),
    "forecasts_current": (
        "Current forecast view derived from forecasts_history."
    ),
    "recommendations_history": (
        "Append-only history of recommendations and recommendation evidence."
    ),
    "recommendations_current": (
        "Current recommendation view derived from recommendations_history."
    ),
    "risk_metrics_history": (
        "Append-only history of asset-level risk measurements."
    ),
    "risk_metrics_current": (
        "Current risk-metric view derived from risk_metrics_history."
    ),
    "historical_performance_history": (
        "Append-only history of source-published historical performance, "
        "including eligibility, suppression, period, return, quality, "
        "and lineage evidence."
    ),
    "historical_performance_current": (
        "Current historical-performance record for each platform and "
        "universal asset, selected deterministically from history."
    ),
    "portfolio_positions_history": (
        "Append-only history of canonical portfolio positions imported or "
        "derived for a platform run."
    ),
    "portfolio_positions_current": (
        "Current canonical portfolio-position view."
    ),
    "platform_status_history": (
        "Append-only history of source-platform publication and run status."
    ),
    "platform_status_current": (
        "Current platform-status view."
    ),
    "macro_signals_history": (
        "Append-only history of canonical macroeconomic or market signals."
    ),
    "macro_signals_current": (
        "Current macro-signal view."
    ),
    "universal_imports": (
        "Import-attempt registry containing package, platform, timing, and "
        "outcome evidence."
    ),
    "universal_import_datasets": (
        "Dataset-level evidence for universal import attempts."
    ),
    "universal_import_errors": (
        "Detailed import-validation and activation errors."
    ),
    "universal_import_error_summary": (
        "Aggregated current import-error summary."
    ),
    "universal_import_health": (
        "Current import-health view by source platform."
    ),
    "universal_latest_import_attempt": (
        "Latest import attempt per platform."
    ),
    "universal_latest_successful_import": (
        "Latest successfully activated import per platform."
    ),
    "universal_packages": (
        "Registry of received and validated universal delivery packages."
    ),
    "universal_platform_registry": (
        "Operational import-state registry for integrated source platforms."
    ),
    "universal_domain_registry": (
        "Governed D1 registry of currently certified UIP investment domains, "
        "their ownership boundaries, publication boundaries, semantic "
        "authority, and explicit execution restrictions."
    ),
    "universal_domain_operational_status": (
        "Read-only join of governed domain authority with current universal "
        "platform import and package operational state."
    ),
    "universal_row_lineage": (
        "Lossless common row-lineage interface across certified universal "
        "history datasets and MTG native-authority history."
    ),
    "universal_lineage_with_domain": (
        "Common row lineage enriched with governed domain identity and "
        "native-semantic ownership without redefining source-domain results."
    ),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def migration_order(path: Path) -> int:
    match = re.match(r"^(\d+)", path.name)
    return int(match.group(1)) if match else 999999


def safe_query(connection: duckdb.DuckDBPyConnection, sql: str) -> list[tuple[Any, ...]]:
    try:
        return connection.execute(sql).fetchall()
    except Exception:
        return []


def build_paths(repo: Path, database: Path | None) -> Paths:
    db = database or repo / "data" / "universal" / "universal_investment.duckdb"
    return Paths(
        repo=repo,
        database=db,
        sql_dir=repo / "foundation" / "import_engine" / "sql",
        manifest=repo / "schemas" / "database" / "schema_manifest.yaml",
        dictionary=repo / "docs" / "project_control" / "UIP_DATA_DICTIONARY.md",
        catalog_md=repo / "docs" / "project_control" / "generated" / "UIP_DATABASE_SCHEMA_CATALOG.md",
        catalog_json=repo / "docs" / "project_control" / "generated" / "uip_database_schema_catalog.json",
    )


def inspect_migrations(paths: Paths) -> list[dict[str, Any]]:
    all_sql_files = sorted(
        paths.sql_dir.glob("*.sql"),
        key=lambda p: (migration_order(p), p.name.lower()),
    )

    canonical_pattern = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$")

    sql_files = [
        path
        for path in all_sql_files
        if canonical_pattern.fullmatch(path.name)
        and "_before_" not in path.name.lower()
        and "_backup_" not in path.name.lower()
    ]

    ignored_sql_files = [
        path
        for path in all_sql_files
        if path not in sql_files
    ]

    if not sql_files:
        raise RuntimeError(f"No canonical SQL files found under {paths.sql_dir}")

    migrations: list[dict[str, Any]] = []
    previous_order: int | None = None
    duplicate_orders: set[int] = set()

    seen: set[int] = set()
    for sql_file in sql_files:
        order = migration_order(sql_file)
        if order in seen:
            duplicate_orders.add(order)
        seen.add(order)

        migrations.append(
            {
                "order": order,
                "filename": sql_file.name,
                "path": sql_file.relative_to(paths.repo).as_posix(),
                "sha256": sha256(sql_file),
                "size_bytes": sql_file.stat().st_size,
                "purpose": infer_migration_purpose(sql_file),
            }
        )
        previous_order = order

    if duplicate_orders:
        raise RuntimeError(
            "Duplicate migration order prefixes found: "
            + ", ".join(str(value) for value in sorted(duplicate_orders))
        )

    for ignored_file in ignored_sql_files:
        print(
            "Ignoring non-canonical SQL evidence file: "
            f"{ignored_file.relative_to(paths.repo).as_posix()}"
        )

    return migrations


def infer_migration_purpose(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace").lower()
    labels: list[str] = []
    if "create table" in text:
        labels.append("create or extend canonical tables")
    if "create view" in text:
        labels.append("create or replace canonical views")
    if "audit" in text or "registry" in text:
        labels.append("import audit and platform registry")
    if "alter table" in text:
        labels.append("schema migration")
    return "; ".join(labels) or "ordered database schema operation"


def inspect_database(paths: Paths) -> dict[str, Any]:
    if not paths.database.exists():
        raise RuntimeError(f"Database not found: {paths.database}")

    connection = duckdb.connect(str(paths.database), read_only=True)
    try:
        object_rows = connection.execute(
            """
            SELECT table_schema, table_name, table_type
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
            ORDER BY table_schema, table_name
            """
        ).fetchall()

        view_definitions = {
            (row[0], row[1]): row[2]
            for row in safe_query(
                connection,
                """
                SELECT schema_name, view_name, sql
                FROM duckdb_views()
                WHERE internal = false
                """,
            )
        }

        constraints_by_table: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in safe_query(
            connection,
            """
            SELECT
                schema_name,
                table_name,
                constraint_type,
                constraint_text,
                expression
            FROM duckdb_constraints()
            ORDER BY schema_name, table_name, constraint_index
            """,
        ):
            key = (row[0], row[1])
            constraints_by_table.setdefault(key, []).append(
                {
                    "type": row[2],
                    "text": row[3],
                    "expression": row[4],
                }
            )

        indexes_by_table: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in safe_query(
            connection,
            """
            SELECT
                schema_name,
                table_name,
                index_name,
                is_unique,
                expressions,
                sql
            FROM duckdb_indexes()
            WHERE internal = false
            ORDER BY schema_name, table_name, index_name
            """,
        ):
            key = (row[0], row[1])
            indexes_by_table.setdefault(key, []).append(
                {
                    "name": row[2],
                    "unique": bool(row[3]),
                    "expressions": row[4],
                    "sql": row[5],
                }
            )

        objects: list[dict[str, Any]] = []
        for schema_name, object_name, object_type in object_rows:
            quoted = f'"{schema_name}"."{object_name}"'
            row_count = connection.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]

            columns = connection.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    ordinal_position
                FROM information_schema.columns
                WHERE table_schema = ?
                  AND table_name = ?
                ORDER BY ordinal_position
                """,
                [schema_name, object_name],
            ).fetchall()

            objects.append(
                {
                    "schema": schema_name,
                    "name": object_name,
                    "qualified_name": f"{schema_name}.{object_name}",
                    "type": object_type,
                    "row_count": row_count,
                    "description": CORE_DATASET_DESCRIPTIONS.get(
                        object_name,
                        "Database object discovered through read-only DuckDB introspection.",
                    ),
                    "columns": [
                        {
                            "position": position,
                            "name": column_name,
                            "data_type": data_type,
                            "nullable": nullable == "YES",
                            "default": default,
                        }
                        for column_name, data_type, nullable, default, position in columns
                    ],
                    "constraints": constraints_by_table.get((schema_name, object_name), []),
                    "indexes": indexes_by_table.get((schema_name, object_name), []),
                    "view_definition": view_definitions.get((schema_name, object_name)),
                }
            )

        return {
            "database_path": (
            paths.database.relative_to(paths.repo).as_posix()
            if paths.database.is_relative_to(paths.repo)
            else str(paths.database)
        ),
            "database_size_bytes": paths.database.stat().st_size,
            "database_sha256": sha256(paths.database),
            "inspected_at_utc": datetime.now(timezone.utc).isoformat(),
            "read_only": True,
            "object_count": len(objects),
            "objects": objects,
        }
    finally:
        connection.close()


def build_manifest(paths: Paths, migrations: list[dict[str, Any]], catalog: dict[str, Any]) -> dict[str, Any]:
    return {
        "manifest_version": 1,
        "platform": "Universal Investment Platform",
        "database_engine": "DuckDB",
        "authority": {
            "migration_manifest": paths.manifest.relative_to(paths.repo).as_posix(),
            "migration_directory": paths.sql_dir.relative_to(paths.repo).as_posix(),
            "generated_catalog_json": paths.catalog_json.relative_to(paths.repo).as_posix(),
            "generated_catalog_markdown": paths.catalog_md.relative_to(paths.repo).as_posix(),
            "semantic_dictionary": paths.dictionary.relative_to(paths.repo).as_posix(),
        },
        "generation": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_database": catalog["database_path"],
            "source_database_sha256": catalog["database_sha256"],
            "read_only_introspection": True,
        },
        "migration_policy": {
            "ordered_by_numeric_filename_prefix": True,
            "fresh_database_initialization_uses_full_chain": True,
            "production_changes_require_new_ordered_migration": True,
            "editing_prior_migration_for_deployed_schema_change_is_prohibited": True,
        },
        "migrations": migrations,
        "observed_database": {
            "object_count": catalog["object_count"],
            "tables": sum(1 for item in catalog["objects"] if item["type"] == "BASE TABLE"),
            "views": sum(1 for item in catalog["objects"] if item["type"] == "VIEW"),
        },
    }


def render_catalog_markdown(catalog: dict[str, Any], migrations: list[dict[str, Any]]) -> str:
    lines = [
        "# UIP Database Schema Catalog",
        "",
        "## Generation evidence",
        "",
        f"- Database: `{catalog['database_path']}`",
        f"- Database SHA-256: `{catalog['database_sha256']}`",
        f"- Database size: `{catalog['database_size_bytes']}` bytes",
        f"- Inspected at: `{catalog['inspected_at_utc']}`",
        "- Inspection mode: `READ_ONLY`",
        f"- Database objects: `{catalog['object_count']}`",
        f"- Ordered SQL files: `{len(migrations)}`",
        "",
        "This catalog is generated from read-only DuckDB introspection. "
        "It records observed implementation evidence; it does not by itself authorize a schema change.",
        "",
        "## Ordered SQL authority inventory",
        "",
        "| Order | File | SHA-256 | Purpose |",
        "|---:|---|---|---|",
    ]

    for migration in migrations:
        lines.append(
            f"| {migration['order']} | `{migration['path']}` | "
            f"`{migration['sha256']}` | {migration['purpose']} |"
        )

    lines.extend(["", "## Database objects", ""])

    for item in catalog["objects"]:
        lines.extend(
            [
                f"### `{item['qualified_name']}`",
                "",
                f"- Type: `{item['type']}`",
                f"- Observed rows: `{item['row_count']}`",
                f"- Description: {item['description']}",
                "",
                "| Position | Column | Type | Nullable | Default |",
                "|---:|---|---|---|---|",
            ]
        )
        for column in item["columns"]:
            default = "" if column["default"] is None else str(column["default"]).replace("|", "\\|")
            lines.append(
                f"| {column['position']} | `{column['name']}` | "
                f"`{column['data_type']}` | "
                f"`{'YES' if column['nullable'] else 'NO'}` | `{default}` |"
            )

        if item["constraints"]:
            lines.extend(["", "**Constraints**", ""])
            for constraint in item["constraints"]:
                lines.append(f"- `{constraint['type']}`: `{constraint['text']}`")

        if item["indexes"]:
            lines.extend(["", "**Indexes**", ""])
            for index in item["indexes"]:
                lines.append(
                    f"- `{index['name']}`; unique=`{str(index['unique']).lower()}`; "
                    f"expressions=`{index['expressions']}`"
                )

        if item["view_definition"]:
            lines.extend(
                [
                    "",
                    "<details>",
                    "<summary>View definition</summary>",
                    "",
                    "```sql",
                    item["view_definition"].strip(),
                    "```",
                    "",
                    "</details>",
                ]
            )
        lines.append("")

    lines.extend(
        [
            "## Interpretation rule",
            "",
            "When the migration chain, observed production schema, generated catalog, and "
            "semantic dictionary disagree, stop and reconcile the discrepancy. Do not silently "
            "treat generated documentation as migration authority.",
            "",
        ]
    )
    return "\n".join(lines)


def render_dictionary(catalog: dict[str, Any]) -> str:
    lines = [
        "# UIP Data Dictionary",
        "",
        "## Purpose",
        "",
        "This dictionary defines the semantic meaning of canonical UIP database objects. "
        "Physical columns and types are generated in `generated/UIP_DATABASE_SCHEMA_CATALOG.md`.",
        "",
        "## Authority and usage",
        "",
        "- Ordered migrations control physical schema changes.",
        "- The generated catalog records the observed database implementation.",
        "- This dictionary controls semantic interpretation.",
        "- Source systems own native facts; certified packages own published snapshots; "
        "UIP owns imported canonical and portfolio-level truth.",
        "- History tables preserve observations. Current views select the applicable latest record.",
        "",
        "## Shared terms",
        "",
        "| Term | Meaning |",
        "|---|---|",
        "| Run | One identifiable source publication, import, or UIP processing execution. |",
        "| Package | Immutable certified delivery snapshot with identifiers, hashes, and validation evidence. |",
        "| Platform | Registered source domain or UIP-owned publishing subsystem. |",
        "| Universal asset ID | Canonical cross-domain asset identifier used inside UIP. |",
        "| History table | Append-oriented record of observations across runs. |",
        "| Current view | Deterministic latest applicable record derived from history. |",
        "| Eligibility | Whether an asset or analytical record may participate in a stated process. |",
        "| Suppression | Explicit exclusion with a reason; never silent disappearance. |",
        "| Lineage | Evidence linking a result to source, package, run, model, contract, and transformation. |",
        "",
        "## Canonical objects",
        "",
    ]

    for item in catalog["objects"]:
        lines.extend(
            [
                f"### `{item['qualified_name']}`",
                "",
                item["description"],
                "",
                f"- Physical type: `{item['type']}`",
                f"- Observed rows during generation: `{item['row_count']}`",
                f"- Column definitions: see the generated schema catalog.",
                "",
            ]
        )

    lines.extend(
        [
            "## Null, status, and coverage rules",
            "",
            "- Missing analytics must use nulls and explicit status, confidence, eligibility, "
            "or suppression fields where the contract provides them.",
            "- An asset must not silently disappear because a forecast, recommendation, risk "
            "metric, price, or historical-performance record is unavailable.",
            "- Current views must be deterministic and traceable to history rows.",
            "- Decision-relevant records require complete lineage.",
            "",
            "## Historical-performance semantic contract",
            "",
            "`historical_performance_history` and `historical_performance_current` are active "
            "schema objects introduced through the ordered historical-performance migration. "
            "They preserve universal historical-performance evidence and expose the latest "
            "observation for each platform and universal asset.",
            "",
            "Semantic purpose:",
            "",
            "- preserve point-in-time performance evidence published by a source domain;",
            "- distinguish eligible from suppressed performance observations;",
            "- retain horizon, period, benchmark, quality, and lineage context;",
            "- support current performance views without overwriting history;",
            "- prohibit unknown universal asset identifiers.",
            "",
            "## Change control",
            "",
            "A semantic change requires a change-ledger entry when it materially alters "
            "cross-domain meaning, portfolio behavior, certification, lineage, or user interpretation.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    paths: Paths,
    migrations: list[dict[str, Any]],
    catalog: dict[str, Any],
    manifest: dict[str, Any],
) -> None:
    for parent in {
        paths.manifest.parent,
        paths.dictionary.parent,
        paths.catalog_md.parent,
        paths.catalog_json.parent,
    }:
        parent.mkdir(parents=True, exist_ok=True)

    paths.manifest.write_text(
        yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    paths.catalog_json.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    paths.catalog_md.write_text(
        render_catalog_markdown(catalog, migrations),
        encoding="utf-8",
    )
    paths.dictionary.write_text(
        render_dictionary(catalog),
        encoding="utf-8",
    )


def validate(paths: Paths) -> list[str]:
    errors: list[str] = []

    required = [
        paths.manifest,
        paths.dictionary,
        paths.catalog_md,
        paths.catalog_json,
    ]
    for path in required:
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"Missing or empty artifact: {path}")

    if errors:
        return errors

    manifest = yaml.safe_load(paths.manifest.read_text(encoding="utf-8"))
    catalog = json.loads(paths.catalog_json.read_text(encoding="utf-8"))
    catalog_md = paths.catalog_md.read_text(encoding="utf-8")
    dictionary = paths.dictionary.read_text(encoding="utf-8")

    migrations = manifest.get("migrations", [])
    orders = [item["order"] for item in migrations]
    if orders != sorted(orders):
        errors.append("Manifest migration order is not sorted.")
    if len(orders) != len(set(orders)):
        errors.append("Manifest contains duplicate migration orders.")

    for migration in migrations:
        source = paths.repo / migration["path"]
        if not source.exists():
            errors.append(f"Manifest migration missing: {migration['path']}")
            continue
        if sha256(source) != migration["sha256"]:
            errors.append(f"Manifest hash mismatch: {migration['path']}")

    if catalog["object_count"] != len(catalog["objects"]):
        errors.append("Catalog object_count does not match object list.")

    for item in catalog["objects"]:
        qualified_name = item["qualified_name"]
        if f"`{qualified_name}`" not in catalog_md:
            errors.append(f"Markdown catalog missing object: {qualified_name}")
        if f"`{qualified_name}`" not in dictionary:
            errors.append(f"Data dictionary missing object: {qualified_name}")

    expected_baseline_objects = {
        "main.asset_master_history",
        "main.asset_master_current",
        "main.forecasts_history",
        "main.forecasts_current",
        "main.recommendations_history",
        "main.recommendations_current",
        "main.risk_metrics_history",
        "main.risk_metrics_current",
        "main.portfolio_positions_history",
        "main.portfolio_positions_current",
        "main.platform_status_history",
        "main.platform_status_current",
        "main.universal_imports",
        "main.universal_packages",
        "main.universal_platform_registry",
    }
    observed = {item["qualified_name"] for item in catalog["objects"]}
    missing = sorted(expected_baseline_objects - observed)
    if missing:
        errors.append("Expected baseline objects missing: " + ", ".join(missing))

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate and validate UIP schema-control artifacts."
    )
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="UIP repository root.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=None,
        help="Optional DuckDB path; defaults to data/universal/universal_investment.duckdb.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate existing artifacts without regenerating them.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo = args.repo.resolve()
    paths = build_paths(repo, args.database.resolve() if args.database else None)

    if not args.validate_only:
        migrations = inspect_migrations(paths)
        catalog = inspect_database(paths)
        manifest = build_manifest(paths, migrations, catalog)
        write_outputs(paths, migrations, catalog, manifest)

    errors = validate(paths)
    if errors:
        print("SCHEMA CONTROL VALIDATION: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    catalog = json.loads(paths.catalog_json.read_text(encoding="utf-8"))
    manifest = yaml.safe_load(paths.manifest.read_text(encoding="utf-8"))

    print("SCHEMA CONTROL VALIDATION: PASS")
    print(f"Database objects: {catalog['object_count']}")
    print(f"Ordered SQL files: {len(manifest['migrations'])}")
    print(f"Manifest: {paths.manifest}")
    print(f"Dictionary: {paths.dictionary}")
    print(f"Catalog Markdown: {paths.catalog_md}")
    print(f"Catalog JSON: {paths.catalog_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
