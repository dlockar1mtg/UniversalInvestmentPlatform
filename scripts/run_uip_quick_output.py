from __future__ import annotations

import argparse
import csv
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "operations" / "phase_11" / "uip_quick_output"

DOMAIN_CANDIDATES = {
    "metals": [
        ROOT / "data" / "integration" / "metals" / "uip_native_packages" / "latest",
        ROOT / "data" / "integration" / "metals" / "latest",
    ],
    "crypto": [
        Path(r"C:\Users\DevonLockard\crypto\data\operations\crypto\uip_delivery\latest"),
        ROOT / "data" / "integration" / "crypto" / "latest",
    ],
    "mtg": [
        Path(r"C:\Users\DevonLockard\mtg-investment-terminal\data\operations\mtg_uip_delivery\latest"),
        ROOT / "data" / "integration" / "mtg" / "latest",
    ],
}

REQUIRED = (
    "asset_master.csv", "forecasts.csv", "recommendations.csv",
    "risk_metrics.csv", "portfolio_positions.csv", "platform_status.csv",
    "package_summary.json",
)


def csv_count(path: Path) -> int:
    if not path.is_file():
        return -1
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return sum(1 for _ in csv.DictReader(handle))


def find_package(domain: str) -> Path | None:
    for candidate in DOMAIN_CANDIDATES[domain]:
        if candidate.is_dir() and (candidate / "package_summary.json").is_file():
            return candidate

    matches: list[Path] = []
    for search_root in {ROOT / "data", DOMAIN_CANDIDATES[domain][0].parents[2]}:
        if not search_root.exists():
            continue
        for summary in search_root.rglob("package_summary.json"):
            parent = summary.parent
            if (parent / "asset_master.csv").is_file():
                matches.append(parent)
    return max(matches, key=lambda p: (p / "package_summary.json").stat().st_mtime) if matches else None


def summary_status(payload: dict[str, Any]) -> str:
    return str(payload.get("status") or payload.get("validation_status") or "").upper()


def inspect_domain(domain: str, stage_root: Path, copy_package: bool) -> dict[str, Any]:
    package = find_package(domain)
    if package is None:
        return {"domain": domain, "status": "FAIL", "reason": "NO_DELIVERY_PACKAGE_FOUND"}

    payload = json.loads((package / "package_summary.json").read_text(encoding="utf-8"))
    missing = [name for name in REQUIRED if not (package / name).is_file()]
    counts = {
        name.removesuffix(".csv"): csv_count(package / name)
        for name in REQUIRED if name.endswith(".csv")
    }
    status = (
        "PASS"
        if summary_status(payload) in {"PASS", "CERTIFIED", "IMPORTED"} and not missing
        else "FAIL"
    )

    staged = ""
    if copy_package:
        destination = stage_root / domain / "latest"
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(package, destination)
        staged = str(destination)

    return {
        "domain": domain,
        "status": status,
        "package_path": str(package),
        "package_id": payload.get("package_id", ""),
        "generated_at_utc": payload.get("generated_at_utc", ""),
        "package_status": summary_status(payload),
        "missing_files": missing,
        "dataset_rows": counts,
        "live_overlay": payload.get("live_overlay", {}),
        "staged_in_uip": staged,
    }


def database_snapshot() -> dict[str, Any]:
    candidates = [
        ROOT / "data" / "universal" / "universal_investment.duckdb",
        ROOT / "data" / "integration" / "universal_investment.duckdb",
        ROOT / "data" / "platform.duckdb",
        ROOT / "data" / "universal_investment_platform.duckdb",
    ]
    database = next((path for path in candidates if path.is_file()), None)
    if database is None:
        found = list((ROOT / "data").rglob("*.duckdb"))
        database = max(found, key=lambda p: p.stat().st_mtime) if found else None
    if database is None:
        return {"status": "NOT_FOUND", "database_path": "", "tables": {}, "platforms": []}

    try:
        import duckdb
        connection = duckdb.connect(str(database), read_only=True)
        try:
            tables = {
                row[0] for row in connection.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
                ).fetchall()
            }
            wanted = (
                "asset_master_history", "forecasts_history",
                "recommendations_history", "risk_metrics_history",
                "portfolio_positions_history", "platform_status_history",
                "universal_packages", "universal_imports",
            )
            counts = {}
            for table in wanted:
                if table in tables:
                    counts[table] = int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            platforms = []
            if "platform_status_history" in tables:
                platforms = [
                    {"platform_id": str(row[0]), "rows": int(row[1])}
                    for row in connection.execute(
                        "SELECT platform_id, COUNT(*) FROM platform_status_history GROUP BY 1 ORDER BY 1"
                    ).fetchall()
                ]
        finally:
            connection.close()
        return {
            "status": "PASS",
            "database_path": str(database),
            "tables": counts,
            "platforms": platforms,
        }
    except Exception as exc:
        return {
            "status": "WARN",
            "database_path": str(database),
            "error": str(exc),
            "tables": {},
            "platforms": [],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify all domain deliveries and show what UIP currently contains.")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-copy", action="store_true")
    args = parser.parse_args()

    output = args.output_root.resolve()
    output.mkdir(parents=True, exist_ok=True)
    stage_root = ROOT / "data" / "integration" / "phase_11_domain_deliveries"

    domains = [
        inspect_domain(domain, stage_root, not args.no_copy)
        for domain in ("metals", "crypto", "mtg")
    ]
    database = database_snapshot()
    delivery_pass = all(item["status"] == "PASS" for item in domains)
    imported_platforms = {
        str(item.get("platform_id", "")).upper()
        for item in database.get("platforms", [])
    }
    import_coverage = {
        domain: domain.upper() in imported_platforms
        for domain in ("metals", "crypto", "mtg")
    }

    report = {
        "status": "PASS" if delivery_pass else "FAIL",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "deliveries_complete": delivery_pass,
        "domains": domains,
        "uip_database": database,
        "database_import_coverage": import_coverage,
        "all_domains_imported": all(import_coverage.values()),
        "interpretation": (
            "All three delivery packages are available. Database import coverage is reported separately."
            if delivery_pass
            else "At least one required domain delivery package is missing or incomplete."
        ),
    }
    (output / "uip_quick_output.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    rows = []
    for item in domains:
        counts = item.get("dataset_rows", {})
        rows.append({
            "domain": item["domain"],
            "delivery_status": item["status"],
            "package_id": item.get("package_id", ""),
            "generated_at_utc": item.get("generated_at_utc", ""),
            "assets": counts.get("asset_master", -1),
            "forecasts": counts.get("forecasts", -1),
            "recommendations": counts.get("recommendations", -1),
            "risk_metrics": counts.get("risk_metrics", -1),
            "portfolio_positions": counts.get("portfolio_positions", -1),
            "platform_status": counts.get("platform_status", -1),
            "imported_to_uip_database": import_coverage[item["domain"]],
            "package_path": item.get("package_path", ""),
        })

    with (output / "uip_quick_output.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    markdown = [
        "# UIP Quick Output",
        "",
        f"**Delivery status:** {'PASS' if delivery_pass else 'FAIL'}",
        f"**All domains imported to UIP database:** {'YES' if all(import_coverage.values()) else 'NO'}",
        "",
        "| Domain | Delivery | Assets | Forecasts | Recommendations | Risks | Positions | Imported DB |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        markdown.append(
            f"| {row['domain'].upper()} | {row['delivery_status']} | {row['assets']} | "
            f"{row['forecasts']} | {row['recommendations']} | {row['risk_metrics']} | "
            f"{row['portfolio_positions']} | {'YES' if row['imported_to_uip_database'] else 'NO'} |"
        )
    markdown.extend([
        "",
        f"Database: `{database.get('database_path', '') or 'Not found'}`",
        "",
        "Delivery completeness and database import completeness are intentionally reported separately.",
    ])
    (output / "UIP_QUICK_OUTPUT.md").write_text("\n".join(markdown) + "\n", encoding="utf-8")

    print("\n".join(markdown))
    print(f"\nJSON: {output / 'uip_quick_output.json'}")
    print(f"CSV: {output / 'uip_quick_output.csv'}")
    return 0 if delivery_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
