"""Build UIP-native Metals vehicle risk V1 from certified native price history.

The builder is artifact-only. It does not collect source data, write PostgreSQL,
stage a presentation publication, or activate a publication.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import stdev

AUTHORITY_ID = "UIP_NATIVE_METALS_RISK_V1"
SOURCE_AUTHORITY = "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1"
SOURCE_STATUS = "METALS_NATIVE_HISTORY_SIDECARS_PASS"
PRICE_SEMANTICS = "UNADJUSTED_CLOSE"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def linear_quantile(values: list[float], probability: float) -> float:
    if not values:
        raise RuntimeError("cannot compute quantile of empty values")
    if not 0.0 <= probability <= 1.0:
        raise RuntimeError("quantile probability must be between zero and one")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def maximum_drawdown(prices: list[float]) -> float:
    if not prices:
        raise RuntimeError("cannot compute drawdown without prices")
    peak = prices[0]
    worst = 0.0
    for value in prices:
        peak = max(peak, value)
        drawdown = value / peak - 1.0
        worst = min(worst, drawdown)
    return worst


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--history-manifest", type=Path, required=True)
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("config/presentation/metals_risk_v1.json"),
    )
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    contract = read_json(args.contract)
    history_manifest = read_json(args.history_manifest)
    history_rows = read_csv(args.history)

    if contract.get("authority_id") != AUTHORITY_ID:
        raise RuntimeError("unexpected risk authority_id")
    if contract.get("legacy_equivalent") is not False:
        raise RuntimeError("native risk V1 must remain non-legacy-equivalent")
    if contract.get("scope") != "VEHICLE_ONLY":
        raise RuntimeError("native risk V1 scope must remain vehicle-only")
    if contract.get("source_authority") != SOURCE_AUTHORITY:
        raise RuntimeError("unexpected configured risk source authority")
    if contract.get("price_semantics") != PRICE_SEMANTICS:
        raise RuntimeError("risk V1 must use UNADJUSTED_CLOSE semantics")

    if history_manifest.get("status") != SOURCE_STATUS:
        raise RuntimeError("native history sidecar did not pass")
    if history_manifest.get("source_authority") != SOURCE_AUTHORITY:
        raise RuntimeError("native history source authority mismatch")
    if int(history_manifest.get("history_row_count", -1)) != len(history_rows):
        raise RuntimeError("native history row count does not match manifest")
    history_entry = (history_manifest.get("files") or {}).get("metals_price_history.csv", {})
    if history_entry.get("sha256") != sha256(args.history):
        raise RuntimeError("native history SHA does not match manifest")

    expected_fields = list(contract["required_output_fields"])
    lookback = int(contract["lookback_observations"])
    minimum = int(contract["minimum_observations"])
    annualization = int(contract["annualization_factor"])
    expected_vehicle_count = int(contract["expected_vehicle_count"])
    confidence = float(contract["var"]["confidence_level"])
    if minimum < lookback:
        raise RuntimeError("minimum observations cannot be less than lookback observations")
    if annualization <= 0:
        raise RuntimeError("annualization factor must be positive")
    if contract["var"].get("method") != "HISTORICAL_EMPIRICAL":
        raise RuntimeError("risk V1 only supports historical empirical VaR")
    if contract["var"].get("quantile_method") != "LINEAR_INTERPOLATION":
        raise RuntimeError("risk V1 quantile method must remain linear interpolation")

    by_asset: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in history_rows:
        asset_id = str(row.get("asset_id", "")).strip()
        ticker = str(row.get("ticker", "")).strip()
        if not asset_id.startswith("metals:vehicle:") or not ticker:
            raise RuntimeError("risk V1 history contains a non-vehicle or missing ticker")
        if row.get("price_semantics") != PRICE_SEMANTICS:
            raise RuntimeError("risk V1 history contains non-UNADJUSTED_CLOSE semantics")
        if row.get("source_authority") != SOURCE_AUTHORITY:
            raise RuntimeError("risk V1 history contains unexpected source authority")
        by_asset[asset_id].append(row)

    if len(by_asset) != expected_vehicle_count:
        raise RuntimeError(
            f"expected {expected_vehicle_count} vehicle series, observed {len(by_asset)}"
        )

    output_rows: list[dict[str, object]] = []
    seen_tickers: set[str] = set()
    for asset_id, rows in sorted(by_asset.items()):
        ordered = sorted(rows, key=lambda row: str(row["observation_date"]))
        dates = [str(row["observation_date"]) for row in ordered]
        if len(dates) != len(set(dates)):
            raise RuntimeError(f"duplicate observation dates for {asset_id}")
        if len(ordered) < minimum:
            raise RuntimeError(
                f"insufficient observations for {asset_id}: {len(ordered)} < {minimum}"
            )
        window = ordered[-lookback:]
        prices = [float(row["close_usd"]) for row in window]
        if any(value <= 0 for value in prices):
            raise RuntimeError(f"nonpositive close found for {asset_id}")
        returns = [prices[index] / prices[index - 1] - 1.0 for index in range(1, len(prices))]
        if len(returns) < 2:
            raise RuntimeError(f"insufficient return observations for {asset_id}")
        downside = [value for value in returns if value < 0.0]
        if len(downside) < 2:
            raise RuntimeError(f"insufficient downside return observations for {asset_id}")

        volatility = stdev(returns) * math.sqrt(annualization)
        downside_volatility = stdev(downside) * math.sqrt(annualization)
        drawdown = maximum_drawdown(prices)
        var_quantile = linear_quantile(returns, 1.0 - confidence)
        value_at_risk = max(0.0, -var_quantile)
        ticker = str(window[-1]["ticker"])
        if ticker in seen_tickers:
            raise RuntimeError(f"duplicate ticker in risk output: {ticker}")
        seen_tickers.add(ticker)

        row = {
            "universal_asset_id": asset_id,
            "ticker": ticker,
            "as_of_date": str(window[-1]["observation_date"]),
            "lookback_observations": lookback,
            "return_convention": contract["return_convention"],
            "annualization_factor": annualization,
            "volatility": f"{volatility:.8f}",
            "downside_volatility": f"{downside_volatility:.8f}",
            "maximum_drawdown": f"{drawdown:.8f}",
            "value_at_risk": f"{value_at_risk:.8f}",
            "price_semantics": PRICE_SEMANTICS,
            "source_authority": SOURCE_AUTHORITY,
            "methodology_version": contract["methodology_version"],
        }
        if list(row.keys()) != expected_fields:
            raise RuntimeError("builder output fields do not match frozen Risk V1 contract")
        output_rows.append(row)

    if len(output_rows) != expected_vehicle_count:
        raise RuntimeError("risk V1 output does not contain exactly one row per vehicle")

    args.output_root.mkdir(parents=True, exist_ok=True)
    output = args.output_root / "risk.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=expected_fields)
        writer.writeheader()
        writer.writerows(output_rows)

    manifest = {
        "status": "METALS_NATIVE_RISK_V1_PASS",
        "authority_id": AUTHORITY_ID,
        "schema_version": contract["schema_version"],
        "methodology_version": contract["methodology_version"],
        "legacy_equivalent": False,
        "scope": "VEHICLE_ONLY",
        "row_count": len(output_rows),
        "vehicle_count": len(output_rows),
        "lookback_observations": lookback,
        "minimum_observations": minimum,
        "return_convention": contract["return_convention"],
        "annualization_factor": annualization,
        "var_method": contract["var"]["method"],
        "var_confidence_level": confidence,
        "var_horizon_days": int(contract["var"]["horizon_days"]),
        "price_semantics": PRICE_SEMANTICS,
        "source_authority": SOURCE_AUTHORITY,
        "source_history_sha256": sha256(args.history),
        "first_as_of_date": min(str(row["as_of_date"]) for row in output_rows),
        "last_as_of_date": max(str(row["as_of_date"]) for row in output_rows),
        "output_sha256": sha256(output),
        "source_collection_performed": False,
        "postgres_write_performed": False,
        "publication_staged": False,
        "publication_activated": False,
    }
    (args.output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print("METALS_NATIVE_RISK_V1=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
