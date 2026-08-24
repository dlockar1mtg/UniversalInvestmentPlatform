from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONTRACT_PATH = ROOT / "config" / "metals" / "tactical_policy_historical_input_feasibility_audit.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            text = raw.strip()
            if not text:
                raise RuntimeError(f"blank JSONL row in {path.name} at line {line_number}")
            value = json.loads(text)
            if not isinstance(value, dict):
                raise RuntimeError(f"non-object JSONL row in {path.name} at line {line_number}")
            rows.append(value)
    return rows


def effective_price(row: dict[str, object]) -> float:
    adjusted = row.get("adjusted_close_usd")
    raw = row.get("close_usd")
    value = adjusted if adjusted is not None else raw
    if value is None:
        raise RuntimeError("history row is missing both adjusted and raw close")
    price = float(value)
    if not math.isfinite(price) or price <= 0:
        raise RuntimeError("history row contains invalid effective price")
    return price


def pct_change(current: float, prior: float) -> float:
    return (current / prior - 1.0) * 100.0


def point_in_time_features(prices: list[float], index: int) -> dict[str, float]:
    if index < 251:
        raise RuntimeError("feature calculation attempted before 252-observation warmup")
    current = prices[index]
    ma50 = statistics.fmean(prices[index - 49:index + 1])
    ma200 = statistics.fmean(prices[index - 199:index + 1])
    trailing_252 = prices[index - 251:index + 1]
    trailing_64 = prices[index - 63:index + 1]
    daily_returns = [trailing_64[i] / trailing_64[i - 1] - 1.0 for i in range(1, len(trailing_64))]
    features = {
        "return_1m_pct": pct_change(current, prices[index - 21]),
        "return_3m_pct": pct_change(current, prices[index - 63]),
        "return_6m_pct": pct_change(current, prices[index - 126]),
        "distance_ma50_pct": pct_change(current, ma50),
        "distance_ma200_pct": pct_change(current, ma200),
        "current_drawdown_pct": pct_change(current, max(trailing_252)),
        "realized_volatility_3m_pct": statistics.stdev(daily_returns) * math.sqrt(252.0) * 100.0,
    }
    if any(not math.isfinite(float(value)) for value in features.values()):
        raise RuntimeError("non-finite point-in-time feature calculated")
    return features


def main() -> int:
    args = parse_args()
    package_dir = Path(args.package_dir).resolve()
    history_path = package_dir / "metals_price_history.jsonl"
    manifest_path = package_dir / "manifest.json"
    if not history_path.is_file() or not manifest_path.is_file():
        raise RuntimeError("certified Metals price/history package is incomplete")

    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("audit_id") != "METALS-TACTICAL-POLICY-HISTORICAL-INPUT-FEASIBILITY-AUDIT-1":
        raise RuntimeError("unexpected historical-input feasibility audit contract")
    controls = contract.get("controls") or {}
    if controls.get("historical_input_feasibility_audit_authorized") is not True:
        raise RuntimeError("historical-input feasibility audit is not authorized")
    for key in (
        "historical_candidate_evaluation_authorized",
        "tactical_posture_authorized",
        "presentation_activation_authorized",
        "production_database_write_authorized",
        "native_source_query_authorized",
        "export_execution_authorized",
        "forecast_refresh_authorized",
        "model_retraining_authorized",
        "cross_domain_rank_authorized",
        "allocation_policy_authorized",
        "automatic_execution_authorized",
    ):
        if controls.get(key) is not False:
            raise RuntimeError(f"prohibited audit control changed unexpectedly: {key}")

    if sha256_file(history_path) != str(contract["expected_history_sha256"]):
        raise RuntimeError("certified history artifact SHA-256 mismatch")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("package_id") != contract["source_package_id"]:
        raise RuntimeError("unexpected source package ID")
    if manifest.get("source_authority") != contract["source_authority"]:
        raise RuntimeError("unexpected source authority")

    rows = load_jsonl(history_path)
    by_asset: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        asset_id = str(row.get("asset_id", ""))
        by_asset.setdefault(asset_id, []).append(row)

    expected_assets = list(contract["eligible_vehicle_asset_ids"]) + list(contract["reference_control_asset_ids"])
    if sorted(by_asset) != sorted(expected_assets):
        raise RuntimeError("history package asset population does not match governed audit universe")

    minimum_history = int(contract["minimum_history_observations"])
    expected_history_count = int(contract["expected_history_observations_per_asset"])
    expected_input_ready = int(contract["expected_input_ready_observations_per_asset"])
    expected_grid = int(contract["expected_forward_evaluable_grid_points_per_asset"])
    step = int(contract["walk_forward_step_observations"])
    max_forward = max(int(value) for value in contract["forward_horizons_observations"])
    required_inputs = tuple(str(value) for value in contract["required_price_derived_inputs"])

    coverage: list[dict[str, object]] = []
    total_input_ready = 0
    total_forward_grid = 0

    for asset_id in sorted(expected_assets):
        asset_rows = sorted(by_asset[asset_id], key=lambda row: str(row["observation_date"]))
        dates = [str(row["observation_date"]) for row in asset_rows]
        if len(dates) != len(set(dates)):
            raise RuntimeError(f"duplicate observation dates for {asset_id}")
        if len(asset_rows) != expected_history_count:
            raise RuntimeError(f"unexpected history count for {asset_id}: {len(asset_rows)}")
        prices = [effective_price(row) for row in asset_rows]

        input_ready_count = 0
        first_input_ready_date = None
        last_input_ready_date = None
        for index in range(minimum_history - 1, len(prices)):
            features = point_in_time_features(prices, index)
            if tuple(features.keys()) != required_inputs:
                raise RuntimeError(f"feature vocabulary mismatch for {asset_id}")
            input_ready_count += 1
            if first_input_ready_date is None:
                first_input_ready_date = dates[index]
            last_input_ready_date = dates[index]

        if input_ready_count != expected_input_ready:
            raise RuntimeError(f"unexpected input-ready observation count for {asset_id}: {input_ready_count}")

        grid_indexes = list(range(minimum_history - 1, len(prices) - max_forward, step))
        if len(grid_indexes) != expected_grid:
            raise RuntimeError(f"unexpected forward-evaluable grid count for {asset_id}: {len(grid_indexes)}")

        total_input_ready += input_ready_count
        total_forward_grid += len(grid_indexes)
        coverage.append({
            "asset_id": asset_id,
            "role": "REFERENCE_CONTROL" if asset_id in contract["reference_control_asset_ids"] else "TACTICAL_OPPORTUNITY",
            "history_count": len(asset_rows),
            "min_date": dates[0],
            "max_date": dates[-1],
            "input_ready_observation_count": input_ready_count,
            "first_input_ready_date": first_input_ready_date,
            "last_input_ready_date": last_input_ready_date,
            "forward_evaluable_grid_point_count": len(grid_indexes),
            "first_forward_evaluable_date": dates[grid_indexes[0]],
            "last_forward_evaluable_date": dates[grid_indexes[-1]],
        })

    eligible_count = len(contract["eligible_vehicle_asset_ids"])
    reference_count = len(contract["reference_control_asset_ids"])
    result = {
        "status": "PASS",
        "read_only": True,
        "audit_id": contract["audit_id"],
        "source_candidate_rule_design": contract["source_candidate_rule_design"],
        "source_package_id": contract["source_package_id"],
        "source_authority": contract["source_authority"],
        "eligible_vehicle_count": eligible_count,
        "reference_control_count": reference_count,
        "historical_input_count": len(required_inputs),
        "minimum_history_observations": minimum_history,
        "walk_forward_step_observations": step,
        "forward_horizons_observations": contract["forward_horizons_observations"],
        "history_observations_per_asset": expected_history_count,
        "input_ready_observations_per_asset": expected_input_ready,
        "forward_evaluable_grid_points_per_asset": expected_grid,
        "total_input_ready_observations": total_input_ready,
        "total_forward_evaluable_grid_points": total_forward_grid,
        "point_in_time_inputs_verified": True,
        "future_values_used_in_feature_calculation": False,
        "forward_outcomes_calculated": False,
        "current_only_evidence_backfill_executed": False,
        "coverage": coverage,
        "historical_candidate_evaluation_authorized": False,
        "tactical_posture_authorized": False,
        "production_database_write_executed": False,
        "native_source_query_executed": False,
        "export_execution_executed": False,
        "forecast_refresh_executed": False,
        "model_retraining_executed": False,
        "cross_domain_rank_authorized": False,
        "allocation_policy_authorized": False,
        "automatic_execution_authorized": False,
        "next_decision": contract["next_decision"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
