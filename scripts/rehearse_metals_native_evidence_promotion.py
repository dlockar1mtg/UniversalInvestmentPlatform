from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "foundation" / "import_engine" / "sql" / "011_metals_tactical_evidence_authority.sql"

FILES = {
    "components": "latest_forecast_model_components.csv",
    "regimes": "latest_learned_regime_probabilities.csv",
    "adjusted": "latest_uncertainty_adjusted_views.csv",
    "changes": "latest_recommendation_change_explanations.csv",
    "freshness": "latest_data_freshness_details.csv",
    "health": "latest_platform_health_score.csv",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def f(value: Any) -> float | None:
    if value in (None, "", "NA", "NaN", "nan", "null", "None"):
        return None
    return float(value)


def commodity_id(metal: str) -> str:
    return f"metals:commodity:{metal.strip().lower()}"


def vehicle_id(ticker: str) -> str:
    return f"metals:vehicle:{ticker.strip().upper()}"


def validate_native(rows: dict[str, list[dict[str, str]]]) -> None:
    component_groups: dict[tuple[str, int], float] = {}
    for row in rows["components"]:
        key = (row["metal"], int(row["horizon_months"]))
        component_groups[key] = component_groups.get(key, 0.0) + float(row["model_weight"])
    if not component_groups or any(not math.isclose(total, 1.0, abs_tol=1e-10) for total in component_groups.values()):
        raise RuntimeError("Model component weights do not reconcile to one by metal/horizon.")

    regime_groups: dict[str, float] = {}
    for row in rows["regimes"]:
        probability = float(row["probability"])
        if probability < 0.0 or probability > 1.0:
            raise RuntimeError("Regime probability is outside [0,1].")
        regime_groups[row["metal"]] = regime_groups.get(row["metal"], 0.0) + probability
    if not regime_groups or any(not math.isclose(total, 1.0, abs_tol=1e-10) for total in regime_groups.values()):
        raise RuntimeError("Regime probabilities do not reconcile to one by metal.")

    for row in rows["adjusted"]:
        expected = float(row["raw_expected_return"]) - float(row["uncertainty_penalty"]) - float(row["downside_penalty"])
        if not math.isclose(expected, float(row["adjusted_expected_return"]), abs_tol=1e-10):
            raise RuntimeError("Uncertainty-adjusted return arithmetic does not reconcile.")


def current_lineage(connection: duckdb.DuckDBPyConnection) -> tuple[str, str, str | None]:
    row = connection.execute(
        """
        SELECT last_package_id, last_import_id
        FROM universal_domain_operational_status
        WHERE lower(domain_id)='metals'
        """
    ).fetchone()
    if not row or not row[0] or not row[1]:
        raise RuntimeError("Current Metals package/import lineage is unavailable.")
    package_id, import_id = str(row[0]), str(row[1])
    manifests = connection.execute(
        """
        SELECT DISTINCT _manifest_sha256
        FROM forecasts_current
        WHERE lower(platform_id)='metals'
          AND _package_id=?
          AND _manifest_sha256 IS NOT NULL
        """,
        [package_id],
    ).fetchall()
    if len(manifests) > 1:
        raise RuntimeError("Current Metals authority has multiple manifest hashes.")
    manifest = str(manifests[0][0]) if manifests else None
    return package_id, import_id, manifest


def promote(connection: duckdb.DuckDBPyConnection, package_root: Path) -> dict[str, int]:
    support = package_root / "supporting_native"
    paths = {key: support / name for key, name in FILES.items()}
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing certified supporting evidence: {missing}")

    rows = {key: read_rows(path) for key, path in paths.items()}
    validate_native(rows)

    package_id, import_id, manifest = current_lineage(connection)
    summary = json.loads((package_root / "package_summary.json").read_text(encoding="utf-8"))
    if str(summary.get("package_id")) != package_id:
        raise RuntimeError(f"Package ID mismatch: source={summary.get('package_id')} current={package_id}")

    promoted_at = datetime.now(timezone.utc).isoformat()

    connection.executemany(
        "INSERT INTO metals_forecast_model_component_history VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (commodity_id(r["metal"]), r["forecast_run_id"], r["metal"], int(r["horizon_months"]), r["model_name"],
             float(r["model_forecast"]), float(r["model_weight"]), import_id, package_id, FILES["components"], i, manifest, promoted_at)
            for i, r in enumerate(rows["components"], start=1)
        ],
    )
    connection.executemany(
        "INSERT INTO metals_regime_probability_history VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (commodity_id(r["metal"]), r["forecast_run_id"], r["metal"], r["regime"], float(r["probability"]),
             import_id, package_id, FILES["regimes"], i, manifest, promoted_at)
            for i, r in enumerate(rows["regimes"], start=1)
        ],
    )
    connection.executemany(
        "INSERT INTO metals_uncertainty_adjusted_view_history VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (vehicle_id(r["ticker"]), commodity_id(r["metal"]), r["forecast_run_id"], r["ticker"], r["metal"],
             int(r["horizon_months"]), float(r["raw_expected_return"]), float(r["uncertainty_penalty"]),
             float(r["downside_penalty"]), float(r["adjusted_expected_return"]), import_id, package_id,
             FILES["adjusted"], i, manifest, promoted_at)
            for i, r in enumerate(rows["adjusted"], start=1)
        ],
    )
    connection.executemany(
        "INSERT INTO metals_recommendation_change_history VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (vehicle_id(r["ticker"]), r["decision_run_id"], r["ticker"], r.get("previous_action"), r.get("current_action"),
             f(r.get("previous_weight_pct")), f(r.get("current_weight_pct")), f(r.get("weight_change_pct")),
             f(r.get("previous_confidence")), f(r.get("current_confidence")), f(r.get("confidence_change")), r.get("explanation"),
             import_id, package_id, FILES["changes"], i, manifest, promoted_at)
            for i, r in enumerate(rows["changes"], start=1)
        ],
    )
    connection.executemany(
        "INSERT INTO metals_data_freshness_history VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (r["decision_run_id"], r["series_key"], r.get("frequency"), r.get("last_observation"), f(r.get("age_days")),
             r.get("freshness_status"), f(r.get("health_score")), r.get("message"), import_id, package_id,
             FILES["freshness"], i, manifest, promoted_at)
            for i, r in enumerate(rows["freshness"], start=1)
        ],
    )
    connection.executemany(
        "INSERT INTO metals_platform_health_history VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (r["decision_run_id"], f(r.get("data_freshness_score")), f(r.get("model_confidence_score")),
             f(r.get("recommendation_quality_score")), f(r.get("pipeline_completeness_score")),
             f(r.get("overall_platform_health")), r.get("platform_grade"), r.get("explanation"), import_id, package_id,
             FILES["health"], i, manifest, promoted_at)
            for i, r in enumerate(rows["health"], start=1)
        ],
    )
    return {key: len(value) for key, value in rows.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Rehearse Metals native-evidence promotion against an isolated database copy.")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--package-root", type=Path, required=True)
    args = parser.parse_args()

    before = sha256_file(args.database)
    if before.lower() != args.expected_sha256.lower():
        raise RuntimeError(f"Database SHA-256 mismatch: {before}")
    if not MIGRATION.is_file():
        raise FileNotFoundError(f"Migration missing: {MIGRATION}")

    with tempfile.TemporaryDirectory(prefix="uip_metals_promotion_") as tmp:
        rehearsal_db = Path(tmp) / "universal_investment_rehearsal.duckdb"
        shutil.copy2(args.database, rehearsal_db)
        connection = duckdb.connect(str(rehearsal_db))
        try:
            connection.execute(MIGRATION.read_text(encoding="utf-8"))
            connection.execute("BEGIN TRANSACTION")
            counts = promote(connection, args.package_root)
            connection.execute("COMMIT")
            observed = {
                "components": connection.execute("SELECT COUNT(*) FROM metals_forecast_model_component_current").fetchone()[0],
                "regimes": connection.execute("SELECT COUNT(*) FROM metals_regime_probability_current").fetchone()[0],
                "adjusted": connection.execute("SELECT COUNT(*) FROM metals_uncertainty_adjusted_view_current").fetchone()[0],
                "changes": connection.execute("SELECT COUNT(*) FROM metals_recommendation_change_current").fetchone()[0],
                "freshness": connection.execute("SELECT COUNT(*) FROM metals_data_freshness_current").fetchone()[0],
                "health": connection.execute("SELECT COUNT(*) FROM metals_platform_health_current").fetchone()[0],
            }
        except Exception:
            try:
                connection.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            connection.close()

    after = sha256_file(args.database)
    if after.lower() != before.lower():
        raise RuntimeError("Authoritative database changed during rehearsal.")
    if observed != counts:
        raise RuntimeError(f"Promotion count mismatch: source={counts} current={observed}")

    print(json.dumps({
        "status": "PASS",
        "mode": "ISOLATED_DATABASE_COPY_REHEARSAL",
        "production_database_mutated": False,
        "database_sha256": after,
        "package_root": str(args.package_root),
        "promoted_counts": observed,
        "next_decision": "AUTHORIZE_PRODUCTION_METALS_NATIVE_EVIDENCE_PROMOTION",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
