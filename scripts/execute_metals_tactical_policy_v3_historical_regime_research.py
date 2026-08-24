from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_freeze.json"
AUTHORIZATION_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_authorization.json"

SYMBOL_COLUMNS = ("vehicle_id", "symbol", "ticker", "asset_id")
DATE_COLUMNS = ("observation_date", "date", "as_of_date")
CLOSE_COLUMNS = ("unadjusted_close", "raw_close", "close")

LABEL_COLUMNS = [
    "vehicle_id",
    "observation_date",
    "exposure_family",
    "is_reference_control",
    "rule_version",
    "candidate_regime",
    "assignment_reason",
    "eligible",
    "return_1m_pct",
    "return_3m_pct",
    "return_6m_pct",
    "distance_ma50_pct",
    "distance_ma200_pct",
    "current_drawdown_pct",
    "realized_volatility_3m_pct",
    "trend_slope",
    "return_dispersion",
    "volatility_change",
    "drawdown_recovery_rate",
    "distance_from_recent_extreme",
    "short_vs_long_momentum_spread",
    "strong_momentum_threshold",
    "high_volatility_change_threshold",
    "high_return_dispersion_threshold",
    "near_recent_extreme_abs_distance_threshold",
    "trend_persistence_condition_count",
    "exhaustion_condition_count",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def choose_column(columns: list[str], allowed: tuple[str, ...], role: str) -> str:
    matches = [name for name in allowed if name in columns]
    if len(matches) != 1:
        raise RuntimeError(f"history input must contain exactly one approved {role} column; found {matches}")
    return matches[0]


def sign(value: float) -> int:
    if not math.isfinite(value) or value == 0:
        return 0
    return 1 if value > 0 else -1


def sample_std(values: pd.Series) -> float:
    clean = values.dropna().astype(float)
    if len(clean) < 2:
        return float("nan")
    return float(clean.std(ddof=1))


def percentile_prior(series: pd.Series, index: int, history: int, q: float) -> tuple[float, int]:
    prior = series.iloc[max(0, index - history):index].dropna().astype(float)
    if len(prior) == 0:
        return float("nan"), 0
    return float(np.quantile(prior.to_numpy(), q, method="linear")), int(len(prior))


def annualized_log_slope(close: pd.Series, index: int, window: int) -> float:
    values = close.iloc[index - window + 1:index + 1].astype(float).to_numpy()
    if len(values) != window or np.any(values <= 0) or np.any(~np.isfinite(values)):
        return float("nan")
    x = np.arange(window, dtype=float)
    slope = float(np.polyfit(x, np.log(values), 1)[0])
    return 100.0 * (math.exp(slope * 252.0) - 1.0)


def exposure_family(symbol: str) -> str:
    if symbol in {"GLD", "IAU", "SGOL"}:
        return "GOLD"
    if symbol in {"SIVR", "SLV"}:
        return "SILVER"
    if symbol == "BIL":
        return "REFERENCE_CONTROL"
    return f"VEHICLE::{symbol}"


def load_history(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise RuntimeError(f"history CSV is missing: {path}")
    frame = pd.read_csv(path)
    columns = [str(col) for col in frame.columns]
    symbol_col = choose_column(columns, SYMBOL_COLUMNS, "vehicle identifier")
    date_col = choose_column(columns, DATE_COLUMNS, "date")
    close_col = choose_column(columns, CLOSE_COLUMNS, "unadjusted close")

    selected = frame[[symbol_col, date_col, close_col]].copy()
    selected.columns = ["vehicle_id", "observation_date", "unadjusted_close"]
    selected["vehicle_id"] = selected["vehicle_id"].astype(str).str.strip().str.upper()
    selected["observation_date"] = pd.to_datetime(selected["observation_date"], errors="raise").dt.date
    selected["unadjusted_close"] = pd.to_numeric(selected["unadjusted_close"], errors="raise")

    if selected["vehicle_id"].eq("").any():
        raise RuntimeError("blank vehicle identifier found")
    if (~np.isfinite(selected["unadjusted_close"].to_numpy(dtype=float))).any():
        raise RuntimeError("non-finite close found")
    if (selected["unadjusted_close"] <= 0).any():
        raise RuntimeError("nonpositive close found")
    if selected.duplicated(["vehicle_id", "observation_date"]).any():
        raise RuntimeError("duplicate vehicle/date rows found")

    selected = selected.sort_values(["vehicle_id", "observation_date"], kind="mergesort").reset_index(drop=True)
    if "BIL" not in set(selected["vehicle_id"]):
        raise RuntimeError("BIL reference/control is missing from history input")
    return selected


def build_vehicle_features(group: pd.DataFrame, freeze: dict[str, Any]) -> pd.DataFrame:
    windows = freeze["price_basis"]["trading_day_windows"]
    close = group["unadjusted_close"].astype(float).reset_index(drop=True)
    result = group.reset_index(drop=True).copy()

    result["return_1m_pct"] = 100.0 * (close / close.shift(int(windows["return_1m"])) - 1.0)
    result["return_3m_pct"] = 100.0 * (close / close.shift(int(windows["return_3m"])) - 1.0)
    result["return_6m_pct"] = 100.0 * (close / close.shift(int(windows["return_6m"])) - 1.0)
    result["distance_ma50_pct"] = 100.0 * (close / close.rolling(int(windows["ma50"]), min_periods=int(windows["ma50"])).mean() - 1.0)
    result["distance_ma200_pct"] = 100.0 * (close / close.rolling(int(windows["ma200"]), min_periods=int(windows["ma200"])).mean() - 1.0)
    rolling_max = close.rolling(int(windows["drawdown_lookback"]), min_periods=int(windows["drawdown_lookback"])).max()
    result["current_drawdown_pct"] = 100.0 * (close / rolling_max - 1.0)

    simple_daily_return = close / close.shift(1) - 1.0
    vol63 = simple_daily_return.rolling(int(windows["volatility_medium"]), min_periods=int(windows["volatility_medium"])).std(ddof=1)
    vol21 = simple_daily_return.rolling(int(windows["volatility_short"]), min_periods=int(windows["volatility_short"])).std(ddof=1)
    result["realized_volatility_3m_pct"] = 100.0 * vol63 * math.sqrt(252.0)
    result["volatility_change"] = 100.0 * vol21 * math.sqrt(252.0) - result["realized_volatility_3m_pct"]

    slope_window = int(windows["trend_slope"])
    result["trend_slope"] = [
        annualized_log_slope(close, i, slope_window) if i >= slope_window - 1 else float("nan")
        for i in range(len(close))
    ]

    dispersion_window = 63
    result["return_dispersion"] = result["return_1m_pct"].rolling(dispersion_window, min_periods=dispersion_window).std(ddof=1)
    result["drawdown_recovery_rate"] = result["current_drawdown_pct"] - result["current_drawdown_pct"].shift(21)

    extreme_window = int(windows["recent_extreme"])
    rolling_high = close.rolling(extreme_window, min_periods=extreme_window).max()
    rolling_low = close.rolling(extreme_window, min_periods=extreme_window).min()
    result["distance_from_recent_extreme"] = np.where(
        result["return_6m_pct"] >= 0,
        100.0 * (close / rolling_high - 1.0),
        100.0 * (close / rolling_low - 1.0),
    )
    result["short_vs_long_momentum_spread"] = result["return_1m_pct"] - result["return_6m_pct"] / 6.0
    return result


def classify_vehicle(features: pd.DataFrame, freeze: dict[str, Any]) -> pd.DataFrame:
    threshold_spec = freeze["point_in_time_adaptive_thresholds"]
    history = int(freeze["price_basis"]["trading_day_windows"]["adaptive_threshold_history"])
    minimum_prior = int(threshold_spec["minimum_prior_threshold_observations"])
    minimum_history = int(freeze["price_basis"]["minimum_history_before_candidate_label"])
    rule_version = freeze["candidate_regime_assignment_logic"]["logic_version"]

    required_features = [
        "return_1m_pct", "return_3m_pct", "return_6m_pct", "distance_ma50_pct",
        "distance_ma200_pct", "current_drawdown_pct", "realized_volatility_3m_pct",
        "trend_slope", "return_dispersion", "volatility_change", "drawdown_recovery_rate",
        "distance_from_recent_extreme", "short_vs_long_momentum_spread",
    ]

    abs_r3 = features["return_3m_pct"].abs()
    abs_extreme = features["distance_from_recent_extreme"].abs()
    rows: list[dict[str, Any]] = []

    for i, row in features.iterrows():
        q_momentum, n_momentum = percentile_prior(abs_r3, i, history, float(threshold_spec["strong_momentum_abs_return_3m_percentile"]))
        q_vol, n_vol = percentile_prior(features["volatility_change"], i, history, float(threshold_spec["high_volatility_change_percentile"]))
        q_disp, n_disp = percentile_prior(features["return_dispersion"], i, history, float(threshold_spec["high_return_dispersion_percentile"]))
        q_extreme, n_extreme = percentile_prior(abs_extreme, i, history, float(threshold_spec["near_recent_extreme_abs_distance_percentile"]))

        threshold_counts = [n_momentum, n_vol, n_disp, n_extreme]
        feature_values = [float(row[name]) if pd.notna(row[name]) else float("nan") for name in required_features]
        eligible = (
            i >= minimum_history
            and all(math.isfinite(value) for value in feature_values)
            and all(count >= minimum_prior for count in threshold_counts)
            and all(math.isfinite(value) for value in (q_momentum, q_vol, q_disp, q_extreme))
        )

        trend_count = 0
        exhaustion_count = 0
        label = "NEUTRAL_OR_UNCERTAIN"
        reason = "INSUFFICIENT_POINT_IN_TIME_EVIDENCE"

        if eligible:
            r1 = float(row["return_1m_pct"])
            r3 = float(row["return_3m_pct"])
            r6 = float(row["return_6m_pct"])
            ma50 = float(row["distance_ma50_pct"])
            ma200 = float(row["distance_ma200_pct"])
            slope = float(row["trend_slope"])
            spread = float(row["short_vs_long_momentum_spread"])
            vol_change = float(row["volatility_change"])
            dispersion = float(row["return_dispersion"])
            extreme = float(row["distance_from_recent_extreme"])
            recovery = float(row["drawdown_recovery_rate"])

            signs = [sign(value) for value in (r1, r3, r6, ma50, ma200)]
            directional_alignment = signs[0] != 0 and len(set(signs)) == 1
            slope_alignment = sign(slope) != 0 and sign(slope) == sign(r6)
            spread_no_conflict = sign(spread) == 0 or sign(spread) == sign(r6)
            strong_momentum = abs(r3) >= q_momentum
            no_vol_spike = vol_change <= q_vol
            trend_conditions = [directional_alignment, slope_alignment, spread_no_conflict, strong_momentum, no_vol_spike]
            trend_count = sum(bool(value) for value in trend_conditions)
            trend_persistence = all(trend_conditions)

            slope_opposes = sign(slope) != 0 and sign(r3) != 0 and sign(slope) == -sign(r3)
            spread_opposes = sign(spread) != 0 and sign(r3) != 0 and sign(spread) == -sign(r3)
            volatility_high = vol_change > q_vol
            dispersion_high = dispersion > q_disp
            near_extreme_with_opposition = abs(extreme) <= q_extreme and spread_opposes
            recovery_opposes = sign(recovery) != 0 and sign(r3) != 0 and sign(recovery) == -sign(r3) and abs(recovery) > 1.0
            exhaustion_conditions = [
                slope_opposes,
                spread_opposes,
                volatility_high,
                dispersion_high,
                near_extreme_with_opposition,
                recovery_opposes,
            ]
            exhaustion_count = sum(bool(value) for value in exhaustion_conditions)
            mean_reversion = strong_momentum and (not trend_persistence) and exhaustion_count >= 2

            if trend_persistence:
                label = "TREND_PERSISTENCE"
                reason = "ALL_FROZEN_TREND_PERSISTENCE_CONDITIONS_MET"
            elif mean_reversion:
                label = "MEAN_REVERSION_OR_EXHAUSTION"
                reason = "FROZEN_STRONG_MOMENTUM_AND_EXHAUSTION_CONDITIONS_MET"
            else:
                label = "NEUTRAL_OR_UNCERTAIN"
                reason = "FROZEN_DIRECTIONAL_REGIME_CONDITIONS_NOT_SATISFIED"

        output = {
            "vehicle_id": str(row["vehicle_id"]),
            "observation_date": row["observation_date"].isoformat(),
            "exposure_family": exposure_family(str(row["vehicle_id"])),
            "is_reference_control": str(row["vehicle_id"]) == "BIL",
            "rule_version": rule_version,
            "candidate_regime": label,
            "assignment_reason": reason,
            "eligible": bool(eligible),
            "strong_momentum_threshold": q_momentum if math.isfinite(q_momentum) else None,
            "high_volatility_change_threshold": q_vol if math.isfinite(q_vol) else None,
            "high_return_dispersion_threshold": q_disp if math.isfinite(q_disp) else None,
            "near_recent_extreme_abs_distance_threshold": q_extreme if math.isfinite(q_extreme) else None,
            "trend_persistence_condition_count": int(trend_count),
            "exhaustion_condition_count": int(exhaustion_count),
        }
        for name in required_features:
            value = float(row[name]) if pd.notna(row[name]) else float("nan")
            output[name] = value if math.isfinite(value) else None
        rows.append(output)

    return pd.DataFrame(rows, columns=LABEL_COLUMNS)


def calculate_outcomes(history: pd.DataFrame, labels: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    keyed_labels = labels[["vehicle_id", "observation_date", "candidate_regime", "eligible", "exposure_family", "is_reference_control"]].copy()
    keyed_labels["observation_date"] = pd.to_datetime(keyed_labels["observation_date"]).dt.date
    outcome_rows: list[dict[str, Any]] = []

    for symbol, group in history.groupby("vehicle_id", sort=True):
        group = group.sort_values("observation_date").reset_index(drop=True)
        close = group["unadjusted_close"].astype(float).to_numpy()
        dates = group["observation_date"].tolist()
        position = {date: i for i, date in enumerate(dates)}
        symbol_labels = keyed_labels[keyed_labels["vehicle_id"] == symbol]
        for _, label_row in symbol_labels.iterrows():
            i = position[label_row["observation_date"]]
            base = float(close[i])
            for horizon in horizons:
                if i + horizon >= len(close):
                    forward_return = mae = mfe = None
                else:
                    future = close[i + 1:i + horizon + 1]
                    forward_return = 100.0 * (float(close[i + horizon]) / base - 1.0)
                    path_returns = 100.0 * (future / base - 1.0)
                    mae = float(np.min(path_returns))
                    mfe = float(np.max(path_returns))
                outcome_rows.append({
                    "vehicle_id": symbol,
                    "observation_date": label_row["observation_date"].isoformat(),
                    "exposure_family": label_row["exposure_family"],
                    "is_reference_control": bool(label_row["is_reference_control"]),
                    "candidate_regime": label_row["candidate_regime"],
                    "eligible": bool(label_row["eligible"]),
                    "horizon_trading_days": int(horizon),
                    "forward_return_pct": forward_return,
                    "mae_pct": mae,
                    "mfe_pct": mfe,
                })
    return pd.DataFrame(outcome_rows)


def summarize_outcomes(outcomes: pd.DataFrame) -> pd.DataFrame:
    usable = outcomes[
        outcomes["eligible"]
        & (~outcomes["is_reference_control"])
        & outcomes["forward_return_pct"].notna()
    ].copy()
    rows: list[dict[str, Any]] = []
    for (regime, horizon), group in usable.groupby(["candidate_regime", "horizon_trading_days"], sort=True):
        returns = group["forward_return_pct"].astype(float)
        rows.append({
            "candidate_regime": regime,
            "horizon_trading_days": int(horizon),
            "observation_count": int(len(group)),
            "vehicle_count": int(group["vehicle_id"].nunique()),
            "exposure_family_count": int(group["exposure_family"].nunique()),
            "mean_forward_return_pct": float(returns.mean()),
            "median_forward_return_pct": float(returns.median()),
            "positive_return_rate": float((returns > 0).mean()),
            "mean_mae_pct": float(group["mae_pct"].astype(float).mean()),
            "mean_mfe_pct": float(group["mfe_pct"].astype(float).mean()),
        })
    return pd.DataFrame(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-csv", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    freeze = json.loads(FREEZE_PATH.read_text(encoding="utf-8"))
    authorization = json.loads(AUTHORIZATION_PATH.read_text(encoding="utf-8"))
    if freeze.get("freeze_id") != "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-FREEZE-1":
        raise RuntimeError("unexpected freeze authority")
    if freeze.get("controls", {}).get("v3_historical_regime_research_execution_authorized") is not True:
        raise RuntimeError("historical regime research execution is not authorized")
    if freeze.get("controls", {}).get("candidate_input_definition_frozen") is not True:
        raise RuntimeError("candidate input definition is not frozen")
    if freeze.get("controls", {}).get("candidate_regime_assignment_logic_frozen") is not True:
        raise RuntimeError("candidate regime assignment logic is not frozen")
    if freeze.get("controls", {}).get("v3_regime_definition_authorized") is not False:
        raise RuntimeError("regime definition must remain unauthorized")
    if authorization.get("authorization_scope", {}).get("research_role") != "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE":
        raise RuntimeError("research role changed")

    history_path = Path(args.history_csv).resolve()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("output directory must not already contain files")
    output_dir.mkdir(parents=True, exist_ok=True)

    history = load_history(history_path)
    counts = history.groupby("vehicle_id").size()
    if counts.nunique() != 1:
        raise RuntimeError(f"history coverage is not balanced by vehicle: {counts.to_dict()}")

    feature_frames = []
    label_frames = []
    for _, group in history.groupby("vehicle_id", sort=True):
        features = build_vehicle_features(group, freeze)
        feature_frames.append(features)
        label_frames.append(classify_vehicle(features, freeze))
    labels = pd.concat(label_frames, ignore_index=True)
    labels = labels.sort_values(["vehicle_id", "observation_date"], kind="mergesort").reset_index(drop=True)

    input_definition_path = output_dir / "versioned_candidate_input_definition.json"
    rule_definition_path = output_dir / "versioned_candidate_regime_assignment_logic.json"
    ledger_path = output_dir / "point_in_time_regime_label_ledger.csv"
    ledger_sha_path = output_dir / "point_in_time_regime_label_ledger_sha256.txt"

    write_json(input_definition_path, {
        "freeze_id": freeze["freeze_id"],
        "price_basis": freeze["price_basis"],
        "candidate_input_definitions": freeze["candidate_input_definitions"],
        "point_in_time_adaptive_thresholds": freeze["point_in_time_adaptive_thresholds"],
    })
    write_json(rule_definition_path, {
        "freeze_id": freeze["freeze_id"],
        "candidate_regime_assignment_logic": freeze["candidate_regime_assignment_logic"],
    })

    labels.to_csv(ledger_path, index=False, quoting=csv.QUOTE_MINIMAL, lineterminator="\n", float_format="%.12g")
    ledger_sha = sha256_file(ledger_path)
    ledger_sha_path.write_text(ledger_sha + "\n", encoding="ascii")

    # Governance boundary: forward outcomes are not calculated until the complete label ledger exists and is hashed.
    horizons = [int(value) for value in freeze["research_outcome_protocol"]["subsequent_return_horizons_trading_days"]]
    outcomes = calculate_outcomes(history, labels, horizons)

    support = labels.groupby(
        ["vehicle_id", "exposure_family", "is_reference_control", "candidate_regime", "eligible"],
        dropna=False,
    ).size().reset_index(name="observation_count")
    support_path = output_dir / "regime_support_by_vehicle_and_exposure_family.csv"
    support.to_csv(support_path, index=False, lineterminator="\n")

    outcome_summary = summarize_outcomes(outcomes)
    outcome_summary_path = output_dir / "subsequent_outcome_research_summary.csv"
    outcome_summary.to_csv(outcome_summary_path, index=False, lineterminator="\n", float_format="%.12g")

    eligible_opportunities = labels[labels["eligible"] & (~labels["is_reference_control"])].copy()
    regime_counts = eligible_opportunities["candidate_regime"].value_counts().to_dict()
    family_counts = eligible_opportunities.groupby("candidate_regime")["exposure_family"].nunique().to_dict()
    minimum_support = int(freeze["support_and_exposure_family_controls"]["minimum_compared_group_support"])
    directional = ["TREND_PERSISTENCE", "MEAN_REVERSION_OR_EXHAUSTION"]
    support_gate = all(int(regime_counts.get(name, 0)) >= minimum_support for name in directional)

    separability = {
        "research_role": "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE",
        "candidate_regime_observation_counts": {key: int(value) for key, value in regime_counts.items()},
        "candidate_regime_exposure_family_counts": {key: int(value) for key, value in family_counts.items()},
        "minimum_compared_group_support": minimum_support,
        "directional_regime_minimum_support_gate_met": bool(support_gate),
        "automatic_regime_definition_lock_authorized": False,
        "interpretation": "Development evidence only; separability and support require separate governance review.",
    }
    write_json(output_dir / "regime_separability_summary.json", separability)

    conflict_summary = {
        "eligible_opportunity_rows": int(len(eligible_opportunities)),
        "neutral_or_uncertain_rows": int((eligible_opportunities["candidate_regime"] == "NEUTRAL_OR_UNCERTAIN").sum()),
        "neutral_or_uncertain_rate": float((eligible_opportunities["candidate_regime"] == "NEUTRAL_OR_UNCERTAIN").mean()) if len(eligible_opportunities) else None,
        "ineligible_rows": int((~labels["eligible"]).sum()),
        "neutral_is_fail_closed_default": True,
    }
    write_json(output_dir / "conflict_and_neutral_assignment_summary.json", conflict_summary)

    write_json(output_dir / "overlapping_forward_window_disclosure.json", {
        "overlapping_forward_windows_present": True,
        "horizons_trading_days": horizons,
        "independence_claim_prohibited": True,
        "disclosure": "Adjacent point-in-time observations have overlapping forward windows; observation counts are not independent-sample counts.",
    })
    write_json(output_dir / "consumed_evidence_disclosure.json", {
        "research_role": "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE",
        "source_history_csv": str(history_path),
        "source_history_sha256": sha256_file(history_path),
        "v1_v2_intervals_remain_consumed": True,
        "unseen_validation_claim_authorized": False,
    })
    write_json(output_dir / "development_not_validation_disclosure.json", {
        "development_evidence_not_unseen_validation": True,
        "v3_regime_definition_authorized": False,
        "tactical_posture_authorized": False,
        "new_validation_outcome_inspection_authorized": False,
        "presentation_activation_authorized": False,
        "production_database_write_authorized": False,
    })

    manifest_files = sorted(path for path in output_dir.iterdir() if path.is_file() and path.name != "manifest.json")
    manifest = {
        "execution_id": "METALS-TACTICAL-POLICY-V3-HISTORICAL-REGIME-RESEARCH-EXECUTION-1",
        "freeze_id": freeze["freeze_id"],
        "rule_version": freeze["candidate_regime_assignment_logic"]["logic_version"],
        "research_role": "DEVELOPMENT_ONLY_ON_CONSUMED_EVIDENCE",
        "history_row_count": int(len(history)),
        "vehicle_count": int(history["vehicle_id"].nunique()),
        "observations_per_vehicle": int(counts.iloc[0]),
        "label_ledger_row_count": int(len(labels)),
        "label_ledger_sha256": ledger_sha,
        "directional_regime_minimum_support_gate_met": bool(support_gate),
        "output_files": {path.name: sha256_file(path) for path in manifest_files},
        "regime_definition_authorized": False,
        "tactical_posture_authorized": False,
        "unseen_validation_claim_authorized": False,
        "next_decision": "REVIEW_METALS_TACTICAL_POLICY_V3_HISTORICAL_REGIME_RESEARCH_RESULTS",
    }
    write_json(output_dir / "manifest.json", manifest)

    print(json.dumps({
        "status": "PASS",
        "execution_id": manifest["execution_id"],
        "research_role": manifest["research_role"],
        "history_row_count": manifest["history_row_count"],
        "vehicle_count": manifest["vehicle_count"],
        "observations_per_vehicle": manifest["observations_per_vehicle"],
        "label_ledger_row_count": manifest["label_ledger_row_count"],
        "label_ledger_sha256": ledger_sha,
        "directional_regime_minimum_support_gate_met": bool(support_gate),
        "regime_definition_authorized": False,
        "tactical_posture_authorized": False,
        "unseen_validation_claim_authorized": False,
        "output_dir": str(output_dir),
        "next_decision": manifest["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
