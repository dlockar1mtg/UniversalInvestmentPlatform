from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from execute_metals_tactical_policy_v3_historical_regime_research import (
    build_vehicle_features,
    classify_vehicle,
)

ROOT = Path(__file__).resolve().parents[1]
FREEZE_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_historical_regime_research_freeze.json"
AUTH_PATH = ROOT / "config" / "metals" / "tactical_policy_v3_new_unseen_validation_outcome_inspection_authorization.json"

EXPECTED_UNSEEN_HISTORY_SHA = "597a979ad5b5c031b4c15b84e3d8b23389c780e9a3fc5a19bd1b06ca4b61a6d5"
EXPECTED_UNSEEN_COVERAGE_SHA = "3de3cb2d21ff247f78e210372bc5505bf13d5b3fd2475260fc84cfb514d91c7e"
EXPECTED_UNSEEN_MANIFEST_SHA = "69ed6ff5324f148734a8b84e672e028fcd2e17893bfac4b4c402063916dcf205"
EXPECTED_V2_HISTORY_SHA = "400aa5792533653eccf7bdfb3dd4b67fddb8f45ad138bda1a7d4ac1c1137bd62"
START_DATE = "2023-08-22"
END_DATE = "2026-08-24"
HORIZONS = [21, 63, 126]
ACTION_MAP = {
    "TREND_PERSISTENCE": "TACTICAL_SUPPORTIVE",
    "MEAN_REVERSION_OR_EXHAUSTION": "TACTICAL_DEFENSIVE",
    "NEUTRAL_OR_UNCERTAIN": "NO_TACTICAL_OVERLAY",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_jsonl_history(path: Path, end_date: str | None = None) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            date = str(row["observation_date"])
            if end_date is not None and date > end_date:
                continue
            ticker = str(row["ticker"]).strip().upper()
            rows.append({
                "vehicle_id": ticker,
                "observation_date": pd.to_datetime(date).date(),
                "unadjusted_close": float(row["close_usd"]),
            })
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise RuntimeError(f"history is empty: {path}")
    if frame.duplicated(["vehicle_id", "observation_date"]).any():
        raise RuntimeError(f"duplicate vehicle/date rows found: {path}")
    if (~np.isfinite(frame["unadjusted_close"].to_numpy(dtype=float))).any() or (frame["unadjusted_close"] <= 0).any():
        raise RuntimeError(f"invalid unadjusted close found: {path}")
    return frame.sort_values(["vehicle_id", "observation_date"], kind="mergesort").reset_index(drop=True)


def calculate_outcomes(history: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    outcomes: list[dict[str, Any]] = []
    by_vehicle = {
        vehicle: group.sort_values("observation_date").reset_index(drop=True)
        for vehicle, group in history.groupby("vehicle_id", sort=True)
    }
    for _, label in labels.iterrows():
        vehicle = str(label["vehicle_id"])
        date = pd.to_datetime(label["observation_date"]).date()
        group = by_vehicle[vehicle]
        matches = group.index[group["observation_date"] == date].tolist()
        if len(matches) != 1:
            raise RuntimeError(f"label date not uniquely present in history: {vehicle} {date}")
        i = int(matches[0])
        current = float(group.loc[i, "unadjusted_close"])
        for horizon in HORIZONS:
            j = i + horizon
            if j >= len(group):
                continue
            future = float(group.loc[j, "unadjusted_close"])
            path = group.loc[i + 1:j, "unadjusted_close"].astype(float).to_numpy()
            excursions = 100.0 * (path / current - 1.0)
            outcomes.append({
                "vehicle_id": vehicle,
                "observation_date": date.isoformat(),
                "exposure_family": str(label["exposure_family"]),
                "candidate_regime": str(label["candidate_regime"]),
                "candidate_action_state": str(label["candidate_action_state"]),
                "eligible": bool(label["eligible"]),
                "is_reference_control": bool(label["is_reference_control"]),
                "horizon_trading_days": int(horizon),
                "forward_return_pct": 100.0 * (future / current - 1.0),
                "mae_pct": float(np.min(excursions)),
                "mfe_pct": float(np.max(excursions)),
            })
    return pd.DataFrame(outcomes)


def summarize_state(outcomes: pd.DataFrame, state: str, horizon: int) -> dict[str, Any]:
    subset = outcomes[
        (outcomes["candidate_action_state"] == state)
        & (outcomes["horizon_trading_days"] == horizon)
        & (outcomes["eligible"] == True)
        & (outcomes["is_reference_control"] == False)
    ].copy()
    return {
        "observation_count": int(len(subset)),
        "vehicle_count": int(subset["vehicle_id"].nunique()) if len(subset) else 0,
        "exposure_family_count": int(subset["exposure_family"].nunique()) if len(subset) else 0,
        "mean_forward_return_pct": float(subset["forward_return_pct"].mean()) if len(subset) else None,
        "median_forward_return_pct": float(subset["forward_return_pct"].median()) if len(subset) else None,
        "positive_return_rate": float((subset["forward_return_pct"] > 0).mean()) if len(subset) else None,
        "mean_mae_pct": float(subset["mae_pct"].mean()) if len(subset) else None,
        "mean_mfe_pct": float(subset["mfe_pct"].mean()) if len(subset) else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unseen-package-dir", required=True)
    parser.add_argument("--v2-history", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    unseen_root = Path(args.unseen_package_dir).resolve()
    v2_history_path = Path(args.v2_history).resolve()
    output_dir = Path(args.output_dir).resolve()
    if output_dir.exists():
        raise RuntimeError(f"output directory already exists: {output_dir}")

    unseen_history = unseen_root / "metals_v3_new_unseen_validation_history.jsonl"
    unseen_coverage = unseen_root / "coverage.json"
    unseen_manifest = unseen_root / "manifest.json"
    for path in [unseen_history, unseen_coverage, unseen_manifest, v2_history_path, FREEZE_PATH, AUTH_PATH]:
        if not path.is_file():
            raise RuntimeError(f"required input missing: {path}")

    if sha256_file(unseen_history) != EXPECTED_UNSEEN_HISTORY_SHA:
        raise RuntimeError("unseen history hash mismatch")
    if sha256_file(unseen_coverage) != EXPECTED_UNSEEN_COVERAGE_SHA:
        raise RuntimeError("unseen coverage hash mismatch")
    if sha256_file(unseen_manifest) != EXPECTED_UNSEEN_MANIFEST_SHA:
        raise RuntimeError("unseen manifest hash mismatch")
    if sha256_file(v2_history_path) != EXPECTED_V2_HISTORY_SHA:
        raise RuntimeError("V2 warmup history hash mismatch")

    auth = load_json(AUTH_PATH)
    freeze = load_json(FREEZE_PATH)
    if auth["controls"]["new_validation_outcome_inspection_authorized"] is not True:
        raise RuntimeError("outcome inspection is not authorized")
    if auth["controls"]["new_validation_result_authorized"] is not True:
        raise RuntimeError("validation result calculation is not authorized")
    if auth["controls"]["network_collection_authorized"] is not False:
        raise RuntimeError("network collection must remain unauthorized")

    v2 = load_jsonl_history(v2_history_path, end_date="2023-08-21")
    unseen = load_jsonl_history(unseen_history)
    unseen_dates = unseen["observation_date"].map(lambda d: d.isoformat())
    if unseen_dates.min() < START_DATE or unseen_dates.max() > END_DATE:
        raise RuntimeError("unseen history interval changed")

    history = pd.concat([v2, unseen], ignore_index=True)
    if history.duplicated(["vehicle_id", "observation_date"]).any():
        raise RuntimeError("combined warmup/unseen history overlaps")
    history = history.sort_values(["vehicle_id", "observation_date"], kind="mergesort").reset_index(drop=True)

    label_frames: list[pd.DataFrame] = []
    for vehicle, group in history.groupby("vehicle_id", sort=True):
        features = build_vehicle_features(group.reset_index(drop=True), freeze)
        labels = classify_vehicle(features, freeze)
        labels = labels[(labels["observation_date"] >= START_DATE) & (labels["observation_date"] <= END_DATE)].copy()
        label_frames.append(labels)
    label_ledger = pd.concat(label_frames, ignore_index=True)
    label_ledger["candidate_action_state"] = label_ledger["candidate_regime"].map(ACTION_MAP)
    if label_ledger["candidate_action_state"].isna().any():
        raise RuntimeError("unmapped candidate regime found")
    if label_ledger["observation_date"].min() < START_DATE:
        raise RuntimeError("consumed V2 row entered unseen label ledger")

    output_dir.mkdir(parents=True, exist_ok=False)
    label_path = output_dir / "unseen_label_ledger.csv"
    label_ledger.to_csv(label_path, index=False, quoting=csv.QUOTE_MINIMAL)
    label_sha = sha256_file(label_path)

    # Governance boundary: outcomes are calculated only after the label ledger is persisted and hashed above.
    outcomes = calculate_outcomes(history, label_ledger)
    outcome_path = output_dir / "unseen_outcome_ledger.csv"
    outcomes.to_csv(outcome_path, index=False, quoting=csv.QUOTE_MINIMAL)
    outcome_sha = sha256_file(outcome_path)

    summaries: dict[str, Any] = {}
    for horizon in HORIZONS:
        summaries[f"{horizon}d"] = {
            "TACTICAL_SUPPORTIVE": summarize_state(outcomes, "TACTICAL_SUPPORTIVE", horizon),
            "TACTICAL_DEFENSIVE": summarize_state(outcomes, "TACTICAL_DEFENSIVE", horizon),
            "NO_TACTICAL_OVERLAY": summarize_state(outcomes, "NO_TACTICAL_OVERLAY", horizon),
        }

    primary = summaries["63d"]
    supportive = primary["TACTICAL_SUPPORTIVE"]
    defensive = primary["TACTICAL_DEFENSIVE"]
    support_gate = supportive["observation_count"] >= 20 and defensive["observation_count"] >= 20
    family_gate = supportive["exposure_family_count"] >= 2 and defensive["exposure_family_count"] >= 2

    checks = {
        "supportive_median_return_exceeds_defensive": False,
        "supportive_positive_return_rate_exceeds_defensive": False,
        "supportive_mean_mae_less_negative_than_defensive": False,
    }
    if support_gate and family_gate:
        checks = {
            "supportive_median_return_exceeds_defensive": supportive["median_forward_return_pct"] > defensive["median_forward_return_pct"],
            "supportive_positive_return_rate_exceeds_defensive": supportive["positive_return_rate"] > defensive["positive_return_rate"],
            "supportive_mean_mae_less_negative_than_defensive": supportive["mean_mae_pct"] > defensive["mean_mae_pct"],
        }

    if not (support_gate and family_gate):
        result = "INCONCLUSIVE"
    elif all(checks.values()):
        result = "PASS"
    else:
        result = "FAIL"

    regime_counts = {
        str(k): int(v)
        for k, v in label_ledger[
            (label_ledger["eligible"] == True) & (label_ledger["is_reference_control"] == False)
        ]["candidate_regime"].value_counts().to_dict().items()
    }

    result_payload = {
        "execution_id": "METALS-TACTICAL-POLICY-V3-NEW-UNSEEN-VALIDATION-OUTCOME-INSPECTION-1",
        "authorization_id": auth["authorization_id"],
        "package_id": auth["frozen_unseen_package"]["package_id"],
        "source_classifier_rule_version": "METALS-V3-REGIME-CANDIDATE-RULES-1",
        "source_action_mapping_version": "METALS-V3-ACTION-MAPPING-1",
        "validation_interval": {"start": START_DATE, "end": END_DATE},
        "primary_horizon_trading_days": 63,
        "secondary_horizons_trading_days": [21, 126],
        "minimum_compared_group_support": 20,
        "minimum_distinct_exposure_families_per_directional_state": 2,
        "label_ledger_sha256": label_sha,
        "outcome_ledger_sha256": outcome_sha,
        "label_ledger_hashed_before_outcome_calculation": True,
        "v2_history_used_only_for_point_in_time_warmup": True,
        "v2_rows_entered_new_validation_labels_or_outcomes": False,
        "regime_counts": regime_counts,
        "outcomes_by_action_state": summaries,
        "primary_support_gate_met": support_gate,
        "primary_exposure_family_gate_met": family_gate,
        "primary_directional_checks": checks,
        "all_three_primary_directional_checks_met": bool(all(checks.values())) if support_gate and family_gate else False,
        "secondary_horizons_cannot_substitute_for_primary_failure": True,
        "overlapping_forward_windows_present": True,
        "validation_result": result,
        "tactical_posture_authorized": False,
        "presentation_activation_authorized": False,
        "production_database_write_authorized": False,
        "next_decision": "REVIEW_METALS_TACTICAL_POLICY_V3_UNSEEN_VALIDATION_RESULT",
    }
    result_path = output_dir / "validation_result.json"
    write_json(result_path, result_payload)
    result_sha = sha256_file(result_path)

    execution_manifest = {
        "execution_id": result_payload["execution_id"],
        "authorization_id": auth["authorization_id"],
        "package_id": result_payload["package_id"],
        "unseen_history_sha256": EXPECTED_UNSEEN_HISTORY_SHA,
        "unseen_coverage_sha256": EXPECTED_UNSEEN_COVERAGE_SHA,
        "unseen_manifest_sha256": EXPECTED_UNSEEN_MANIFEST_SHA,
        "v2_warmup_history_sha256": EXPECTED_V2_HISTORY_SHA,
        "label_ledger_file": label_path.name,
        "label_ledger_sha256": label_sha,
        "outcome_ledger_file": outcome_path.name,
        "outcome_ledger_sha256": outcome_sha,
        "validation_result_file": result_path.name,
        "validation_result_sha256": result_sha,
        "network_collection_executed": False,
        "production_database_write_executed": False,
        "presentation_activation_executed": False,
        "tactical_posture_authorized": False,
        "execution_consumed_once": True,
        "next_decision": result_payload["next_decision"],
    }
    manifest_path = output_dir / "manifest.json"
    write_json(manifest_path, execution_manifest)

    print(json.dumps({
        "status": "PASS",
        "execution_id": result_payload["execution_id"],
        "validation_result": result,
        "label_ledger_sha256": label_sha,
        "outcome_ledger_sha256": outcome_sha,
        "validation_result_sha256": result_sha,
        "primary_support_gate_met": support_gate,
        "primary_exposure_family_gate_met": family_gate,
        "all_three_primary_directional_checks_met": result_payload["all_three_primary_directional_checks_met"],
        "supportive_63d_observation_count": supportive["observation_count"],
        "defensive_63d_observation_count": defensive["observation_count"],
        "supportive_63d_exposure_family_count": supportive["exposure_family_count"],
        "defensive_63d_exposure_family_count": defensive["exposure_family_count"],
        "network_collection_executed": False,
        "tactical_posture_authorized": False,
        "next_decision": result_payload["next_decision"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
