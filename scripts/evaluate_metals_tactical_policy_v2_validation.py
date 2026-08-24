from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_validation_evaluation.json"
DESIGN_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_validation_evaluation_design.json"
RULE_PATH = ROOT / "config" / "metals" / "tactical_policy_v2_candidate_rule_design.json"

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
    parser.add_argument("--output-path", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pct(a: float, b: float) -> float:
    return 100.0 * (a / b - 1.0)


def mean(values: list[float]) -> float | None:
    return None if not values else float(statistics.fmean(values))


def median(values: list[float]) -> float | None:
    return None if not values else float(statistics.median(values))


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    position = (len(ordered) - 1) * q
    lo = math.floor(position)
    hi = math.ceil(position)
    if lo == hi:
        return float(ordered[lo])
    weight = position - lo
    return float(ordered[lo] * (1.0 - weight) + ordered[hi] * weight)


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
    signals = rule["v2_candidate_signal_rules"]
    score = 0
    for rule_key, value_key in (
        ("return_1m", "return_1m_pct"),
        ("return_3m", "return_3m_pct"),
        ("return_6m", "return_6m_pct"),
        ("distance_ma50", "distance_ma50_pct"),
        ("distance_ma200", "distance_ma200_pct"),
    ):
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

    mapping = rule["v2_candidate_score_mapping"]
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
        "mean_return_pct": mean(returns),
        "median_return_pct": median(returns),
        "positive_return_rate": None if not returns else sum(1 for x in returns if x > 0.0) / len(returns),
        "p25_return_pct": percentile(returns, 0.25),
        "p75_return_pct": percentile(returns, 0.75),
        "mean_maximum_adverse_excursion_pct": mean(mae),
        "median_maximum_adverse_excursion_pct": median(mae),
        "mean_maximum_favorable_excursion_pct": mean(mfe),
        "median_maximum_favorable_excursion_pct": median(mfe),
    }


def grouped_metrics(rows: list[dict[str, object]], horizons: list[int]) -> dict[str, object]:
    output: dict[str, object] = {}
    for posture in ("ACCUMULATE", "HOLD", "WATCH", "REDUCE", "AVOID"):
        subset = [row for row in rows if row["posture"] == posture]
        output[posture] = {f"{h}d": summarize(subset, h) for h in horizons}
    constructive = [row for row in rows if row["posture"] in {"ACCUMULATE", "HOLD"}]
    defensive = [row for row in rows if row["posture"] in {"REDUCE", "AVOID"}]
    neutral = [row for row in rows if row["posture"] == "WATCH"]
    output["CONSTRUCTIVE"] = {f"{h}d": summarize(constructive, h) for h in horizons}
    output["DEFENSIVE"] = {f"{h}d": summarize(defensive, h) for h in horizons}
    output["NEUTRAL"] = {f"{h}d": summarize(neutral, h) for h in horizons}
    output["POOLED_NO_TACTICAL_OVERLAY"] = {f"{h}d": summarize(rows, h) for h in horizons}
    return output


def behavior_metrics(rows: list[dict[str, object]]) -> dict[str, object]:
    by_asset: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_asset[str(row["asset_id"])].append(row)
    changes = 0
    comparisons = 0
    run_lengths: list[int] = []
    for asset_rows in by_asset.values():
        ordered = sorted(asset_rows, key=lambda x: int(x["grid_position"]))
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
        "mean_consecutive_grid_points_same_posture": mean([float(x) for x in run_lengths]),
    }


def main() -> int:
    args = parse_args()
    authorization = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    design = json.loads(DESIGN_PATH.read_text(encoding="utf-8"))
    rule = json.loads(RULE_PATH.read_text(encoding="utf-8"))

    if authorization.get("evaluation_id") != "METALS-TACTICAL-POLICY-V2-VALIDATION-EVALUATION-1":
        raise RuntimeError("unexpected V2 evaluation authorization")
    controls = authorization.get("controls") or {}
    for key in ("validation_outcome_calculation_authorized", "historical_candidate_evaluation_authorized", "new_validation_outcome_inspection_authorized"):
        if controls.get(key) is not True:
            raise RuntimeError(f"required V2 evaluation control is not authorized: {key}")
    for key in (
        "candidate_rule_change_authorized", "candidate_threshold_change_authorized",
        "tactical_posture_authorized", "presentation_activation_authorized",
        "production_database_write_authorized", "native_source_query_authorized",
        "package_regeneration_authorized", "forecast_refresh_authorized",
        "model_retraining_authorized", "cross_domain_rank_authorized",
        "allocation_policy_authorized", "automatic_execution_authorized",
        "missing_authority_may_be_synthesized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited V2 evaluation control changed: {key}")

    package_dir = Path(args.package_dir).resolve()
    output_path = Path(args.output_path).resolve()
    if output_path.exists():
        raise RuntimeError(f"V2 validation output already exists and may not be overwritten: {output_path}")

    history_path = package_dir / "metals_v2_validation_history.jsonl"
    coverage_path = package_dir / "coverage.json"
    manifest_path = package_dir / "manifest.json"
    if sha256_file(history_path) != authorization["expected_history_sha256"]:
        raise RuntimeError("V2 validation history SHA-256 mismatch")
    if sha256_file(coverage_path) != authorization["expected_coverage_sha256"]:
        raise RuntimeError("V2 validation coverage SHA-256 mismatch")
    if sha256_file(manifest_path) != authorization["expected_manifest_sha256"]:
        raise RuntimeError("V2 validation manifest SHA-256 mismatch")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("package_id") != authorization["package_id"]:
        raise RuntimeError("unexpected V2 validation package")
    if manifest.get("outcome_blind") is not True:
        raise RuntimeError("V2 validation package did not remain outcome blind before evaluation")

    by_asset: dict[str, list[dict[str, object]]] = defaultdict(list)
    with history_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                by_asset[str(row["asset_id"])].append(row)

    expected_assets = set(OPPORTUNITY) | {REFERENCE}
    if set(by_asset) != expected_assets:
        raise RuntimeError("V2 validation asset coverage changed")

    grid = design["evaluation_grid"]
    horizons = [int(x) for x in grid["forward_horizons_observations"]]
    step = int(grid["walk_forward_step_observations"])
    first_index = int(grid["first_candidate_index_zero_based"])
    last_index = int(grid["last_forward_evaluable_index_zero_based"])
    expected_per_asset = int(grid["expected_grid_points_per_vehicle"])

    rows: list[dict[str, object]] = []
    buy_and_hold_context: dict[str, object] = {}
    for asset_id in sorted(expected_assets):
        asset_rows = sorted(by_asset[asset_id], key=lambda r: str(r["observation_date"]))
        if len(asset_rows) != int(authorization["expected_common_observation_count"]):
            raise RuntimeError(f"unexpected V2 history count for {asset_id}")
        prices = [float(r["adjusted_close_usd"] if r["adjusted_close_usd"] is not None else r["close_usd"]) for r in asset_rows]
        indexes = list(range(first_index, last_index + 1, step))
        if len(indexes) != expected_per_asset:
            raise RuntimeError(f"unexpected V2 grid count for {asset_id}: {len(indexes)}")
        buy_and_hold_context[asset_id] = {
            "start_date": asset_rows[0]["observation_date"],
            "end_date": asset_rows[-1]["observation_date"],
            "full_interval_return_pct": pct(prices[-1], prices[0]),
        }

        for grid_position, index in enumerate(indexes):
            role = "REFERENCE_CONTROL" if asset_id == REFERENCE else "TACTICAL_OPPORTUNITY"
            result: dict[str, object] = {
                "asset_id": asset_id,
                "role": role,
                "grid_position": grid_position,
                "decision_date": asset_rows[index]["observation_date"],
            }
            input_values = features(prices, index)
            score, posture = score_candidate(input_values, rule)
            if role == "REFERENCE_CONTROL":
                posture = "REFERENCE_CONTROL"
            else:
                result.update(input_values)
            result["candidate_score"] = score
            result["posture"] = posture
            entry = prices[index]
            for horizon in horizons:
                future = prices[index + 1:index + horizon + 1]
                if len(future) != horizon:
                    raise RuntimeError("incomplete forward window in locked V2 grid")
                result[f"forward_return_{horizon}d_pct"] = pct(prices[index + horizon], entry)
                result[f"mae_{horizon}d_pct"] = min(pct(value, entry) for value in future)
                result[f"mfe_{horizon}d_pct"] = max(pct(value, entry) for value in future)
            rows.append(result)

    if len(rows) != int(authorization["expected_total_grid_points"]):
        raise RuntimeError("V2 total validation grid count changed")
    opportunity_rows = [row for row in rows if row["role"] == "TACTICAL_OPPORTUNITY"]
    reference_rows = [row for row in rows if row["role"] == "REFERENCE_CONTROL"]
    if len(opportunity_rows) != int(authorization["expected_opportunity_grid_points"]):
        raise RuntimeError("V2 opportunity grid count changed")
    if len(reference_rows) != int(authorization["expected_reference_control_grid_points"]):
        raise RuntimeError("V2 reference grid count changed")

    metrics = grouped_metrics(opportunity_rows, horizons)
    behavior = behavior_metrics(opportunity_rows)
    reference_metrics = {f"{h}d": summarize(reference_rows, h) for h in horizons}

    minimum_support = int(design["locked_candidate"]["minimum_compared_group_support"])
    constructive_63 = metrics["CONSTRUCTIVE"]["63d"]
    defensive_63 = metrics["DEFENSIVE"]["63d"]
    support_met = (
        int(constructive_63["observation_count"]) >= minimum_support
        and int(defensive_63["observation_count"]) >= minimum_support
    )

    checks = {
        "constructive_63d_median_return_gt_defensive": False,
        "constructive_63d_positive_return_rate_gt_defensive": False,
        "defensive_63d_mean_mae_more_negative_than_constructive": False,
        "holdout_posture_change_rate_lte_0_50": behavior["posture_change_rate"] <= 0.50,
        "minimum_group_support_met": support_met,
        "no_semantic_or_governance_violation": True,
    }
    if support_met:
        checks["constructive_63d_median_return_gt_defensive"] = float(constructive_63["median_return_pct"]) > float(defensive_63["median_return_pct"])
        checks["constructive_63d_positive_return_rate_gt_defensive"] = float(constructive_63["positive_return_rate"]) > float(defensive_63["positive_return_rate"])
        checks["defensive_63d_mean_mae_more_negative_than_constructive"] = float(defensive_63["mean_maximum_adverse_excursion_pct"]) < float(constructive_63["mean_maximum_adverse_excursion_pct"])

    if not support_met:
        candidate_result = "INCONCLUSIVE"
    elif all(checks.values()):
        candidate_result = "PASS"
    else:
        candidate_result = "FAIL"

    result = {
        "status": "PASS",
        "evaluation_id": authorization["evaluation_id"],
        "candidate_result": candidate_result,
        "package_id": authorization["package_id"],
        "validation_interval_consumed": True,
        "validation_history_sha256": sha256_file(history_path),
        "validation_coverage_sha256": sha256_file(coverage_path),
        "validation_manifest_sha256": sha256_file(manifest_path),
        "total_grid_points": len(rows),
        "opportunity_grid_points": len(opportunity_rows),
        "reference_control_grid_points": len(reference_rows),
        "minimum_compared_group_support": minimum_support,
        "constructive_63d_observation_count": constructive_63["observation_count"],
        "defensive_63d_observation_count": defensive_63["observation_count"],
        "constructive_63d_median_return_pct": constructive_63["median_return_pct"],
        "defensive_63d_median_return_pct": defensive_63["median_return_pct"],
        "constructive_63d_positive_return_rate": constructive_63["positive_return_rate"],
        "defensive_63d_positive_return_rate": defensive_63["positive_return_rate"],
        "constructive_63d_mean_mae_pct": constructive_63["mean_maximum_adverse_excursion_pct"],
        "defensive_63d_mean_mae_pct": defensive_63["mean_maximum_adverse_excursion_pct"],
        "posture_change_rate": behavior["posture_change_rate"],
        "checks": checks,
        "metrics": metrics,
        "behavior": behavior,
        "reference_control_metrics": reference_metrics,
        "buy_and_hold_context": buy_and_hold_context,
        "overlapping_forward_windows_disclosed": True,
        "vehicle_cluster_dependence_disclosed": True,
        "candidate_rules_changed_during_or_after_validation": False,
        "candidate_thresholds_changed_during_or_after_validation": False,
        "tactical_posture_authorized": False,
        "presentation_activation_executed": False,
        "production_database_write_executed": False,
        "native_source_query_executed": False,
        "package_regeneration_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": authorization["next_decision_by_result"][candidate_result],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
    temp_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(output_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
