"""Persist UIP-owned Metals collection outputs without the standalone Metals runtime."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_native_ingestion import ingest_collected_surfaces  # noqa: E402
from foundation.production.metals_native_store import MetalsNativeStore  # noqa: E402


def _connection():
    database_url = os.environ.get("UIIP_DATABASE_URL", "").strip()
    if database_url:
        import psycopg
        return psycopg.connect(database_url), "format"
    path = ROOT / "data" / "operations" / "metals" / "metals_native.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path), "qmark"


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist UIP-native Metals observations.")
    parser.add_argument("--benchmark", action="append", type=Path, default=[])
    parser.add_argument("--vehicle", action="append", type=Path, default=[])
    parser.add_argument("--run-id", default=f"metals-native-{uuid4().hex[:12]}")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    connection, style = _connection()
    try:
        result = ingest_collected_surfaces(
            MetalsNativeStore(connection, parameter_style=style),
            run_id=args.run_id,
            benchmark_paths=args.benchmark,
            vehicle_paths=args.vehicle,
        )
        print(json.dumps(result.__dict__, indent=2))
        print(f"METALS NATIVE INGESTION: {result.status}")
        return 0
    except Exception as exc:
        print(f"METALS NATIVE INGESTION: FAILED\n{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1 if args.strict else 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
