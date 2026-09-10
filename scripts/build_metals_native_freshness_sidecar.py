"""Build UIP-native Metals data-freshness sidecar from current production inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

AUTHORITY_ID = "UIP_NATIVE_METALS_DATA_FRESHNESS_V1"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def load_contract(path: Path) -> dict:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("authority_id") != AUTHORITY_ID:
        raise RuntimeError("unexpected freshness authority_id")
    if contract.get("legacy_equivalent") is not False:
        raise RuntimeError("native freshness V1 must explicitly remain non-legacy-equivalent")
    return contract


def age_days(observed: str, as_of: date) -> int:
    age = (as_of - date.fromisoformat(observed)).days
    if age < 0:
        raise RuntimeError(f"future observation date is not allowed: {observed}")
    return age


def classify(age: int, policy: dict) -> str:
    current = int(policy["current_max_age_days"])
    stale_after = int(policy["stale_after_days"])
    if current < 0 or stale_after <= current:
        raise RuntimeError("invalid freshness thresholds")
    if age <= current:
        return "CURRENT"
    if age <= stale_after:
        return "AGING"
    return "STALE"


def health_score(age: int, policy: dict) -> float:
    stale_after = int(policy["stale_after_days"])
    return round(max(0.0, 100.0 * (1.0 - (age / stale_after))), 2)


def build_row(*, series_key: str, source: str, observed: str, as_of: date, policies: dict) -> dict[str, object]:
    if source not in policies:
        raise RuntimeError(f"unrecognized governed freshness source: {source}")
    policy = policies[source]
    age = age_days(observed, as_of)
    status = classify(age, policy)
    frequency = str(policy["frequency"])
    current = int(policy["current_max_age_days"])
    stale_after = int(policy["stale_after_days"])
    score = health_score(age, policy)
    message = (
        f"{status}: {series_key} latest {frequency.lower()} observation {observed} is {age} days old; "
        f"CURRENT <= {current} days and STALE > {stale_after} days under {AUTHORITY_ID}."
    )
    return {
        "series_key": series_key,
        "frequency": frequency,
        "last_observation": observed,
        "age_days": age,
        "freshness_status": status,
        "health_score": f"{score:.2f}",
        "message": message,
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--daily-market", type=Path, required=True)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/presentation/metals_data_freshness_v1.json"),
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    contract = load_contract(args.contract)
    policies = contract["source_policies"]
    benchmark = read_csv(args.benchmark)
    daily = read_csv(args.daily_market)
    if not benchmark or not daily:
        raise RuntimeError("benchmark and daily-market inputs must both be non-empty")

    rows: list[dict[str, object]] = []
    for item in benchmark:
        source = item["source"].strip().lower()
        rows.append(
            build_row(
                series_key=item["series_id"].strip(),
                source=source,
                observed=item["observation_date"].strip(),
                as_of=args.as_of,
                policies=policies,
            )
        )

    for item in daily:
        ticker = item["ticker"].strip().upper()
        rows.append(
            build_row(
                series_key=f"metals:vehicle:{ticker}",
                source="yfinance_daily_market_input",
                observed=item["trading_date"].strip(),
                as_of=args.as_of,
                policies=policies,
            )
        )

    rows.sort(key=lambda row: str(row["series_key"]))
    keys = [str(row["series_key"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise RuntimeError("duplicate freshness series_key values are not allowed")

    expected_fields = list(contract["required_output_fields"])
    if expected_fields != list(rows[0].keys()):
        raise RuntimeError("builder output fields do not match the frozen V1 contract")

    args.output_root.mkdir(parents=True, exist_ok=True)
    output = args.output_root / "metals_data_freshness.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=expected_fields)
        writer.writeheader()
        writer.writerows(rows)

    status_counts = {
        status: sum(row["freshness_status"] == status for row in rows)
        for status in contract["status_order"]
    }
    manifest = {
        "status": "METALS_NATIVE_DATA_FRESHNESS_V1_PASS",
        "authority_id": AUTHORITY_ID,
        "schema_version": contract["schema_version"],
        "legacy_equivalent": False,
        "as_of": args.as_of.isoformat(),
        "row_count": len(rows),
        "benchmark_subject_count": len(benchmark),
        "vehicle_subject_count": len(daily),
        "unique_series_key_count": len(set(keys)),
        "status_counts": status_counts,
        "output_sha256": sha256(output),
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
        "source_collection_performed": False,
    }
    (args.output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("METALS_NATIVE_DATA_FRESHNESS_V1=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
