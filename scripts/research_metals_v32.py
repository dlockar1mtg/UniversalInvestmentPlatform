"""Metals model v3.2 research: fixing the bottom end, and error-based 12-month ranges.

Variants (decided before looking at results), each refitted every January on outcomes
already known, judged once on the out-of-sample period against v3.1:
  v3.1               value + trend (production)
  v3.2a capped       value + trend, each limited to its 5th-95th percentile at the refit
  v3.2b +3y change   value + trend + 3-year log price change
  v3.2c both         capped value + trend + 3-year change
Adoption rule: a variant replaces v3.1 only if its top-3 strategy matches or beats v3.1 on
annual return and Sharpe, its rank correlation is at least v3.1's, and its bottom-fifth
calibration gap (realized minus expected) is smaller. Each variant's 12-month range is its
own refit errors (10th to 90th percentile) around the prediction; coverage should be ~80%.
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


def _load(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


v3 = _load("research_metals_v3", "research_metals_v3.py")
bt = v3.bt

VARIANTS = {
    "v3.1": {"features": ("value", "trend"), "capped": False},
    "v3.2a capped": {"features": ("value", "trend"), "capped": True},
    "v3.2b +3y change": {"features": ("value", "trend", "change36"), "capped": False},
    "v3.2c both": {"features": ("value", "trend", "change36"), "capped": True},
}
CAP_QUANTILES = (0.05, 0.95)
RANGE_QUANTILES = (0.10, 0.90)


def features(points, i):
    base = v3.features(points, i)
    if base is None or i < 36:
        return None
    return {"value": base[0], "trend": base[1], "change36": math.log(points[i][1] / points[i - 36][1])}


def rows_for(series):
    out = []
    for metal, points in sorted(series.items()):
        for i in range(len(points)):
            f = features(points, i)
            if f is None:
                continue
            forward = points[i + 12][1] / points[i][1] - 1.0 if i + 12 < len(points) else None
            out.append({"metal": metal, "i": i, "date": points[i][0], "f": f, "forward": forward})
    return out


def quantile(values, q):
    s = sorted(values)
    pos = (len(s) - 1) * q
    lo = int(math.floor(pos))
    hi = min(lo + 1, len(s) - 1)
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def ols(x_rows, y):
    """Least squares with intercept; x_rows is a list of feature lists."""
    k = len(x_rows[0]) + 1
    data = [[1.0, *x] for x in x_rows]
    m = [[sum(d[i] * d[j] for d in data) for j in range(k)] + [sum(d[i] * t for d, t in zip(data, y))] for i in range(k)]
    for col in range(k):
        pivot = max(range(col, k), key=lambda r: abs(m[r][col]))
        m[col], m[pivot] = m[pivot], m[col]
        if abs(m[col][col]) < 1e-12:
            raise ValueError("singular design")
        for r in range(k):
            if r != col:
                factor = m[r][col] / m[col][col]
                m[r] = [a - factor * b for a, b in zip(m[r], m[col])]
    return [m[i][k] / m[i][i] for i in range(k)]


def walk_forward(series, variant, first_start, start, end):
    """(metal, i) -> (expected, low, high), refitting each January on outcomes known by then."""
    spec = VARIANTS[variant]
    names = spec["features"]
    rows = rows_for(series)
    out = {}
    for year in range(start.year, end.year + 1):
        cutoff = date(year, 1, 1)
        known = [r for r in rows if r["date"] >= first_start and r["forward"] is not None
                 and series[r["metal"]][r["i"] + 12][0] < cutoff]
        if len(known) < 60:
            continue
        caps = {n: (quantile([r["f"][n] for r in known], CAP_QUANTILES[0]), quantile([r["f"][n] for r in known], CAP_QUANTILES[1]))
                for n in names} if spec["capped"] else None

        def vector(f):
            return [min(max(f[n], caps[n][0]), caps[n][1]) if caps else f[n] for n in names]

        coef = ols([vector(r["f"]) for r in known], [r["forward"] for r in known])
        predict = lambda f: coef[0] + sum(c * x for c, x in zip(coef[1:], vector(f)))
        residuals = [r["forward"] - predict(r["f"]) for r in known]
        low, high = quantile(residuals, RANGE_QUANTILES[0]), quantile(residuals, RANGE_QUANTILES[1])
        for r in rows:
            if r["date"].year == year and start <= r["date"] <= end:
                e = predict(r["f"])
                out[(r["metal"], r["i"])] = (e, e + low, e + high)
    return out


def coverage(series, bands):
    hits = total = 0
    for (metal, i), (_, low, high) in bands.items():
        points = series[metal]
        if i + 12 < len(points):
            actual = points[i + 12][1] / points[i][1] - 1.0
            hits += low <= actual <= high
            total += 1
    return hits / total if total else None


def evaluate(series, variant, cash, first_start, start, end):
    bands = walk_forward(series, variant, first_start, start, end)
    predictions = {key: value[0] for key, value in bands.items()}
    score = v3.score_predictions(series, predictions)
    strategies = v3.rule_strategies(series, predictions, cash)
    bottom = score["calibration_quintiles"][0]
    return {
        "rank_correlation": score["rank_correlation"],
        "bottom_fifth": bottom,
        "bottom_gap": bottom["realized"] - bottom["expected"],
        "top_fifth": score["calibration_quintiles"][-1],
        "calibration_quintiles": score["calibration_quintiles"],
        "by_call": score["by_call"],
        "strategies": strategies,
        "range_coverage": coverage(series, bands),
        "average_range_width": mean(h - l for _, l, h in bands.values()) if bands else None,
    }


def decide(results):
    base = results["v3.1"]
    b_top = base["strategies"]["top_k"]
    verdicts = {}
    for name, r in results.items():
        if name == "v3.1":
            continue
        top = r["strategies"]["top_k"]
        checks = {
            "top3_return": (top.get("annual_return") or -9) >= (b_top.get("annual_return") or -9),
            "top3_sharpe": (top.get("sharpe") or -9) >= (b_top.get("sharpe") or -9),
            "rank_correlation": (r["rank_correlation"] or -9) >= (base["rank_correlation"] or -9),
            "bottom_gap_smaller": abs(r["bottom_gap"]) < abs(base["bottom_gap"]),
        }
        verdicts[name] = {"passes": all(checks.values()), "checks": checks}
    winners = [n for n, v in verdicts.items() if v["passes"]]
    best = max(winners, key=lambda n: results[n]["strategies"]["top_k"].get("sharpe") or -9) if winners else None
    return {"verdicts": verdicts, "adopt": best}


def _pct(x):
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def render(report):
    lines = ["# Metals model v3.2 research", "",
             f"Walk-forward, refit each January; judged {report['period'][0]} to {report['period'][1]}. Cash: {report['cash_source']}.", "",
             "| Variant | Rank corr | Top-3 annual | Top-3 Sharpe | Top-3 max DD | Bottom fifth exp / real | Top fifth exp / real | 80% range coverage | Avg range width |",
             "|---|---|---|---|---|---|---|---|---|"]
    for name, r in report["results"].items():
        t = r["strategies"]["top_k"]
        lines.append(f"| {name} | {r['rank_correlation']:+.3f} | {_pct(t.get('annual_return'))} | {t.get('sharpe') or 0:.2f} | {_pct(t.get('max_drawdown'))} | "
                     f"{_pct(r['bottom_fifth']['expected'])} / {_pct(r['bottom_fifth']['realized'])} | {_pct(r['top_fifth']['expected'])} / {_pct(r['top_fifth']['realized'])} | "
                     f"{(r['range_coverage'] or 0) * 100:.0f}% | {_pct(r['average_range_width'])} |")
    h = report["results"]["v3.1"]["strategies"]["hold"]
    lines += ["", f"Holding all metals: {_pct(h.get('annual_return'))} a year, Sharpe {h.get('sharpe') or 0:.2f}.", "", "## Adoption rule", ""]
    for name, v in report["decision"]["verdicts"].items():
        failed = [k for k, ok in v["checks"].items() if not ok]
        lines.append(f"- {name}: {'PASSES' if v['passes'] else 'fails ' + ', '.join(failed)}")
    lines += ["", f"**Decision: {'adopt ' + report['decision']['adopt'] if report['decision']['adopt'] else 'keep v3.1'}**"]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--first-start", type=date.fromisoformat, default=date(1980, 1, 1))
    parser.add_argument("--split", type=date.fromisoformat, default=date(2006, 1, 1))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "operations" / "metals" / "v32_research")
    args = parser.parse_args(argv)
    series = {m: p for m, p in bt.load_history(args.history).items() if bt.is_monthly(p)}
    cash, cash_source = bt.fetch_cash(os.environ.get("UIIP_FRED_API_KEY"), args.first_start)
    last = max(points[-1][0] for points in series.values())
    results = {name: evaluate(series, name, cash, args.first_start, args.split, last) for name in VARIANTS}
    report = {"period": [args.split.isoformat(), last.isoformat()], "cash_source": cash_source,
              "results": results, "decision": decide(results)}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "v32_research.json").write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    markdown = render(report)
    (args.output_dir / "v32_research.md").write_text(markdown, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as handle:
            handle.write(markdown)
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
