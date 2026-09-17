from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

SUPPORTED = ("aluminum", "copper", "gold", "nickel", "platinum", "silver", "tin", "zinc")
AUTHORITY_ID = "UIP_NATIVE_METALS_COMMODITY_TECHNICAL_CONTEXT_V1"
STATUS = "METALS_NATIVE_COMMODITY_TECHNICAL_CONTEXT_V1_PASS"


def _month_shift(value: date, months: int) -> date:
    index = value.year * 12 + (value.month - 1) - months
    return date(index // 12, index % 12 + 1, 1)


def _read_history(path: Path) -> dict[str, dict[date, float]]:
    rows: dict[str, dict[date, float]] = defaultdict(dict)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            asset = str(row.get("asset_id", "")).strip().lower()
            if asset not in SUPPORTED:
                continue
            observed = date.fromisoformat(str(row["observation_date"]))
            if observed.day != 1:
                raise RuntimeError(f"World Bank monthly history must be month-normalized: {observed}")
            value = float(row["value"])
            if value < 0:
                raise RuntimeError("negative commodity value is invalid")
            if observed in rows[asset]:
                raise RuntimeError(f"duplicate monthly observation: {asset}/{observed}")
            rows[asset][observed] = value
    return rows


def _return(latest: float, history: dict[date, float], target: date) -> float:
    if target not in history:
        raise RuntimeError(f"missing exact prior calendar month: {target}")
    prior = history[target]
    if prior == 0:
        raise RuntimeError(f"zero prior value is invalid: {target}")
    return latest / prior - 1.0


def build_rows(history_path: Path) -> list[dict[str, object]]:
    grouped = _read_history(history_path)
    output: list[dict[str, object]] = []
    for asset in SUPPORTED:
        history = grouped.get(asset, {})
        if not history:
            raise RuntimeError(f"missing World Bank history for {asset}")
        latest_date = max(history)
        latest = history[latest_date]
        peak = max(history.values())
        if peak <= 0:
            raise RuntimeError(f"invalid history peak for {asset}")
        output.append(
            {
                "universal_asset_id": f"metals:commodity:{asset}",
                "asset_id": asset,
                "as_of_date": latest_date.isoformat(),
                "source": "world_bank",
                "source_frequency": "monthly",
                "return_1m": _return(latest, history, _month_shift(latest_date, 1)),
                "return_3m": _return(latest, history, _month_shift(latest_date, 3)),
                "return_6m": _return(latest, history, _month_shift(latest_date, 6)),
                "current_drawdown": latest / peak - 1.0,
                "ma50_supported": False,
                "ma200_supported": False,
                "authority_id": AUTHORITY_ID,
            }
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    rows = build_rows(args.history)
    args.output_root.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_root / "metals_commodity_technical_context.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "status": STATUS,
        "authority_id": AUTHORITY_ID,
        "row_count": len(rows),
        "supported_asset_count": 8,
        "unsupported_assets": {"uranium": "EIA source is annual; monthly technical context unavailable"},
        "ma50_supported": False,
        "ma200_supported": False,
        "publication_staged": False,
        "publication_activated": False,
        "postgres_write": False,
    }
    (args.output_root / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(STATUS)
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
