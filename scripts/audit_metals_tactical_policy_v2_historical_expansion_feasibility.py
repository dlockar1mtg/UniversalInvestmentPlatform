from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "metals" / "tactical_policy_v2_historical_expansion_feasibility_audit.json"


def _load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _history_for_symbol(symbol: str, end_exclusive: str) -> pd.DataFrame:
    frame = yf.download(
        symbol,
        period="max",
        interval="1d",
        auto_adjust=False,
        actions=False,
        progress=False,
        threads=False,
    )
    if frame is None or frame.empty:
        raise RuntimeError(f"No history returned for {symbol}.")

    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = [str(col[0]) for col in frame.columns]

    frame = frame.reset_index()
    date_col = "Date" if "Date" in frame.columns else frame.columns[0]
    frame[date_col] = pd.to_datetime(frame[date_col], utc=True).dt.date
    cutoff = date.fromisoformat(end_exclusive)
    frame = frame.loc[frame[date_col] <= cutoff].copy()
    frame = frame.dropna(subset=["Close"])
    if frame.empty:
        raise RuntimeError(f"No pre-V1 history returned for {symbol}.")
    return frame[[date_col, "Close"]].rename(columns={date_col: "observation_date"})


def main() -> int:
    cfg = _load_config()
    symbols = list(cfg["vehicle_symbols"])
    cutoff = cfg["maximum_feasibility_end_date"]
    minimum_history = int(cfg["minimum_history_observations"])
    max_forward = max(int(v) for v in cfg["forward_horizons_observations"])

    coverage = []
    frames: dict[str, pd.DataFrame] = {}
    for symbol in symbols:
        frame = _history_for_symbol(symbol, cutoff)
        frames[symbol] = frame
        coverage.append(
            {
                "symbol": symbol,
                "role": "REFERENCE_CONTROL" if symbol == "BIL" else "TACTICAL_OPPORTUNITY",
                "available_observation_count": int(len(frame)),
                "available_start_date": str(frame.iloc[0]["observation_date"]),
                "available_end_date": str(frame.iloc[-1]["observation_date"]),
            }
        )

    common_dates = None
    for frame in frames.values():
        dates = set(frame["observation_date"].tolist())
        common_dates = dates if common_dates is None else common_dates.intersection(dates)

    common_dates_sorted = sorted(common_dates or [])
    if not common_dates_sorted:
        raise RuntimeError("No common pre-V1 observation dates across governed Metals vehicles.")

    common_start = common_dates_sorted[0]
    common_end = common_dates_sorted[-1]
    common_count = len(common_dates_sorted)
    required_minimum = minimum_history + max_forward
    sufficient = common_count >= required_minimum

    result = {
        "status": "PASS" if sufficient else "INCONCLUSIVE",
        "read_only": True,
        "audit_id": cfg["audit_id"],
        "source_candidate_rule_design": cfg["source_candidate_rule_design"],
        "vehicle_count": len(symbols),
        "opportunity_vehicle_count": len(cfg["opportunity_symbols"]),
        "reference_control_count": len(cfg["reference_control_symbols"]),
        "existing_certified_history_start_date": cfg["existing_certified_history_start_date"],
        "maximum_feasibility_end_date": cutoff,
        "common_start_date": str(common_start),
        "common_end_date": str(common_end),
        "common_observation_count": common_count,
        "minimum_required_common_observations": required_minimum,
        "common_interval_supports_warmup_and_max_forward_horizon": sufficient,
        "coverage": coverage,
        "network_history_availability_probe_executed": True,
        "price_values_reported": False,
        "return_outcomes_reported": False,
        "candidate_postures_calculated": False,
        "forward_returns_calculated": False,
        "maximum_adverse_or_favorable_excursion_calculated": False,
        "historical_expansion_persisted": False,
        "new_validation_outcome_inspection_executed": False,
        "historical_expansion_execution_authorized": False,
        "historical_candidate_evaluation_authorized": False,
        "tactical_posture_authorized": False,
        "presentation_activation_executed": False,
        "production_database_write_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": cfg["next_decision"] if sufficient else "REVIEW_METALS_TACTICAL_POLICY_V2_HISTORICAL_EXPANSION_FEASIBILITY",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
