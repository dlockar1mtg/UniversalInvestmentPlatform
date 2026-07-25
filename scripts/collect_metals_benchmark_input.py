"""Collect UIP-native benchmark observations from official Metals providers."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from foundation.production.metals_providers import ProviderCollectionPolicy, collect_with_policy, ingest_commodity_observations
from foundation.production.providers import EIAUraniumProvider, WorldBankCommodityProvider


_UNITS = {
    "gold": "usd_per_troy_ounce",
    "silver": "usd_per_troy_ounce",
    "platinum": "usd_per_troy_ounce",
    "copper": "usd_per_metric_ton",
    "uranium": "usd_per_pound",
}


def _rows(provider_name: str, result, policy) -> list[dict[str, object]]:
    batch = ingest_commodity_observations(result, policy)
    rows: list[dict[str, object]] = []
    for record in batch.records:
        asset = str(record.asset_id).upper()
        observed = record.observed_at.astimezone(timezone.utc)
        rows.append({
            "series_id": asset,
            "observation_date": observed.date().isoformat(),
            "value": str(record.values["price"]),
            "source": provider_name,
            "unit": _UNITS.get(asset.lower(), "usd"),
        })
    return rows


def collect_rows(as_of: datetime | None = None) -> list[dict[str, object]]:
    now = as_of or datetime.now(timezone.utc)
    rows: list[dict[str, object]] = []

    world_bank_policy = ProviderCollectionPolicy(
        maximum_attempts=3,
        initial_backoff=timedelta(seconds=2),
        maximum_age=timedelta(days=75),
    )
    world_bank = collect_with_policy(WorldBankCommodityProvider().latest, world_bank_policy, as_of=now)
    rows.extend(_rows("world_bank", world_bank, world_bank_policy))

    eia_policy = ProviderCollectionPolicy(
        maximum_attempts=3,
        initial_backoff=timedelta(seconds=2),
        maximum_age=timedelta(days=730),
    )
    eia = collect_with_policy(EIAUraniumProvider().latest, eia_policy, as_of=now)
    rows.extend(_rows("eia", eia, eia_policy))

    return sorted(rows, key=lambda row: (str(row["series_id"]), str(row["observation_date"]), str(row["source"])))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "operations" / "metals" / "benchmark_input.csv",
    )
    args = parser.parse_args()

    rows = collect_rows()
    if not rows:
        print("METALS BENCHMARK COLLECTION: FAILED (no rows)")
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["series_id", "observation_date", "value", "source", "unit"])
        writer.writeheader()
        writer.writerows(rows)

    print(f"METALS BENCHMARK COLLECTION: PASS ({len(rows)} rows)")
    print(f"Output: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
