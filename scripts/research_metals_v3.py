"""Metals model v3 research: value and trend, calibrated to expected 12-month returns.

Each month, for each metal (month-end World Bank prices, using only data up to that month):
  value = log(price) - mean(log price over the last 120 months)   (above/below 10-year average)
  trend = log(price) - log(mean price over the last 12 months)     (above/below 12-month average)
One pooled linear model maps (value, trend) to the next 12 months' return. It is fitted on
the in-sample period only and judged once on the out-of-sample period: ranking skill,
calibration, outcomes by call, and a hold-on-BUY strategy versus holding, with a one-month
lag (monthly-average prices) and a cost on every switch. Read-only.
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

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("backtest_metals_native_model", Path(__file__).with_name("backtest_metals_native_model.py"))
bt = importlib.util.module_from_spec(_spec)
sys.modules.setdefault("backtest_metals_native_model", bt)
_spec.loader.exec_module(bt)

VALUE_MONTHS = 120
TREND_MONTHS = 12
SWITCH_COST = 0.001
CALL_THRESHOLDS = (("STRONG_BUY", 0.12), ("BUY", 0.05), ("HOLD", -0.05), ("REDUCE", -0.12))
INVESTED = ("STRONG_BUY", "BUY")


def call_for(expected: float) -> str:
    for name, floor in CALL_THRESHOLDS:
        if expected >= floor:
            return name
    return "AVOID"


def features(points, i):
    if i + 1 < VALUE_MONTHS:
        return None
    logs = [math.log(v) for _, v in points[i + 1 - VALUE_MONTHS : i + 1]]
    current = logs[-1]
    value = current - mean(logs)
    trend = current - math.log(mean(v for _, v in points[i + 1 - TREND_MONTHS : i + 1]))
    return value, trend


def observations(series):
    """(metal, index, date, value, trend, forward 12-month return or None)."""
    rows = []
    for metal, points in sorted(series.items()):
        for i in range(len(points)):
            f = features(points, i)
            if f is None:
                continue
            forward = points[i + 12][1] / points[i][1] - 1.0 if i + 12 < len(points) else None
            rows.append((metal, i, points[i][0], f[0], f[1], forward))
    return rows


def fit(rows):
    """Ordinary least squares: forward = a + b*value + c*trend (pooled)."""
    data = [(1.0, r[3], r[4], r[5]) for r in rows if r[5] is not None]
    if len(data) < 30:
        raise ValueError("too few in-sample observations to fit")
    xtx = [[sum(d[i] * d[j] for d in data) for j in range(3)] for i in range(3)]
    xty = [sum(d[i] * d[3] for d in data) for i in range(3)]
    # solve 3x3 by Gaussian elimination
    m = [row[:] + [xty[k]] for k, row in enumerate(xtx)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(m[r][col]))
        m[col], m[pivot] = m[pivot], m[col]
        for r in range(3):
            if r != col:
                factor = m[r][col] / m[col][col]
                m[r] = [a - factor * b for a, b in zip(m[r], m[col])]
    return tuple(m[k][3] / m[k][k] for k in range(3))


def predict(coef, value, trend):
    return coef[0] + coef[1] * value + coef[2] * trend


def evaluate(series, coef, cash, start, end):
    rows = [r for r in observations(series) if start <= r[2] <= end]
    scored = [(predict(coef, r[3], r[4]), r[5], call_for(predict(coef, r[3], r[4]))) for r in rows if r[5] is not None]
    by_call = {}
    for exp, fwd, call in scored:
        by_call.setdefault(call, []).append(fwd)
    quint = sorted(scored, key=lambda s: s[0])
    k = max(1, len(quint) // 5)
    calibration = [(mean(s[0] for s in quint[q * k:(q + 1) * k]), mean(s[1] for s in quint[q * k:(q + 1) * k])) for q in range(5)]
    # strategy: per metal, hold while call is BUY/STRONG_BUY (decided at i, earns month i+2), else cash
    per_metal, monthly = {}, []
    for metal, points in sorted(series.items()):
        strat, hold, cash_used, prev, invested = [], [], [], None, 0
        for i in range(len(points) - 1 - bt.EXECUTION_LAG_MONTHS):
            if not (start <= points[i][0] <= end):
                continue
            f = features(points, i)
            if f is None:
                continue
            on = call_for(predict(coef, *f)) in INVESTED
            j = i + 1 + bt.EXECUTION_LAG_MONTHS
            metal_return = points[j][1] / points[j - 1][1] - 1.0
            c = cash.get((points[j][0].year, points[j][0].month), 0.0)
            cost = SWITCH_COST if prev is not None and on != prev else 0.0
            strat.append((metal_return if on else c) - cost)
            hold.append(metal_return)
            cash_used.append(c)
            invested += on
            prev = on
        if strat:
            per_metal[metal] = {"strategy": bt.performance(strat, cash_used), "hold": bt.performance(hold, cash_used),
                                "share_invested": invested / len(strat)}
            monthly.append((strat, hold, cash_used))
    length = min(len(m[0]) for m in monthly)
    portfolio = {
        "strategy": bt.performance([mean(m[0][-length:][t] for m in monthly) for t in range(length)], monthly[0][2][-length:]),
        "hold": bt.performance([mean(m[1][-length:][t] for m in monthly) for t in range(length)], monthly[0][2][-length:]),
    }
    beats = sum(1 for v in per_metal.values() if (v["strategy"].get("sharpe") or -9) > (v["hold"].get("sharpe") or -9))
    return {
        "observations": len(scored),
        "rank_correlation": bt.spearman([s[0] for s in scored], [s[1] for s in scored]),
        "by_call": {c: {"months": len(v), "average_next_12m": mean(v), "share_positive": sum(x > 0 for x in v) / len(v)} for c, v in by_call.items()},
        "calibration_quintiles": [{"expected": e, "realized": r} for e, r in calibration],
        "portfolio": portfolio,
        "metals_beating_hold_sharpe": beats,
        "metals": len(per_metal),
        "per_metal": per_metal,
    }


def _pct(x):
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def render(report):
    c = report["coefficients"]
    o = report["out_of_sample"]
    s, h = o["portfolio"]["strategy"], o["portfolio"]["hold"]
    lines = [
        "# Metals model v3 research", "",
        f"Fitted on {report['in_sample'][0]} to {report['in_sample'][1]} ({report['in_sample_observations']} metal-months); "
        f"judged on {report['out_of_sample_period'][0]} to {report['out_of_sample_period'][1]}. Cash: {report['cash_source']}.", "",
        f"Expected 12-month return = {c['intercept']:+.3f} {c['value']:+.3f} x value {c['trend']:+.3f} x trend "
        "(value = log price vs 10-year average; trend = log price vs 12-month average).", "",
        "## Out-of-sample", "",
        f"- Rank correlation (expected vs actual next 12 months): {o['rank_correlation']:+.3f} (current model: about 0.00)",
        f"- Strategy (hold metals rated BUY or STRONG BUY, else T-bills; equal-weight): annual return {_pct(s.get('annual_return'))}, "
        f"max drawdown {_pct(s.get('max_drawdown'))}, Sharpe {s.get('sharpe') or 0:.2f}",
        f"- Holding all metals: annual return {_pct(h.get('annual_return'))}, max drawdown {_pct(h.get('max_drawdown'))}, Sharpe {h.get('sharpe') or 0:.2f}",
        f"- Metals where the strategy beat holding (Sharpe): {o['metals_beating_hold_sharpe']}/{o['metals']}", "",
        "| Call | Months | Average next 12 months | Share positive |", "|---|---|---|---|",
    ]
    for name, _ in CALL_THRESHOLDS + (("AVOID", None),):
        b = o["by_call"].get(name)
        if b:
            lines.append(f"| {name} | {b['months']} | {_pct(b['average_next_12m'])} | {b['share_positive'] * 100:.0f}% |")
    lines += ["", "| Expected-return fifth | Average expected | Average realized |", "|---|---|---|"]
    for q, cal in enumerate(o["calibration_quintiles"], start=1):
        lines.append(f"| {q} (lowest first) | {_pct(cal['expected'])} | {_pct(cal['realized'])} |")
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--in-sample-start", type=date.fromisoformat, default=date(1980, 1, 1))
    parser.add_argument("--split", type=date.fromisoformat, default=date(2006, 1, 1))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "operations" / "metals" / "v3_research")
    args = parser.parse_args(argv)
    series = {m: p for m, p in bt.load_history(args.history).items() if bt.is_monthly(p)}
    in_end = date(args.split.year - 1, 12, 31)
    # In-sample fit uses only observations whose 12-month outcome is known before the split.
    in_rows = [r for r in observations(series) if args.in_sample_start <= r[2] and r[5] is not None
               and series[r[0]][min(r[1] + 12, len(series[r[0]]) - 1)][0] <= in_end]
    a, b, c = fit(in_rows)
    cash, cash_source = bt.fetch_cash(os.environ.get("UIIP_FRED_API_KEY"), args.in_sample_start)
    last = max(points[-1][0] for points in series.values())
    report = {
        "in_sample": [args.in_sample_start.isoformat(), in_end.isoformat()],
        "in_sample_observations": len(in_rows),
        "out_of_sample_period": [args.split.isoformat(), last.isoformat()],
        "coefficients": {"intercept": a, "value": b, "trend": c},
        "cash_source": cash_source,
        "out_of_sample": evaluate(series, (a, b, c), cash, args.split, last),
        "metals": sorted(series),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "v3_research.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    markdown = render(report)
    (args.output_dir / "v3_research.md").write_text(markdown, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
