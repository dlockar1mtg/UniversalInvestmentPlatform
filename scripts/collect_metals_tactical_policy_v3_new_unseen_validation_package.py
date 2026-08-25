from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import pandas as pd
import yfinance as yf

PACKAGE_ID = "metals-v3-new-unseen-validation-20230822-20260824"
START_DATE = "2023-08-22"
END_DATE = "2026-08-24"
DOWNLOAD_END_EXCLUSIVE = "2026-08-25"
SOURCE_PROVIDER = "yfinance"
OPPORTUNITY_TICKERS = ["COPX", "CPER", "GLD", "IAU", "PPLT", "SGOL", "SIVR", "SLV", "URA", "URNM"]
REFERENCE_TICKER = "BIL"
TICKERS = OPPORTUNITY_TICKERS + [REFERENCE_TICKER]
REQUIRED_FIELDS = [
    "asset_id",
    "ticker",
    "observation_date",
    "open_usd",
    "high_usd",
    "low_usd",
    "close_usd",
    "adjusted_close_usd",
    "volume",
    "source_provider",
    "package_id",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_columns(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if isinstance(frame.columns, pd.MultiIndex):
        normalized = {}
        for wanted in ["Open", "High", "Low", "Close", "Adj Close", "Volume"]:
            matches = [col for col in frame.columns if wanted in col and ticker in col]
            if not matches:
                matches = [col for col in frame.columns if wanted in col]
            if len(matches) != 1:
                raise RuntimeError(f"Could not uniquely resolve {wanted} for {ticker}: {matches}")
            normalized[wanted] = frame[matches[0]]
        return pd.DataFrame(normalized, index=frame.index)
    return frame


def scalar_or_none(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (int, float)) and not math.isfinite(float(value)):
        return None
    return value


def collect_ticker(ticker: str) -> list[dict]:
    frame = yf.download(
        ticker,
        start=START_DATE,
        end=DOWNLOAD_END_EXCLUSIVE,
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    if frame is None or frame.empty:
        raise RuntimeError(f"No history returned for {ticker}")
    frame = normalize_columns(frame, ticker).copy()
    frame.index = pd.to_datetime(frame.index).tz_localize(None)
    frame = frame[(frame.index >= pd.Timestamp(START_DATE)) & (frame.index <= pd.Timestamp(END_DATE))]
    if frame.empty:
        raise RuntimeError(f"No in-range history returned for {ticker}")

    rows: list[dict] = []
    for ts, row in frame.sort_index().iterrows():
        close_value = scalar_or_none(row.get("Close"))
        if close_value is None or float(close_value) <= 0:
            raise RuntimeError(f"Invalid raw close for {ticker} on {ts.date()}")
        record = {
            "asset_id": f"metals:vehicle:{ticker}",
            "ticker": ticker,
            "observation_date": ts.date().isoformat(),
            "open_usd": None if scalar_or_none(row.get("Open")) is None else float(row.get("Open")),
            "high_usd": None if scalar_or_none(row.get("High")) is None else float(row.get("High")),
            "low_usd": None if scalar_or_none(row.get("Low")) is None else float(row.get("Low")),
            "close_usd": float(close_value),
            "adjusted_close_usd": None if scalar_or_none(row.get("Adj Close")) is None else float(row.get("Adj Close")),
            "volume": None if scalar_or_none(row.get("Volume")) is None else int(round(float(row.get("Volume")))),
            "source_provider": SOURCE_PROVIDER,
            "package_id": PACKAGE_ID,
        }
        if set(record) != set(REQUIRED_FIELDS):
            raise RuntimeError(f"Unexpected schema for {ticker} on {ts.date()}")
        rows.append(record)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    out = Path(args.output_dir)
    if out.exists():
        raise RuntimeError(f"Output directory already exists; refusing overwrite: {out}")
    out.mkdir(parents=True)

    history_path = out / "metals_v3_new_unseen_validation_history.jsonl"
    coverage_path = out / "coverage.json"
    manifest_path = out / "manifest.json"

    all_rows: list[dict] = []
    ticker_rows: dict[str, list[dict]] = {}
    try:
        for ticker in TICKERS:
            rows = collect_ticker(ticker)
            ticker_rows[ticker] = rows
            all_rows.extend(rows)

        all_rows.sort(key=lambda r: (r["ticker"], r["observation_date"]))
        with history_path.open("w", encoding="utf-8", newline="\n") as f:
            for row in all_rows:
                f.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")

        date_sets = {ticker: {r["observation_date"] for r in rows} for ticker, rows in ticker_rows.items()}
        common_dates = sorted(set.intersection(*(date_sets[t] for t in TICKERS)))
        if not common_dates:
            raise RuntimeError("No common observation dates across the governed vehicle universe")

        coverage = {
            "package_id": PACKAGE_ID,
            "outcome_blind": True,
            "validation_start_date": START_DATE,
            "validation_end_date": END_DATE,
            "source_provider": SOURCE_PROVIDER,
            "required_price_semantics": "UNADJUSTED_CLOSE",
            "vehicle_count": len(TICKERS),
            "opportunity_vehicle_count": len(OPPORTUNITY_TICKERS),
            "reference_control_vehicle": REFERENCE_TICKER,
            "row_count": len(all_rows),
            "common_observation_count": len(common_dates),
            "common_first_observation_date": common_dates[0],
            "common_last_observation_date": common_dates[-1],
            "vehicles": {
                ticker: {
                    "row_count": len(ticker_rows[ticker]),
                    "first_observation_date": ticker_rows[ticker][0]["observation_date"],
                    "last_observation_date": ticker_rows[ticker][-1]["observation_date"],
                }
                for ticker in TICKERS
            },
        }
        coverage_path.write_text(json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        history_sha = sha256_file(history_path)
        coverage_sha = sha256_file(coverage_path)
        manifest = {
            "package_id": PACKAGE_ID,
            "authorization_id": "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-AUTHORIZATION-1",
            "package_role": "GENUINELY_NEW_UNSEEN_VALIDATION_HISTORY",
            "outcome_blind": True,
            "package_frozen": True,
            "classifier_executed": False,
            "validation_outcomes_calculated": False,
            "validation_outcomes_inspected": False,
            "tactical_posture_authorized": False,
            "validation_start_date": START_DATE,
            "validation_end_date": END_DATE,
            "consumed_interval_end_date": "2023-08-21",
            "source_provider": SOURCE_PROVIDER,
            "auto_adjust": False,
            "required_price_field": "close_usd",
            "required_price_semantics": "UNADJUSTED_CLOSE",
            "vehicle_count": len(TICKERS),
            "opportunity_vehicle_count": len(OPPORTUNITY_TICKERS),
            "reference_control_vehicle": REFERENCE_TICKER,
            "history_file": history_path.name,
            "coverage_file": coverage_path.name,
            "history_sha256": history_sha,
            "coverage_sha256": coverage_sha,
            "row_count": len(all_rows),
            "common_observation_count": len(common_dates),
            "new_validation_outcome_inspection_authorized": False,
            "next_decision": "CERTIFY_AND_AUTHORIZE_METALS_TACTICAL_POLICY_V3_NEW_UNSEEN_VALIDATION_OUTCOME_INSPECTION",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        print(json.dumps({
            "status": "PASS",
            "package_id": PACKAGE_ID,
            "output_dir": str(out),
            "row_count": len(all_rows),
            "vehicle_count": len(TICKERS),
            "common_observation_count": len(common_dates),
            "history_sha256": history_sha,
            "coverage_sha256": coverage_sha,
            "package_frozen": True,
            "outcome_blind": True,
            "validation_outcomes_inspected": False,
            "next_decision": manifest["next_decision"],
        }, indent=2, sort_keys=True))
        return 0
    except Exception:
        for path in [manifest_path, coverage_path, history_path]:
            if path.exists():
                path.unlink()
        try:
            out.rmdir()
        except OSError:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
