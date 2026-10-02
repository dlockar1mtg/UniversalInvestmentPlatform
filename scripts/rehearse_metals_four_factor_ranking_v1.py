from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

_VEHICLE_REGISTRY_PATH = Path(__file__).resolve().parents[1] / "config" / "metals" / "vehicles.json"


def _registered_tickers() -> tuple[str, ...]:
    """Enabled, non-reserve Metals implementation vehicles, in registry order."""
    registry = json.loads(_VEHICLE_REGISTRY_PATH.read_text(encoding="utf-8-sig"))
    return tuple(
        str(row["ticker"]).upper()
        for row in registry.get("vehicles", [])
        if row.get("enabled", True) and row.get("role") != "reserve"
    )


EXPECTED = set(_registered_tickers())


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _positive(value, label: str, ticker: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid {label} for {ticker}") from exc
    if number <= 0:
        raise RuntimeError(f"Nonpositive {label} for {ticker}")
    return number


def _risk_rows(path: str) -> dict[str, dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    mapped = {str(row.get("ticker", "")).upper(): row for row in rows}
    if not EXPECTED <= set(mapped):
        raise RuntimeError(f"Risk evidence missing tickers: {sorted(EXPECTED - set(mapped))}")
    return mapped


def _tie_key(row: dict) -> tuple:
    return (
        -row["total_score"],
        -row["exposure_fidelity_score"],
        row["bid_ask_spread_bps"],
        row["expense_ratio_pct"],
        row["maximum_drawdown_magnitude"],
        row["ticker"],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", default="config/metals/vehicles.json")
    parser.add_argument("--ranking-config", default="config/presentation/metals_vehicle_ranking_v1.json")
    parser.add_argument("--cost", default="config/presentation/metals_vehicle_cost_evidence_snapshot_v1.json")
    parser.add_argument("--spread", default="config/presentation/metals_vehicle_spread_evidence_v1.json")
    parser.add_argument("--adv", required=True)
    parser.add_argument("--risk", required=True)
    parser.add_argument("--output", default="data/operations/metals/vehicle_ranking_v1/rehearsal.json")
    args = parser.parse_args()

    registry = _load_json(args.registry)
    config = _load_json(args.ranking_config)
    cost = _load_json(args.cost)
    spread = _load_json(args.spread)
    adv = _load_json(args.adv)
    risk = _risk_rows(args.risk)

    if config.get("authority_id") != "UIP_NATIVE_METALS_VEHICLE_RANKING_V1" or config.get("methodology_version") != "1.3.0":
        raise RuntimeError("Unexpected ranking authority or methodology version")
    if abs(sum(config["weights"].values()) - 1.0) > 1e-12:
        raise RuntimeError("Ranking weights do not sum to one")
    if cost.get("ranking_authority") is not False:
        raise RuntimeError("Cost snapshot must remain non-ranking authority")
    if spread.get("spread_evidence_certified") is not True:
        raise RuntimeError("Spread evidence is not certified")
    if adv.get("adv_evidence_complete") is not True:
        raise RuntimeError("ADV evidence is incomplete")

    vehicles = [row for row in registry["vehicles"] if row.get("enabled") and row.get("role") != "reserve"]
    if {row["ticker"] for row in vehicles} != EXPECTED:
        raise RuntimeError("Registry implementation universe does not match registered ticker set")

    cost_map = {row["ticker"]: row for row in cost["vehicles"]}
    spread_map = spread["vehicles"]
    adv_map = {row["ticker"]: row for row in adv["vehicles"]}
    if set(cost_map) != EXPECTED or set(spread_map) != EXPECTED or set(adv_map) != EXPECTED:
        raise RuntimeError("Required evidence does not cover registered ticker set")

    groups: dict[str, list[dict]] = defaultdict(list)
    for vehicle in vehicles:
        groups[vehicle["underlying_asset_id"]].append(vehicle)

    results = []
    for commodity_id in sorted(groups):
        members = sorted(groups[commodity_id], key=lambda row: row["ticker"])
        raw = []
        for vehicle in members:
            ticker = vehicle["ticker"]
            expense = _positive(cost_map[ticker].get("expense_ratio_pct"), "expense ratio", ticker)
            adv_value = _positive(adv_map[ticker].get("average_dollar_volume_usd"), "average dollar volume", ticker)
            spread_value = _positive(spread_map[ticker].get("median_bid_ask_spread_bps"), "bid/ask spread", ticker)
            rr = risk[ticker]
            volatility = _positive(rr.get("volatility"), "volatility", ticker)
            downside = _positive(rr.get("downside_volatility"), "downside volatility", ticker)
            drawdown = _positive(abs(float(rr.get("maximum_drawdown"))), "maximum drawdown magnitude", ticker)
            var = _positive(rr.get("value_at_risk"), "value at risk", ticker)
            exposure = config["exposure_fidelity_class_scores"].get(vehicle["vehicle_type"])
            exposure_score = _positive(exposure, "exposure fidelity score", ticker)
            raw.append({
                "ticker": ticker,
                "vehicle_id": vehicle["vehicle_id"],
                "vehicle_type": vehicle["vehicle_type"],
                "exposure_fidelity_score": exposure_score,
                "expense_ratio_pct": expense,
                "average_dollar_volume_usd": adv_value,
                "bid_ask_spread_bps": spread_value,
                "volatility": volatility,
                "downside_volatility": downside,
                "maximum_drawdown_magnitude": drawdown,
                "value_at_risk": var,
            })

        if len(raw) == 1:
            results.append({
                "commodity_id": commodity_id,
                "state": "ONLY_REGISTERED_IMPLEMENTATION",
                "rehearsal_leader": None,
                "vehicles": raw,
            })
            continue

        min_cost = min(row["expense_ratio_pct"] for row in raw)
        max_adv = max(row["average_dollar_volume_usd"] for row in raw)
        min_spread = min(row["bid_ask_spread_bps"] for row in raw)
        risk_fields = ["volatility", "downside_volatility", "maximum_drawdown_magnitude", "value_at_risk"]
        risk_mins = {field: min(row[field] for row in raw) for field in risk_fields}

        weights = config["weights"]
        floor = config["liquidity_floor"]
        holding_months = float(config["holding_period_months"])
        # Cost of ownership (% per year): the fee plus the bid/ask spread paid once per
        # holding period, annualised over the assumed hold.
        for row in raw:
            row["cost_of_ownership_pct"] = row["expense_ratio_pct"] + (row["bid_ask_spread_bps"] / 100.0) * (
                12.0 / holding_months
            )
        min_ownership_cost = min(row["cost_of_ownership_pct"] for row in raw)

        scored = []
        for row in raw:
            cost_score = 100.0 * min_ownership_cost / row["cost_of_ownership_pct"]
            adv_score = 100.0 * row["average_dollar_volume_usd"] / max_adv
            spread_score = 100.0 * min_spread / row["bid_ask_spread_bps"]
            liquidity_score = 0.5 * adv_score + 0.5 * spread_score
            # Liquidity is a minimum bar for a months-long holder, not a scored advantage.
            floor_passed = (
                row["average_dollar_volume_usd"] >= float(floor["minimum_average_dollar_volume_usd"])
                and row["bid_ask_spread_bps"] <= float(floor["maximum_bid_ask_spread_bps"])
            )
            risk_subscores = {field: 100.0 * risk_mins[field] / row[field] for field in risk_fields}
            risk_score = sum(risk_subscores.values()) / 4.0
            total = (
                float(weights["exposure_fidelity"]) * row["exposure_fidelity_score"]
                + float(weights["cost_efficiency"]) * cost_score
                + float(weights["liquidity_implementation_friction"]) * liquidity_score
                + float(weights["risk_efficiency"]) * risk_score
            )
            scored.append({
                **row,
                "cost_efficiency_score": cost_score,
                "adv_score": adv_score,
                "spread_score": spread_score,
                "liquidity_implementation_friction_score": liquidity_score,
                "liquidity_floor_passed": floor_passed,
                "risk_subscores": risk_subscores,
                "risk_efficiency_score": risk_score,
                "total_score": total,
            })

        # Vehicles below the liquidity floor rank after every vehicle that clears it.
        ordered = sorted(scored, key=lambda row: (not row["liquidity_floor_passed"], *_tie_key(row)))
        results.append({
            "commodity_id": commodity_id,
            "state": "READ_ONLY_REHEARSAL_ORDERING_COMPLETE",
            "rehearsal_leader": ordered[0]["ticker"],
            "tie_break_order": config["tie_break_order"],
            "vehicles": ordered,
        })

    evidence = {
        "status": "METALS_FOUR_FACTOR_RANKING_V1_REHEARSAL_PASS",
        "authority_id": config["authority_id"],
        "methodology_version": config["methodology_version"],
        "registered_vehicle_count": len(EXPECTED),
        "commodity_group_count": len(results),
        "weights": config["weights"],
        "groups": results,
        "ranking_rehearsal_complete": True,
        "preferred_vehicle_labels_authorized": False,
        "publication_write_performed": False,
        "production_state_modified": False,
        "allocation_created": False,
        "position_sizing_created": False,
        "automatic_execution_authorized": False,
        "central_publication_cron_restored": False,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
