"""Governed manual Crypto production cycle owned by UIP.

The cycle is fail-closed:
1. invoke the standalone Crypto production pipeline;
2. prepare and validate its UIP delivery;
3. promote the certified universal package into UIP;
4. validate and transactionally import it;
5. publish UIP-controlled Crypto intelligence and dashboard datasets.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile

import duckdb

from foundation.import_engine.audit import (
    apply_audit_registry_migration,
    synchronize_successful_import,
)
from foundation.import_engine.config import ImportEngineConfig
from foundation.import_engine.database import initialize_database
from foundation.import_engine.exceptions import DuplicatePackageError
from foundation.import_engine.integrity import validate_package_integrity
from foundation.import_engine.loader import import_package
from foundation.import_engine.package import discover_package

DELIVERY_CONTRACT = "uip-crypto-delivery-v1"
PLATFORM_ID = "crypto"
REQUIRED_FILES = {
    "asset_master.csv",
    "forecasts.csv",
    "platform_status.csv",
    "portfolio_positions.csv",
    "recommendations.csv",
    "risk_metrics.csv",
    "export_manifest.csv",
    "package_summary.json",
    "validation_report.json",
}


@dataclass(frozen=True)
class CryptoProductionResult:
    status: str
    source_run_id: str
    package_id: str
    import_id: str
    imported_rows: int
    dashboard_rows: int
    intelligence_rows: int
    source_command_ran: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _run(command: list[str], cwd: Path) -> None:
    print("\n>", " ".join(command))
    completed = subprocess.run(command, cwd=cwd)
    if completed.returncode:
        raise RuntimeError(
            f"Command failed with exit code {completed.returncode}: "
            + " ".join(command)
        )


def latest_run_summary(crypto_root: Path) -> Path:
    production_root = crypto_root / "data" / "operations" / "crypto" / "production_runs"
    candidates = sorted(production_root.glob("*/run_summary.json"))
    if not candidates:
        raise FileNotFoundError(
            f"No Crypto production run summary found under {production_root}"
        )
    return candidates[-1]


def invoke_crypto_production(crypto_root: Path) -> Path:
    _run(
        [sys.executable, "scripts/run_crypto_production_pipeline.py"],
        crypto_root,
    )
    summary_path = latest_run_summary(crypto_root)
    summary = _read_json(summary_path)
    if summary.get("status") != "PASS":
        raise ValueError("Latest Crypto production run is not PASS")
    if not isinstance(summary.get("universal_export"), dict):
        raise ValueError("Crypto production summary has no universal export")
    if summary["universal_export"].get("status") != "PASS":
        raise ValueError("Crypto universal export is not PASS")
    return summary_path


def prepare_crypto_delivery(crypto_root: Path, summary_path: Path) -> Path:
    output_root = crypto_root / "data" / "operations" / "crypto" / "uip_delivery"
    _run(
        [
            sys.executable,
            "scripts/prepare_crypto_uip_delivery.py",
            "--run-summary",
            str(summary_path.resolve()),
            "--output-root",
            str(output_root.resolve()),
        ],
        crypto_root,
    )
    return output_root / "latest.json"


def validate_delivery(latest_pointer: Path) -> tuple[dict[str, Any], Path]:
    pointer = _read_json(latest_pointer.resolve())
    delivery_dir = Path(str(pointer.get("delivery_directory", ""))).resolve()
    manifest_path = Path(str(pointer.get("manifest", ""))).resolve()
    if not delivery_dir.is_dir():
        raise FileNotFoundError(f"Crypto delivery directory not found: {delivery_dir}")
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Crypto delivery manifest not found: {manifest_path}")
    try:
        manifest_path.relative_to(delivery_dir)
    except ValueError as exc:
        raise ValueError("Crypto delivery manifest escapes delivery directory") from exc

    manifest = _read_json(manifest_path)
    checks = {
        "status": manifest.get("status") == "PASS",
        "contract": manifest.get("delivery_contract") == DELIVERY_CONTRACT,
        "run_id": str(manifest.get("run_id", "")) == str(pointer.get("run_id", "")),
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Crypto delivery contract failed: {failed}")

    by_name = {
        str(row.get("name")): row
        for row in manifest.get("files", [])
        if isinstance(row, dict) and row.get("name")
    }
    missing = sorted(REQUIRED_FILES - set(by_name))
    if missing:
        raise ValueError(f"Crypto delivery manifest is incomplete: {missing}")

    for name in sorted(REQUIRED_FILES):
        path = delivery_dir / name
        metadata = by_name[name]
        if not path.is_file():
            raise FileNotFoundError(f"Missing Crypto delivery file: {name}")
        if _sha256(path) != str(metadata.get("sha256", "")):
            raise ValueError(f"Crypto delivery checksum mismatch: {name}")

    summary = _read_json(delivery_dir / "package_summary.json")
    if summary.get("status") != "PASS":
        raise ValueError("Crypto package summary is not PASS")
    if str(summary.get("platform_id", "")).lower() != PLATFORM_ID:
        raise ValueError("Crypto package platform_id is not crypto")
    return manifest, delivery_dir


def promote_package(source: Path, destination: Path) -> Path:
    destination = destination.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="crypto-uip-", dir=destination.parent) as temp:
        stage = Path(temp) / "latest"
        shutil.copytree(source, stage)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(stage), str(destination))
    return destination


def publish_uip_datasets(
    config: ImportEngineConfig,
    package_id: str,
    output_root: Path,
) -> tuple[int, int]:
    connection = duckdb.connect(str(config.database_path), read_only=True)
    try:
        dashboard_columns = [
            "universal_asset_id", "asset_name", "asset_symbol", "asset_class",
            "asset_subclass", "currency", "investable", "active",
            "last_observed_date", "notes", "metadata_json",
        ]
        dashboard_rows_raw = connection.execute(
            """
            SELECT universal_asset_id, asset_name, asset_symbol, asset_class,
                   asset_subclass, currency, investable, active,
                   last_observed_date, notes, metadata_json
            FROM asset_master_history
            WHERE lower(platform_id) = 'crypto' AND _package_id = ?
            ORDER BY universal_asset_id
            """,
            [package_id],
        ).fetchall()
        dashboard_rows = [dict(zip(dashboard_columns, row)) for row in dashboard_rows_raw]

        intelligence_columns = [
            "record_type", "universal_asset_id", "asset_name", "horizon_months",
            "point_forecast", "lower_bound", "upper_bound", "expected_return",
            "recommendation", "normalized_score", "confidence_score",
            "risk_level", "risk_score", "generated_at_utc", "metadata_json",
        ]
        intelligence_rows_raw = connection.execute(
            """
            WITH assets AS (
                SELECT universal_asset_id, asset_name
                FROM asset_master_history
                WHERE lower(platform_id) = 'crypto' AND _package_id = ?
            )
            SELECT 'FORECAST', f.universal_asset_id, a.asset_name,
                   f.forecast_horizon_months, f.point_forecast, f.lower_bound,
                   f.upper_bound, f.expected_return, NULL, NULL,
                   f.confidence_score, NULL, NULL, f.generated_at_utc,
                   f.metadata_json
            FROM forecasts_history f
            JOIN assets a USING (universal_asset_id)
            WHERE lower(f.platform_id) = 'crypto' AND f._package_id = ?
            UNION ALL
            SELECT 'RECOMMENDATION', r.universal_asset_id, a.asset_name,
                   r.time_horizon_months, NULL, NULL, NULL, NULL,
                   r.recommendation, r.normalized_score, r.confidence_score,
                   NULL, NULL, r.generated_at_utc, r.metadata_json
            FROM recommendations_history r
            JOIN assets a USING (universal_asset_id)
            WHERE lower(r.platform_id) = 'crypto' AND r._package_id = ?
            UNION ALL
            SELECT 'RISK', k.universal_asset_id, a.asset_name,
                   NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                   k.risk_level, k.risk_score, k.generated_at_utc,
                   k.metadata_json
            FROM risk_metrics_history k
            JOIN assets a USING (universal_asset_id)
            WHERE lower(k.platform_id) = 'crypto' AND k._package_id = ?
            ORDER BY 2, 1, 4 NULLS LAST
            """,
            [package_id, package_id, package_id, package_id],
        ).fetchall()
        intelligence_rows = [
            dict(zip(intelligence_columns, row)) for row in intelligence_rows_raw
        ]
    finally:
        connection.close()

    output_root.mkdir(parents=True, exist_ok=True)
    _write_csv(output_root / "crypto_dashboard.csv", dashboard_columns, dashboard_rows)
    _write_csv(
        output_root / "crypto_intelligence.csv",
        intelligence_columns,
        intelligence_rows,
    )
    (output_root / "publication_status.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "published_at_utc": _utc_now(),
                "package_id": package_id,
                "dashboard_rows": len(dashboard_rows),
                "intelligence_rows": len(intelligence_rows),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return len(dashboard_rows), len(intelligence_rows)


def run_crypto_production_cycle(
    repository_root: Path,
    crypto_root: Path,
    *,
    skip_source_run: bool = False,
) -> CryptoProductionResult:
    repository_root = repository_root.resolve()
    crypto_root = crypto_root.resolve()
    if not crypto_root.is_dir():
        raise FileNotFoundError(str(crypto_root))

    source_command_ran = not skip_source_run
    if skip_source_run:
        summary_path = latest_run_summary(crypto_root)
        latest_pointer = crypto_root / "data" / "operations" / "crypto" / "uip_delivery" / "latest.json"
        if not latest_pointer.is_file():
            latest_pointer = prepare_crypto_delivery(crypto_root, summary_path)
    else:
        summary_path = invoke_crypto_production(crypto_root)
        latest_pointer = prepare_crypto_delivery(crypto_root, summary_path)

    source_summary = _read_json(summary_path)
    _, delivery_dir = validate_delivery(latest_pointer)
    latest_package = promote_package(
        delivery_dir,
        repository_root / "data" / "integration" / "crypto" / "latest",
    )

    config = ImportEngineConfig.from_repository_root(repository_root)
    initialize_database(config)
    apply_audit_registry_migration(config)
    package = discover_package(latest_package)
    validation = validate_package_integrity(package)
    if not validation.passed:
        raise RuntimeError(
            f"Crypto package integrity failed with {validation.error_count} error(s)"
        )

    import_id = ""
    imported_rows = 0
    try:
        imported = import_package(config, latest_package)
        import_id = imported.import_id
        imported_rows = imported.imported_row_count
        synchronize_successful_import(config, import_id=imported.import_id)
    except DuplicatePackageError:
        connection = duckdb.connect(str(config.database_path), read_only=True)
        try:
            row = connection.execute(
                """
                SELECT successful_import_id
                FROM universal_packages
                WHERE package_id = ? AND package_status = 'IMPORTED'
                """,
                [package.identity.package_id],
            ).fetchone()
            if not row or not row[0]:
                raise
            import_id = str(row[0])
            imported_rows = int(
                connection.execute(
                    "SELECT imported_row_count FROM universal_imports WHERE import_id = ?",
                    [import_id],
                ).fetchone()[0]
            )
        finally:
            connection.close()

    dashboard_rows, intelligence_rows = publish_uip_datasets(
        config,
        package.identity.package_id,
        repository_root / "data" / "operations" / "uip_crypto" / "latest",
    )
    result = CryptoProductionResult(
        status="PASS",
        source_run_id=str(source_summary.get("run_id", "")),
        package_id=package.identity.package_id,
        import_id=import_id,
        imported_rows=imported_rows,
        dashboard_rows=dashboard_rows,
        intelligence_rows=intelligence_rows,
        source_command_ran=source_command_ran,
    )
    state_root = repository_root / "data" / "operations" / "uip_crypto"
    state_root.mkdir(parents=True, exist_ok=True)
    (state_root / "last_successful_cycle.json").write_text(
        json.dumps(asdict(result), indent=2) + "\n",
        encoding="utf-8",
    )
    return result
