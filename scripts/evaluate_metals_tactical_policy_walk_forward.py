from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = ROOT / "config" / "metals" / "tactical_policy_walk_forward_evaluation.json"
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_walk_forward_evaluation_design.json"
RULE_PATH = ROOT / "config" / "metals" / "tactical_policy_candidate_rule_design.json"

OPPORTUNITY = (
    "metals:vehicle:COPX", "metals:vehicle:CPER", "metals:vehicle:GLD",
    "metals:vehicle:IAU", "metals:vehicle:PPLT", "metals:vehicle:SGOL",
    "metals:vehicle:SIVR", "metals:vehicle:SLV", "metals:vehicle:URA",
    "metals:vehicle:URNM",
)
REFERENCE = "metals:vehicle:BIL"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    return parser.parse_args()


def pct(a: float, b: float) -> float:
    return 100.0 * (a / b - 1.0)


def median(values: list[float]) -> float | None:
    return None if not values else float(statistics.median(values))


def mean(values: list[float]) -> float | None:
    return None if not values else float(statistics.fmean(values))


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * q
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return float(ordered[low])
    weight = position - low
    return float(ordered[low] * (1.0 - weight) + ordered[high] * weight)


def sample_stdev(values: list[float]) -> float:
    return 0.0 if len(values) < 2 else float(statistics.stdev(values))


def features(prices: list[float], index: int) -> dict[str, float]:
    current = prices[index]
    returns_63 = [prices[j] / prices[j - 1] - 1.0 for j in range(index - 62, index + 1)]
    trailing_252 = prices[index - 251:index + 1]
    return {
        "return_1m_pct": pct(current, prices[index - 21]),
        "return_3m_pct": pct(current, prices[index - 63]),
        "return_6m_pct": pct(current, prices[index - 126]),
        "distance_ma50_pct": pct(current, statistics.fmean(prices[index - 49:index + 1])),
        "distance_ma200_pct": pct(current, statistics.fmean(prices[index - 199:index + 1])),
        "current_drawdown_pct": pct(current, max(trailing_252)),
        "realized_volatility_3m_pct": sample_stdev(returns_63) * math.sqrt(252.0) * 100.0,
    }


def score_candidate(values: dict[str, float], rule: dict[str, object]) -> tuple[int, str]:
    signals = rule["candidate_signal_rules"]
    score = 0
    pairs = (
        ("return_1m", "return_1m_pct"),
        ("return_3m", "return_3m_pct"),
        ("return_6m", "return_6m_pct"),
        ("distance_ma50", "distance_ma50_pct"),
        ("distance_ma200", "distance_ma200_pct"),
    )
    for rule_key, value_key in pairs:
        spec = signals[rule_key]
        value = values[value_key]
        weight = int(spec["weight"])
        if value >= float(spec["positive_if_gte"]):
            score += weight
        elif value <= float(spec["negative_if_lte"]):
            score -= weight

    drawdown = values["current_drawdown_pct"]
    dd = signals["drawdown_penalty"]
    if drawdown <= float(dd["penalty_2_if_lte"]):
        score -= 2
    elif drawdown <= float(dd["penalty_1_if_lte"]):
        score -= 1

    if values["realized_volatility_3m_pct"] >= float(signals["volatility_penalty"]["penalty_1_if_gte"]):
        score -= 1

    mapping = rule["candidate_score_mapping"]
    if score >= int(mapping["ACCUMULATE"]["minimum_score"]):
        posture = "ACCUMULATE"
    elif score >= int(mapping["HOLD"]["minimum_score"]):
        posture = "HOLD"
    elif score >= int(mapping["WATCH"]["minimum_score"]):
        posture = "WATCH"
    elif score >= int(mapping["REDUCE"]["minimum_score"]):
        posture = "REDUCE"
    else:
        posture = "AVOID"
    return score, posture


def summarize(rows: list[dict[str, object]], horizon: int) -> dict[str, object]:
    returns = [float(row[f"forward_return_{horizon}d_pct"]) for row in rows]
    mae = [float(row[f"mae_{horizon}d_pct"]) for row in rows]
    mfe = [float(row[f"mfe_{horizon}d_pct"]) for row in rows]
    return {
        "observation_count": len(rows),
        "mean_forward_return_pct": mean(returns),
        "median_forward_return_pct": median(returns),
        "positive_return_rate": None if not returns else sum(1 for value in returns if value > 0) / len(returns),
        "p25_forward_return_pct": percentile(returns, 0.25),
        "p75_forward_return_pct": percentile(returns, 0.75),
        "mean_maximum_adverse_excursion_pct": mean(mae),
        "median_maximum_adverse_excursion_pct": median(mae),
        "mean_maximum_favorable_excursion_pct": mean(mfe),
    }


def grouped_metrics(rows: list[dict[str, object]], horizons: list[int]) -> dict[str, object]:
    output: dict[str, object] = {}
    for posture in ("ACCUMULATE", "HOLD", "WATCH", "REDUCE", "AVOID"):
        posture_rows = [row for row in rows if row["posture"] == posture]
        output[posture] = {f"{h}d": summarize(posture_rows, h) for h in horizons}
    constructive = [row for row in rows if row["posture"] in {"ACCUMULATE", "HOLD"}]
    defensive = [row for row in rows if row["posture"] in {"REDUCE", "AVOID"}]
    neutral = [row for row in rows if row["posture"] == "WATCH"]
    output["CONSTRUCTIVE"] = {f"{h}d": summarize(constructive, h) for h in horizons}
    output["NEUTRAL"] = {f"{h}d": summarize(neutral, h) for h in horizons}
    output["DEFENSIVE"] = {f"{h}d": summarize(defensive, h) for h in horizons}
    output["POOLED"] = {f"{h}d": summarize(rows, h) for h in horizons}
    return output


def behavior_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    by_asset: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_asset[str(row["asset_id"])].append(row)
    changes = 0
    comparisons = 0
    run_lengths: list[int] = []
    for asset_rows in by_asset.values():
        ordered = sorted(asset_rows, key=lambda item: int(item["grid_position"]))
        if not ordered:
            continue
        run = 1
        for prior, current in zip(ordered, ordered[1:]):
            comparisons += 1
            if prior["posture"] != current["posture"]:
                changes += 1
                run_lengths.append(run)
                run = 1
            else:
                run += 1
        run_lengths.append(run)
    distribution = Counter(str(row["posture"]) for row in rows)
    return {
        "posture_distribution": dict(sorted(distribution.items())),
        "posture_change_count": changes,
        "posture_change_rate": 0.0 if comparisons == 0 else changes / comparisons,
        "mean_consecutive_grid_points_in_same_posture": mean([float(x) for x in run_lengths]),
    }


def main() -> int:
    authorization = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    rule = json.loads(RULE_PATH.read_text(encoding="utf-8"))
    if authorization.get("evaluation_id") != "METALS-TACTICAL-POLICY-WALK-FORWARD-EVALUATION-1":
        raise RuntimeError("unexpected walk-forward evaluation authorization")
    controls = authorization.get("controls") or {}
    if controls.get("forward_outcome_calculation_authorized") is not True or controls.get("historical_candidate_evaluation_authorized") is not True:
        raise RuntimeError("walk-forward calculation is not authorized")
    for key in (
        "candidate_threshold_change_authorized", "tactical_posture_authorized",
        "presentation_activation_authorized", "production_database_write_authorized",
        "native_source_query_authorized", "export_execution_authorized",
        "forecast_refresh_authorized", "model_retraining_authorized",
        "cross_domain_rank_authorized", "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited control changed unexpectedly: {key}")

    package_dir = Path(parse_args().package_dir).resolve()
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("package_id") != authorization["source_package_id"]:
        raise RuntimeError("unexpected source package")
    if manifest.get("source_authority") != authorization["source_authority"]:
        raise RuntimeError("unexpected source authority")

    by_asset: dict[str, list[dict[str, object]]] = defaultdict(list)
    with (package_dir / "metals_price_history.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            by_asset[str(row["asset_id"])].append(row)

    expected_assets = set(OPPORTUNITY) | {REFERENCE}
    if set(by_asset) != expected_assets:
        raise RuntimeError("price-history asset coverage changed")

    horizons = [int(x) for x in design["evaluation_grid"]["forward_horizons_observations"]]
    step = int(design["evaluation_grid"]["walk_forward_step_observations"])
    development_n = int(design["evaluation_grid"]["development_grid_points_per_asset"])
    holdout_n = int(design["evaluation_grid"]["holdout_grid_points_per_asset"])
    max_horizon = max(horizons)
    evaluation_rows: list[dict[str, object]] = []

    for asset_id in sorted(expected_assets):
        asset_rows = sorted(by_asset[asset_id], key=lambda row: str(row["observation_date"]))
        if len(asset_rows) != int(authorization["expected_history_observations_per_asset"]):
            raise RuntimeError(f"unexpected history count for {asset_id}")
        prices = [float(row["adjusted_close_usd"] if row["adjusted_close_usd"] is not None else row["close_usd"]) for row in asset_rows]
        indexes = list(range(251, len(prices) - max_horizon, step))
        if len(indexes) != int(authorization["expected_grid_points_per_asset"]):
            raise RuntimeError(f"unexpected grid count for {asset_id}: {len(indexes)}")
        if len(indexes[:development_n]) != development_n or len(indexes[development_n:]) != holdout_n:
            raise RuntimeError("development/holdout split changed")

        for grid_position, index in enumerate(indexes):
            input_values = features(prices, index)
            score, posture = score_candidate(input_values, rule)
            role = "REFERENCE_CONTROL" if asset_id == REFERENCE else "TACTICAL_OPPORTUNITY"
            if role == "REFERENCE_CONTROL":
                posture = "REFERENCE_CONTROL"
            split = "DEVELOPMENT" if grid_position < development_n else "HOLDOUT"
            result: dict[str, object] = {
                "asset_id": asset_id,
                "role": role,
                "split": split,
                "grid_position": grid_position,
                "decision_date": str(asset_rows[index]["observation_date"]),
                "candidate_score": score,
                "posture": posture,
            }
            if role == "TACTICAL_OPPORTUNITY":
                result.update(input_values)
            entry = prices[index]
            for horizon in horizons:
                future = prices[index + 1:index + horizon + 1]
                result[f"forward_return_{horizon}d_pct"] = pct(prices[index + horizon], entry)
                result[f"mae_{horizon}d_pct"] = min(pct(value, entry) for value in future)
                result[f"mfe_{horizon}d_pct"] = max(pct(value, entry) for value in future)
            evaluation_rows.append(result)

    opportunity_rows = [row for row in evaluation_rows if row["role"] == "TACTICAL_OPPORTUNITY"]
    reference_rows = [row for row in evaluation_rows if row["role"] == "REFERENCE_CONTROL"]
    development = [row for row in opportunity_rows if row["split"] == "DEVELOPMENT"]
    holdout = [row for row in opportunity_rows if row["split"] == "HOLDOUT"]
    if len(development) != int(authorization["expected_development_opportunity_points"]):
        raise RuntimeError("development observation count changed")
    if len(holdout) != int(authorization["expected_holdout_opportunity_points"]):
        raise RuntimeError("holdout observation count changed")

    dev_metrics = grouped_metrics(development, horizons)
    hold_metrics = grouped_metrics(holdout, horizons)
    dev_behavior = behavior_metrics(development)
    hold_behavior = behavior_metrics(holdout)
    bil_development = [row for row in reference_rows if row["split"] == "DEVELOPMENT"]
    bil_holdout = [row for row in reference_rows if row["split"] == "HOLDOUT"]

    minimum_support = int(design["candidate_pass_fail_rules"]["minimum_supported_holdout_observations_per_compared_group"])
    constructive_63 = hold_metrics["CONSTRUCTIVE"]["63d"]
    defensive_63 = hold_metrics["DEFENSIVE"]["63d"]
    support_met = int(constructive_63["observation_count"]) >= minimum_support and int(defensive_63["observation_count"]) >= minimum_support

    checks = {
        "constructive_63d_median_return_gt_defensive": False,
        "constructive_63d_positive_rate_gt_defensive": False,
        "defensive_63d_mean_mae_no_worse_than_constructive": False,
        "holdout_posture_change_rate_lte_0_50": hold_behavior["posture_change_rate"] <= 0.50,
        "minimum_group_support_met": support_met,
        "no_semantic_or_governance_violation": True,
    }
    if support_met:
        checks["constructive_63d_median_return_gt_defensive"] = float(constructive_63["median_forward_return_pct"]) > float(defensive_63["median_forward_return_pct"])
        checks["constructive_63d_positive_rate_gt_defensive"] = float(constructive_63["positive_return_rate"]) > float(defensive_63["positive_return_rate"])
        checks["defensive_63d_mean_mae_no_worse_than_constructive"] = float(defensive_63["mean_maximum_adverse_excursion_pct"]) >= float(constructive_63["mean_maximum_adverse_excursion_pct"])

    if not support_met:
        candidate_result = "INCONCLUSIVE"
    elif all(checks[key] for key in (
        "constructive_63d_median_return_gt_defensive",
        "constructive_63d_positive_rate_gt_defensive",
        "defensive_63d_mean_mae_no_worse_than_constructive",
        "holdout_posture_change_rate_lte_0_50",
        "no_semantic_or_governance_violation",
    )):
        candidate_result = "PASS"
    else:
        candidate_result = "FAIL"

    buy_hold_by_asset = []
    for asset_id in OPPORTUNITY:
        asset_rows = sorted(by_asset[asset_id], key=lambda row: str(row["observation_date"]))
        prices = [float(row["adjusted_close_usd"] if row["adjusted_close_usd"] is not None else row["close_usd"]) for row in asset_rows]
        first_eval_index = 251
        buy_hold_by_asset.append({
            "asset_id": asset_id,
            "start_date": str(asset_rows[first_eval_index]["observation_date"]),
            "end_date": str(asset_rows[-1]["observation_date"]),
            "total_return_pct": pct(prices[-1], prices[first_eval_index]),
        })

    result = {
        "status": "PASS",
        "read_only": True,
        "evaluation_id": authorization["evaluation_id"],
        "source_evaluation_design": authorization["source_evaluation_design"],
        "source_candidate_rule_design": authorization["source_candidate_rule_design"],
        "source_package_id": authorization["source_package_id"],
        "source_authority": authorization["source_authority"],
        "candidate_rules_changed": False,
        "candidate_thresholds_changed": False,
        "forward_outcomes_calculated": True,
        "historical_candidate_evaluation_executed": True,
        "opportunity_vehicle_count": len(OPPORTUNITY),
        "reference_control_count": 1,
        "development_opportunity_points": len(development),
        "holdout_opportunity_points": len(holdout),
        "development_metrics": dev_metrics,
        "holdout_metrics": hold_metrics,
        "development_policy_behavior": dev_behavior,
        "holdout_policy_behavior": hold_behavior,
        "bil_reference_control": {
            "development": {f"{h}d": summarize(bil_development, h) for h in horizons},
            "holdout": {f"{h}d": summarize(bil_holdout, h) for h in horizons},
        },
        "baselines": {
            "development_pooled_opportunity": dev_metrics["POOLED"],
            "holdout_pooled_opportunity": hold_metrics["POOLED"],
            "buy_and_hold_by_asset": buy_hold_by_asset,
        },
        "holdout_candidate_checks": checks,
        "candidate_validation_result": candidate_result,
        "overlapping_forward_windows_disclosed": True,
        "vehicle_cluster_dependence_disclosed": True,
        "duplicate_exposure_families_not_independent_confirmation": True,
        "tactical_posture_authorized": False,
        "presentation_activation_executed": False,
        "production_database_write_executed": False,
        "native_source_query_executed": False,
        "export_execution_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": authorization["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
