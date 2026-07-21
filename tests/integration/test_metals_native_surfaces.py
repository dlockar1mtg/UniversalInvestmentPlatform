from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from exchange.metals.adapter.native_surfaces import (
    BRIDGE_SURFACES,
    MANIFEST_NAME,
    NativeSurfaceError,
    export_bridge_surfaces,
    load_bridge_surface,
)


def build_database(root: Path, *, omit: str | None = None) -> Path:
    database = root / "data" / "metals_intelligence.duckdb"
    database.parent.mkdir(parents=True)
    connection = duckdb.connect(str(database))
    try:
        for key, (_, view) in BRIDGE_SURFACES.items():
            if key == omit:
                continue
            connection.execute(
                f"""CREATE VIEW "{view}" AS
                SELECT '{key}' AS surface_name, 1 AS record_value"""
            )
    finally:
        connection.close()
    return database


def test_bridge_export_is_complete_and_self_verifying(tmp_path: Path) -> None:
    build_database(tmp_path)
    manifest_path = export_bridge_surfaces(tmp_path)
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_path.name == MANIFEST_NAME
    assert len(document["surfaces"]) == 5
    assert sum(item["row_count"] for item in document["surfaces"]) == 5
    for key, (filename, view) in BRIDGE_SURFACES.items():
        record = next(item for item in document["surfaces"] if item["surface"] == key)
        assert record["file_name"] == filename
        assert record["source_view"] == view
        assert len(record["sha256"]) == 64


def test_verified_surfaces_load_after_legacy_database_is_removed(tmp_path: Path) -> None:
    database = build_database(tmp_path)
    export_bridge_surfaces(tmp_path)
    database.unlink()
    exports = tmp_path / "data" / "exports"
    for key in BRIDGE_SURFACES:
        frame = load_bridge_surface(exports, key)
        assert frame.iloc[0]["surface_name"] == key


def test_bridge_surface_rejects_checksum_drift(tmp_path: Path) -> None:
    build_database(tmp_path)
    export_bridge_surfaces(tmp_path)
    exports = tmp_path / "data" / "exports"
    filename = BRIDGE_SURFACES["portfolio_positions"][0]
    with (exports / filename).open("a", encoding="utf-8") as handle:
        handle.write("\ntampered,2\n")
    with pytest.raises(NativeSurfaceError, match="checksum mismatch"):
        load_bridge_surface(exports, "portfolio_positions")


def test_database_fallback_requires_explicit_authorization(tmp_path: Path) -> None:
    database = build_database(tmp_path)
    exports = tmp_path / "data" / "exports"
    with pytest.raises(NativeSurfaceError, match="verified Metals bridge exports"):
        load_bridge_surface(exports, "portfolio_positions", database=database)
    frame = load_bridge_surface(
        exports,
        "portfolio_positions",
        database=database,
        allow_legacy_database_fallback=True,
    )
    assert frame.iloc[0]["surface_name"] == "portfolio_positions"


def test_failed_export_does_not_publish_manifest(tmp_path: Path) -> None:
    build_database(tmp_path, omit="risk_contributions")
    with pytest.raises(NativeSurfaceError, match="required legacy view"):
        export_bridge_surfaces(tmp_path)
    assert not (tmp_path / "data" / "exports" / MANIFEST_NAME).exists()
