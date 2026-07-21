"""Immutable CSV handoff for Metals datasets that legacy v8 does not export itself."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd


BRIDGE_SURFACES = {
    "vehicle_recommendations": (
        "latest_vehicle_recommendations.csv",
        "latest_vehicle_recommendations",
    ),
    "recommendation_history": (
        "latest_recommendation_history.csv",
        "latest_recommendation_history",
    ),
    "portfolio_risk_metrics": (
        "latest_portfolio_risk_metrics.csv",
        "latest_portfolio_risk_metrics",
    ),
    "risk_contributions": (
        "latest_risk_contributions.csv",
        "latest_risk_contributions",
    ),
    "portfolio_positions": (
        "latest_portfolio_positions.csv",
        "latest_portfolio_positions",
    ),
}
MANIFEST_NAME = "metals_bridge_export_manifest.json"


class NativeSurfaceError(RuntimeError):
    """Raised when the bridge handoff is absent, incomplete, or corrupted."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _query_view(database: Path, view: str) -> pd.DataFrame:
    if not database.exists():
        raise NativeSurfaceError(f"Metals DuckDB not found: {database}")
    connection = duckdb.connect(str(database), read_only=True)
    try:
        return connection.execute(f'SELECT * FROM "{view}"').fetchdf()
    except Exception as exc:
        raise NativeSurfaceError(f"cannot read required legacy view: {view}") from exc
    finally:
        connection.close()


def export_bridge_surfaces(metals_root: str | Path) -> Path:
    root = Path(metals_root).resolve()
    database = root / "data" / "metals_intelligence.duckdb"
    exports = root / "data" / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    stage = exports / f".metals-bridge-stage-{uuid.uuid4().hex}"
    stage.mkdir()
    generated_at = datetime.now(timezone.utc).isoformat()
    records = []
    try:
        for key, (filename, view) in BRIDGE_SURFACES.items():
            frame = _query_view(database, view)
            if frame.empty:
                raise NativeSurfaceError(f"required legacy view is empty: {view}")
            path = stage / filename
            frame.to_csv(path, index=False)
            records.append(
                {
                    "surface": key,
                    "file_name": filename,
                    "source_view": view,
                    "row_count": len(frame),
                    "sha256": _sha256(path),
                }
            )
        manifest = {
            "schema_version": "1.0",
            "source_interface": "metals-native-v8-bridge",
            "generated_at_utc": generated_at,
            "database_file": database.name,
            "surfaces": records,
        }
        manifest_path = stage / MANIFEST_NAME
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        for record in records:
            os.replace(stage / record["file_name"], exports / record["file_name"])
        os.replace(manifest_path, exports / MANIFEST_NAME)
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    return exports / MANIFEST_NAME


def _load_manifest(exports: Path) -> dict:
    path = exports / MANIFEST_NAME
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NativeSurfaceError(
            "verified Metals bridge exports are unavailable; run export_metals_bridge_surfaces.py"
        ) from exc
    if document.get("schema_version") != "1.0":
        raise NativeSurfaceError("unsupported Metals bridge manifest schema")
    surfaces = document.get("surfaces")
    if not isinstance(surfaces, list):
        raise NativeSurfaceError("Metals bridge manifest has no surface inventory")
    return document


def load_bridge_surface(
    exports: str | Path,
    surface: str,
    *,
    database: str | Path | None = None,
    allow_legacy_database_fallback: bool = False,
) -> pd.DataFrame:
    export_root = Path(exports)
    if surface not in BRIDGE_SURFACES:
        raise NativeSurfaceError(f"unknown Metals bridge surface: {surface}")
    filename, view = BRIDGE_SURFACES[surface]
    try:
        manifest = _load_manifest(export_root)
        records = {
            item.get("surface"): item
            for item in manifest["surfaces"]
            if isinstance(item, dict)
        }
        record = records.get(surface)
        if record is None or record.get("file_name") != filename:
            raise NativeSurfaceError(f"bridge manifest does not declare surface: {surface}")
        path = export_root / filename
        if not path.is_file():
            raise NativeSurfaceError(f"bridge surface file is missing: {filename}")
        if _sha256(path) != record.get("sha256"):
            raise NativeSurfaceError(f"bridge surface checksum mismatch: {filename}")
        frame = pd.read_csv(path)
        if len(frame) != record.get("row_count"):
            raise NativeSurfaceError(f"bridge surface row count mismatch: {filename}")
        if frame.empty:
            raise NativeSurfaceError(f"bridge surface is empty: {filename}")
        return frame
    except NativeSurfaceError:
        if not allow_legacy_database_fallback:
            raise
        if database is None:
            raise NativeSurfaceError("legacy database fallback requested without a database path")
        return _query_view(Path(database), view)
