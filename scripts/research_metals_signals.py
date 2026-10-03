"""Compare candidate Metals signals with an in-sample / out-of-sample split.

Each candidate turns the price history available at month t into a position (hold the
metal or hold T-bills) and a score (higher = more bullish). Settings for each family
are chosen on the in-sample period only (by the equal-weight portfolio's Sharpe), and
the chosen setting is then judged once on the out-of-sample period it never saw.

Shares data loading, cash and metrics with scripts/backtest_metals_native_model.py,
acts with the same one-month lag, and charges a cost on every switch. Read-only.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
from datetime import date
from pathlib import Path
from statistics import mean
from typing import Callable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("backtest_metals_native_model", Path(__file__).with_name("backtest_metals_native_model.py"))
bt = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("backtest_metals_native_model", bt)
_spec.loader.exec_module(bt)

SWITCH_COST = 0.001  # 0.10% each time the position changes
Points = Sequence[tuple[date, float]]
Signal = Callable[[Points], "tuple[bool, float] | None"]


def _trailing(points: Points, months: int) -> float | None:
    if len(points) <= months or points[-1 - months][1] <= 0:
        return None
    return points[-1][1] / points[-1 - months][1] - 1.0


def mean_reversion(months: int) -> Signal:
    """Hold after a decline over the lookback; score is the negative trailing return."""
    def signal(points: Points):
        change = _trailing(points, months)
        return None if change is None else (change < 0.0, -change)
    return signal


def moving_average(months: int) -> Signal:
    """Hold while the price is above its moving average; score is the distance above it."""
    def signal(points: Points):
        if len(points) < months:
            return None
        average = mean(value for _, value in points[-months:])
        gap = points[-1][1] / average - 1.0
        return gap > 0.0, gap
    return signal


def value(years: int) -> Signal:
    """Hold while the price is below its long-run average; score is how far below."""
    def signal(points: Points):
        months = 12 * years
        if len(points) < months:
            return None
        log_average = mean(math.log(v) for _, v in points[-months:])
        gap = math.log(points[-1][1]) - log_average
        return gap < 0.0, -gap
    return signal


def model_signal(model_call: Callable, metal: str, funded: bool) -> Signal:
    def signal(points: Points):
        recommendation, adjusted = model_call(metal, points, funded)
        return recommendation in bt.INVESTED_CALLS, (adjusted if adjusted is not None else 0.0)
    return signal


def evaluate(
    series: Mapping[str, Points],
    signal_for: Callable[[str], Signal],
    cash: Mapping[tuple[int, int], float],
    start: date,
    end: date,
) -> dict:
    per_metal, monthly, scores, forwards = {}, [], [], []
    for metal, points in sorted(series.items()):
        strat, hold, cash_used, previous, invested, switches = [], [], [], None, 0, 0
        signal = signal_for(metal)
        for i in range(12, len(points) - 1 - bt.EXECUTION_LAG_MONTHS):
            as_of = points[i][0]
            if as_of < start or as_of > end:
                continue
            outcome = signal(points[: i + 1])
            if outcome is None:
                continue
            in_metal, score = outcome
            j = i + 1 + bt.EXECUTION_LAG_MONTHS
            metal_return = points[j][1] / points[j - 1][1] - 1.0
            cash_return = cash.get((points[j][0].year, points[j][0].month), 0.0)
            cost = SWITCH_COST if previous is not None and in_metal != previous else 0.0
            switches += cost > 0
            strat.append((metal_return if in_metal else cash_return) - cost)
            hold.append(metal_return)
            cash_used.append(cash_return)
            invested += in_metal
            previous = in_metal
            if i + 12 < len(points):
                scores.append(score)
                forwards.append(points[i + 12][1] / points[i][1] - 1.0)
        if strat:
            per_metal[metal] = {
                "strategy": bt.performance(strat, cash_used),
                "hold": bt.performance(hold, cash_used),
                "share_invested": invested / len(strat),
                "switches": switches,
            }
            monthly.append((strat, hold, cash_used))
    if not monthly:
        return {}
    length = min(len(m[0]) for m in monthly)
    strat = [mean(m[0][-length:][k] for m in monthly) for k in range(length)]
    hold = [mean(m[1][-length:][k] for m in monthly) for k in range(length)]
    cash_used = monthly[0][2][-length:]
    portfolio = {"strategy": bt.performance(strat, cash_used), "hold": bt.performance(hold, cash_used)}
    beats = sum(
        1 for item in per_metal.values()
        if (item["strategy"].get("sharpe") or -9) > (item["hold"].get("sharpe") or -9)
    )
    return {
        "portfolio": portfolio,
        "rank_correlation": bt.spearman(scores, forwards),
        "metals_beating_hold_sharpe": beats,
        "metals": len(per_metal),
        "per_metal": per_metal,
    }


def families(model_call: Callable | None, funded: set[str]) -> dict[str, list[tuple[str, Callable[[str], Signal]]]]:
    grid = {
        "mean_reversion": [(f"{m}m", (lambda m: lambda metal: mean_reversion(m))(m)) for m in (12, 24, 36, 60)],
        "moving_average": [(f"{m}m", (lambda m: lambda metal: moving_average(m))(m)) for m in (6, 8, 10, 12)],
        "value": [(f"{y}y", (lambda y: lambda metal: value(y))(y)) for y in (5, 10)],
    }
    if model_call is not None:
        grid["current_model"] = [("production", lambda metal: model_signal(model_call, metal, metal in funded))]
    return grid


def _sharpe(result: dict) -> float:
    value_ = ((result.get("portfolio") or {}).get("strategy") or {}).get("sharpe")
    return -9.0 if value_ is None else value_


def research(series, model_call, funded, cash, in_sample: tuple[date, date], out_sample: tuple[date, date]) -> dict:
    report = {"in_sample": [d.isoformat() for d in in_sample], "out_of_sample": [d.isoformat() for d in out_sample],
              "switch_cost": SWITCH_COST, "families": {}}
    for family, settings in families(model_call, funded).items():
        tried = {name: evaluate(series, make, cash, *in_sample) for name, make in settings}
        chosen = max(tried, key=lambda name: _sharpe(tried[name]))
        make = dict(settings)[chosen]
        report["families"][family] = {
            "in_sample_by_setting": {name: _summary(result) for name, result in tried.items()},
            "chosen_setting": chosen,
            "out_of_sample": evaluate(series, make, cash, *out_sample),
        }
    return report


def _summary(result: dict) -> dict:
    if not result:
        return {}
    return {
        "portfolio": result["portfolio"],
        "rank_correlation": result["rank_correlation"],
        "metals_beating_hold_sharpe": result["metals_beating_hold_sharpe"],
        "metals": result["metals"],
    }


def _pct(x):
    return "n/a" if x is None else f"{x * 100:.1f}%"


def _num(x):
    return "n/a" if x is None else f"{x:.2f}"


def render(report: dict) -> str:
    lines = [
        "# Metals signal research",
        "",
        f"Settings chosen on {report['in_sample'][0]} to {report['in_sample'][1]} only; judged once on "
        f"{report['out_of_sample'][0]} to {report['out_of_sample'][1]}. Hold the metal when the rule says so, "
        f"otherwise T-bills; one-month lag; {report['switch_cost'] * 100:.2f}% cost per switch; equal-weight across metals.",
        "",
        "## Out-of-sample (never used to choose settings)",
        "",
        "| Rule | Setting | Annual return | Hold: annual return | Max drawdown | Hold: max drawdown | Sharpe | Hold Sharpe | Rank correlation | Metals beating hold |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for family, item in report["families"].items():
        oos = item["out_of_sample"]
        if not oos:
            continue
        s, h = oos["portfolio"]["strategy"], oos["portfolio"]["hold"]
        lines.append(
            f"| {family} | {item['chosen_setting']} | {_pct(s.get('annual_return'))} | {_pct(h.get('annual_return'))} | "
            f"{_pct(s.get('max_drawdown'))} | {_pct(h.get('max_drawdown'))} | {_num(s.get('sharpe'))} | {_num(h.get('sharpe'))} | "
            f"{_num(oos['rank_correlation'])} | {oos['metals_beating_hold_sharpe']}/{oos['metals']} |"
        )
    lines += ["", "## In-sample, every setting tried", "", "| Rule | Setting | Sharpe | Hold Sharpe | Rank correlation |", "|---|---|---|---|---|"]
    for family, item in report["families"].items():
        for name, result in item["in_sample_by_setting"].items():
            if not result:
                continue
            lines.append(
                f"| {family} | {name}{' (chosen)' if name == item['chosen_setting'] else ''} | "
                f"{_num(result['portfolio']['strategy'].get('sharpe'))} | {_num(result['portfolio']['hold'].get('sharpe'))} | "
                f"{_num(result['rank_correlation'])} |"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None, model_call: Callable | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--methodology", type=Path, default=ROOT / "config" / "metals" / "model_methodology_registry.json")
    parser.add_argument("--vehicle-registry", type=Path, default=ROOT / "config" / "metals" / "vehicles.json")
    parser.add_argument("--in-sample-start", type=date.fromisoformat, default=date(1980, 1, 1))
    parser.add_argument("--split", type=date.fromisoformat, default=date(2006, 1, 1))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "operations" / "metals" / "signal_research")
    parser.add_argument("--skip-current-model", action="store_true")
    args = parser.parse_args(argv)

    series = {m: p for m, p in bt.load_history(args.history).items() if bt.is_monthly(p)}
    funded = bt.funded_metals(args.vehicle_registry)
    if model_call is None and not args.skip_current_model:
        model_call = bt.real_model_call(json.loads(args.methodology.read_text(encoding="utf-8-sig")))
    cash, cash_source = bt.fetch_cash(os.environ.get("UIIP_FRED_API_KEY"), args.in_sample_start)
    last = max(points[-1][0] for points in series.values())
    in_sample = (args.in_sample_start, date(args.split.year - 1, 12, 31))
    report = research(series, model_call, funded, cash, in_sample, (args.split, last))
    report["cash_source"] = cash_source
    report["metals"] = sorted(series)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "signal_research.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    markdown = render(report)
    (args.output_dir / "signal_research.md").write_text(markdown, encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
