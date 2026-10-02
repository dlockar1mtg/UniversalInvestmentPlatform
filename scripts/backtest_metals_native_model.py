"""Walk-forward backtest of the UIP-native Metals model.

At each month the real production model (evaluate_native_cycle) is run on only the
history available at that date, and its 12-month call is judged two ways:

* forecast skill: do higher calls precede higher 12-month returns?
* a simple strategy: hold the metal while the call is BUY or STRONG_BUY, otherwise
  cash (3-month T-bills), versus holding the metal throughout.

World Bank prices are monthly averages, which makes consecutive monthly returns
artificially correlated and flatters momentum. The strategy therefore acts with a
one-month lag: the call made from month t's data earns month t+2's return.
Nothing here touches PostgreSQL or the published dashboard.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from statistics import mean, pstdev
from typing import Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

INVESTED_CALLS = ("BUY", "STRONG_BUY")
CALL_ORDER = ("STRONG_BUY", "BUY", "HOLD", "REDUCE", "AVOID")
EXECUTION_LAG_MONTHS = 1
MAXIMUM_MONTHLY_GAP_DAYS = 45


@dataclass(frozen=True)
class Call:
    metal: str
    as_of: date
    recommendation: str
    adjusted_return: float | None
    forward_12m_return: float | None


def _key(asset_id: str) -> str:
    return str(asset_id).split(":")[-1].upper()


def load_history(path: Path) -> dict[str, list[tuple[date, float]]]:
    series: dict[str, dict[date, float]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            try:
                value = float(row["value"])
                day = date.fromisoformat(str(row["observation_date"])[:10])
            except (KeyError, TypeError, ValueError):
                continue
            if value > 0:
                series.setdefault(_key(row["asset_id"]), {})[day] = value
    return {metal: sorted(points.items()) for metal, points in series.items()}


def is_monthly(points: Sequence[tuple[date, float]]) -> bool:
    if len(points) < 24:
        return False
    gaps = sorted((b[0] - a[0]).days for a, b in zip(points, points[1:]))
    return gaps[len(gaps) // 2] <= MAXIMUM_MONTHLY_GAP_DAYS


def funded_metals(registry_path: Path) -> set[str]:
    registry = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    return {
        _key(row["underlying_asset_id"])
        for row in registry.get("vehicles", [])
        if row.get("enabled", True) and row.get("role") != "reserve"
    }


def real_model_call(methodology: Mapping[str, object]) -> Callable:
    """Wrap the production model: (metal, points up to t, funded) -> (call, adjusted return)."""
    from foundation.production.metals_native_cycle import NativeObservation, evaluate_native_cycle

    def call(metal: str, points: Sequence[tuple[date, float]], funded: bool) -> tuple[str, float | None]:
        asset_id = f"METALS:COMMODITY:{metal}"
        rows = [NativeObservation(asset_id, day.isoformat(), value, "backtest") for day, value in points]
        # Funds track their metal, so before funds existed the metal's own series stands in
        # for the fund confirmation term the live model uses.
        proxy = f"PROXY_{metal}"
        vehicles = [NativeObservation(proxy, day.isoformat(), value, "backtest") for day, value in points] if funded else []
        report = evaluate_native_cycle(
            rows, vehicles, methodology, vehicle_underlying={proxy: asset_id} if funded else {}
        )
        for forecast in report.forecasts:
            if _key(forecast.asset_id) == metal and int(forecast.horizon_months) == 12:
                components = json.loads(forecast.component_json or "{}")
                adjusted = components.get("confidence_adjusted_return")
                if adjusted is None:
                    adjusted = float(forecast.annualized_return) * float(forecast.confidence)
                return str(forecast.recommendation), float(adjusted)
        return "HOLD", None

    return call


def walk_forward(
    series: Mapping[str, Sequence[tuple[date, float]]],
    model_call: Callable,
    funded: set[str],
    start: date,
) -> list[Call]:
    calls: list[Call] = []
    for metal, points in sorted(series.items()):
        for index in range(12, len(points)):
            as_of, value = points[index]
            if as_of < start:
                continue
            recommendation, adjusted = model_call(metal, points[: index + 1], metal in funded)
            forward = points[index + 12][1] / value - 1.0 if index + 12 < len(points) else None
            calls.append(Call(metal, as_of, recommendation, adjusted, forward))
    return calls


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2.0 + 1.0
        i = j + 1
    return ranks


def spearman(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    if len(xs) < 3:
        return None
    rx, ry = _ranks(xs), _ranks(ys)
    mx, my = mean(rx), mean(ry)
    sx = math.sqrt(sum((r - mx) ** 2 for r in rx))
    sy = math.sqrt(sum((r - my) ** 2 for r in ry))
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sx * sy)


def calibration(calls: Sequence[Call]) -> dict:
    judged = [c for c in calls if c.forward_12m_return is not None]
    buckets = {}
    for name in CALL_ORDER:
        rows = [c.forward_12m_return for c in judged if c.recommendation == name]
        if rows:
            buckets[name] = {
                "months": len(rows),
                "average_next_12m_return": mean(rows),
                "share_positive": sum(1 for r in rows if r > 0) / len(rows),
            }
    scored = [c for c in judged if c.adjusted_return is not None]
    return {
        "judged_calls": len(judged),
        "by_call": buckets,
        "rank_correlation": spearman([c.adjusted_return for c in scored], [c.forward_12m_return for c in scored]),
    }


def performance(returns: Sequence[float], cash: Sequence[float]) -> dict:
    if not returns:
        return {}
    wealth, peak, drawdown = 1.0, 1.0, 0.0
    for r in returns:
        wealth *= 1.0 + r
        peak = max(peak, wealth)
        drawdown = min(drawdown, wealth / peak - 1.0)
    years = len(returns) / 12.0
    volatility = pstdev(returns) * math.sqrt(12) if len(returns) > 1 else 0.0
    excess = [r - c for r, c in zip(returns, cash)]
    sharpe = (mean(excess) * 12) / volatility if volatility > 0 else None
    return {
        "months": len(returns),
        "annual_return": wealth ** (1.0 / years) - 1.0,
        "annual_volatility": volatility,
        "max_drawdown": drawdown,
        "sharpe": sharpe,
    }


def strategy(
    calls: Sequence[Call],
    points: Sequence[tuple[date, float]],
    cash_monthly: Mapping[tuple[int, int], float],
) -> dict:
    by_date = {c.as_of: c for c in calls}
    index_of = {day: i for i, (day, _) in enumerate(points)}
    strat, hold, cash_used, invested = [], [], [], 0
    for day, call in sorted(by_date.items()):
        i = index_of[day]
        j = i + 1 + EXECUTION_LAG_MONTHS
        if j >= len(points):
            continue
        metal_return = points[j][1] / points[j - 1][1] - 1.0
        cash = cash_monthly.get((points[j][0].year, points[j][0].month), 0.0)
        in_metal = call.recommendation in INVESTED_CALLS
        invested += in_metal
        strat.append(metal_return if in_metal else cash)
        hold.append(metal_return)
        cash_used.append(cash)
    switches = sum(
        1 for a, b in zip(sorted(by_date.values(), key=lambda c: c.as_of), sorted(by_date.values(), key=lambda c: c.as_of)[1:])
        if (a.recommendation in INVESTED_CALLS) != (b.recommendation in INVESTED_CALLS)
    )
    return {
        "model_strategy": performance(strat, cash_used),
        "buy_and_hold": performance(hold, cash_used),
        "share_of_months_invested": invested / len(strat) if strat else None,
        "switches": switches,
        "_monthly": {"strategy": strat, "hold": hold, "cash": cash_used},
    }


def portfolio(results: Mapping[str, dict]) -> dict:
    monthly = [r["_monthly"] for r in results.values() if r.get("_monthly", {}).get("strategy")]
    if not monthly:
        return {}
    length = min(len(m["strategy"]) for m in monthly)
    def tail(m, key):
        return m[key][-length:]
    strat = [mean(tail(m, "strategy")[k] for m in monthly) for k in range(length)]
    hold = [mean(tail(m, "hold")[k] for m in monthly) for k in range(length)]
    cash = tail(monthly[0], "cash")
    return {"metals": len(monthly), "model_strategy": performance(strat, cash), "buy_and_hold": performance(hold, cash)}


def fetch_cash(api_key: str | None, start: date) -> tuple[dict[tuple[int, int], float], str]:
    """Monthly T-bill return from FRED TB3MS (annual %), or zero cash if unavailable."""
    if not api_key:
        return {}, "ZERO (no FRED key)"
    url = (
        "https://api.stlouisfed.org/fred/series/observations?series_id=TB3MS&file_type=json"
        f"&observation_start={start.isoformat()}&api_key={api_key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - report and fall back
        return {}, f"ZERO (FRED unavailable: {type(exc).__name__})"
    cash = {}
    for item in payload.get("observations", []):
        try:
            day = date.fromisoformat(item["date"])
            cash[(day.year, day.month)] = float(item["value"]) / 100.0 / 12.0
        except (KeyError, ValueError):
            continue
    return cash, "FRED TB3MS (3-month T-bill)"


def _pct(value):
    return "n/a" if value is None else f"{value * 100:.1f}%"


def render_markdown(report: dict) -> str:
    lines = [
        "# Metals model backtest",
        "",
        f"Walk-forward from {report['start']} to {report['end']}; model methodology {report['methodology_version']}; "
        f"cash: {report['cash_source']}. The strategy holds a metal while the 12-month call is BUY/STRONG_BUY "
        f"(otherwise cash) and acts with a {EXECUTION_LAG_MONTHS}-month lag.",
        "",
        "## Strategy vs buy-and-hold",
        "",
        "| Metal | Model: annual return | Hold: annual return | Model: max drawdown | Hold: max drawdown | Model Sharpe | Hold Sharpe | Time invested | Switches |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    rows = list(report["by_metal"].items())
    if report.get("portfolio"):
        rows.append(("Equal-weight portfolio", report["portfolio"]))
    for metal, item in rows:
        m, h = item.get("model_strategy") or {}, item.get("buy_and_hold") or {}
        if not m:
            continue
        sharpe = lambda d: "n/a" if d.get("sharpe") is None else f"{d['sharpe']:.2f}"
        lines.append(
            f"| {metal} | {_pct(m.get('annual_return'))} | {_pct(h.get('annual_return'))} | "
            f"{_pct(m.get('max_drawdown'))} | {_pct(h.get('max_drawdown'))} | {sharpe(m)} | {sharpe(h)} | "
            f"{_pct(item.get('share_of_months_invested'))} | {item.get('switches', '')} |"
        )
    lines += ["", "## Do higher calls precede higher returns? (all metals pooled)", "",
              "| Call | Months | Average next-12-month return | Share positive |", "|---|---|---|---|"]
    for name, bucket in report["calibration"]["by_call"].items():
        lines.append(f"| {name} | {bucket['months']} | {_pct(bucket['average_next_12m_return'])} | {_pct(bucket['share_positive'])} |")
    rc = report["calibration"]["rank_correlation"]
    lines += ["", f"Rank correlation between the model's adjusted return and the next 12 months: "
              f"{'n/a' if rc is None else f'{rc:.3f}'} (0 = no skill).", ""]
    if report.get("calls_only"):
        lines.append("Calibration only (not monthly data, no strategy): " + ", ".join(report["calls_only"]))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, model_call: Callable | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--methodology", type=Path, default=ROOT / "config" / "metals" / "model_methodology_registry.json")
    parser.add_argument("--vehicle-registry", type=Path, default=ROOT / "config" / "metals" / "vehicles.json")
    parser.add_argument("--start", type=date.fromisoformat, default=date(2006, 1, 1))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "operations" / "metals" / "backtest")
    args = parser.parse_args(argv)

    methodology = json.loads(args.methodology.read_text(encoding="utf-8-sig"))
    series = load_history(args.history)
    funded = funded_metals(args.vehicle_registry)
    model_call = model_call or real_model_call(methodology)
    cash, cash_source = fetch_cash(os.environ.get("UIIP_FRED_API_KEY"), args.start)

    calls = walk_forward(series, model_call, funded, args.start)
    by_metal, calls_only = {}, []
    for metal, points in sorted(series.items()):
        metal_calls = [c for c in calls if c.metal == metal]
        if not metal_calls:
            continue
        if is_monthly(points):
            by_metal[metal] = strategy(metal_calls, points, cash)
            by_metal[metal]["calibration"] = calibration(metal_calls)
        else:
            calls_only.append(metal)
    report = {
        "start": args.start.isoformat(),
        "end": max(c.as_of for c in calls).isoformat() if calls else None,
        "methodology_version": (methodology.get("models") or [{}])[0].get("methodology_version")
        or methodology.get("methodology_version"),
        "cash_source": cash_source,
        "execution_lag_months": EXECUTION_LAG_MONTHS,
        "by_metal": by_metal,
        "portfolio": portfolio(by_metal),
        "calibration": calibration(calls),
        "calls_only": calls_only,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    clean = json.loads(json.dumps(report, default=str))
    for item in clean["by_metal"].values():
        item.pop("_monthly", None)
    (args.output_dir / "backtest.json").write_text(json.dumps(clean, indent=2) + "\n", encoding="utf-8")
    with (args.output_dir / "calls.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metal", "as_of", "recommendation", "adjusted_return", "forward_12m_return"])
        for c in calls:
            writer.writerow([c.metal, c.as_of.isoformat(), c.recommendation, c.adjusted_return, c.forward_12m_return])
    markdown = render_markdown(report)
    (args.output_dir / "backtest.md").write_text(markdown, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
