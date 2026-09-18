from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "config" / "presentation" / "metals_commodity_technical_context_v1.json"
SUPPORTED = ("aluminum", "copper", "gold", "nickel", "platinum", "silver", "tin", "zinc")
AUTHORITY_ID = "UIP_NATIVE_METALS_COMMODITY_TECHNICAL_CONTEXT_V1"
STATUS = "METALS_NATIVE_COMMODITY_TECHNICAL_CONTEXT_V1_PASS"


def _month_shift(value: date, months: int) -> date:
    index = value.year * 12 + (value.month - 1) - months
    return date(index // 12, index % 12 + 1, 1)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_contract(path: Path) -> dict:
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("authority_id") != AUTHORITY_ID:
        raise RuntimeError("commodity technical-context authority mismatch")
    if contract.get("legacy_equivalent") is not False:
        raise RuntimeError("commodity technical-context authority must be nonlegacy")
    expected_assets = [f"metals:commodity:{asset}" for asset in SUPPORTED]
    if contract.get("supported_assets") != expected_assets:
        raise RuntimeError("commodity technical-context supported-asset contract mismatch")
    source = contract.get("source_contract") or {}
    if source.get("provider") != "world_bank" or source.get("required_frequency") != "MONTHLY":
        raise RuntimeError("commodity technical-context source contract mismatch")
    moving = contract.get("moving_average_policy") or {}
    if moving.get("ma50_authorized") is not False or moving.get("ma200_authorized") is not False:
        raise RuntimeError("daily moving averages are not authorized by V1")
    return contract


def _read_history(path: Path) -> dict[str, dict[date, dict[str, object]]]:
    rows: dict[str, dict[date, dict[str, object]]] = defaultdict(dict)
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
            source = str(row.get("source", "")).strip().lower()
            series_id = str(row.get("series_id", "")).strip()
            if source != "world_bank":
                raise RuntimeError(f"unsupported commodity technical-context source: {source}")
            expected_series = f"WORLD_BANK::{asset.upper()}_MONTHLY"
            if series_id != expected_series:
                raise RuntimeError(f"commodity technical-context series identity mismatch: {asset}/{series_id}")
            if observed in rows[asset]:
                raise RuntimeError(f"duplicate monthly observation: {asset}/{observed}")
            rows[asset][observed] = {
                "value": value,
                "source": source,
                "series_id": series_id,
            }
    return rows


def _period_return(latest: float, history: dict[date, dict[str, object]], target: date) -> float:
    if target not in history:
        raise RuntimeError(f"missing exact prior calendar month: {target}")
    prior = float(history[target]["value"])
    if prior == 0:
        raise RuntimeError(f"zero prior value is invalid: {target}")
    return latest / prior - 1.0


def build_rows(history_path: Path, contract_path: Path = DEFAULT_CONTRACT) -> list[dict[str, object]]:
    contract = _load_contract(contract_path)
    grouped = _read_history(history_path)
    output: list[dict[str, object]] = []
    for asset in SUPPORTED:
        history = grouped.get(asset, {})
        if not history:
            raise RuntimeError(f"missing World Bank history for {asset}")
        latest_date = max(history)
        latest_record = history[latest_date]
        latest = float(latest_record["value"])
        peak = max(float(record["value"]) for record in history.values())
        if peak <= 0:
            raise RuntimeError(f"invalid history peak for {asset}")
        peak_dates = sorted(
            observed
            for observed, record in history.items()
            if float(record["value"]) == peak
        )
        if len(peak_dates) != 1:
            raise RuntimeError(f"ambiguous historical peak date for {asset}")
        output.append(
            {
                "universal_asset_id": f"metals:commodity:{asset}",
                "asset_id": asset,
                "as_of_date": latest_date.isoformat(),
                "source_provider": str(latest_record["source"]),
                "source_series_id": str(latest_record["series_id"]),
                "source_frequency": "monthly",
                "observation_count": len(history),
                "return_1m": _period_return(latest, history, _month_shift(latest_date, 1)),
                "return_3m": _period_return(latest, history, _month_shift(latest_date, 3)),
                "return_6m": _period_return(latest, history, _month_shift(latest_date, 6)),
                "current_drawdown": latest / peak - 1.0,
                "historical_peak_value": peak,
                "historical_peak_date": peak_dates[0].isoformat(),
                "ma50_supported": False,
                "ma200_supported": False,
                "authority_id": AUTHORITY_ID,
                "methodology_version": contract["methodology_version"],
                "presentation_semantics": contract["presentation_semantics"],
            }
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    contract = _load_contract(args.contract)
    rows = build_rows(args.history, args.contract)
    args.output_root.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_root / "metals_commodity_technical_context.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    manifest = {
        "status": STATUS,
        "authority_id": AUTHORITY_ID,
        "schema_version": contract["schema_version"],
        "methodology_version": contract["methodology_version"],
        "legacy_equivalent": False,
        "scope": contract["scope"],
        "source_state_mode": contract["source_state_mode"],
        "presentation_semantics": contract["presentation_semantics"],
        "row_count": len(rows),
        "supported_asset_count": len(rows),
        "source_history_row_count": sum(int(row["observation_count"]) for row in rows),
        "unsupported_assets": contract["unsupported_assets"],
        "ma50_supported": False,
        "ma200_supported": False,
        "output_sha256": _sha256(csv_path),
        "source_collection_performed": True,
        "publication_staged": False,
        "publication_activated": False,
        "postgres_write_performed": False,
    }
    (args.output_root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(STATUS)
    print(f"rows={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
