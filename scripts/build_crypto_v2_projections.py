"""Build Crypto v2 Monte Carlo projections, check them walk-forward, and keep a self-scoring forecast log.

Method (October 2026 research): replay random 6-month blocks of the coin's own monthly log returns
from the last 72 months, 10,000 paths, to get 10/25/50/75/90th percentile prices at 12, 24 and 36
months. Each day the 12-month method is re-checked walk-forward over the most recent test months
(each forecast built only from data known at its month). A projection is VALIDATED when the raw
simulation passes, PROVISIONAL when only the recalibrated version passes (its percentile levels are
shifted to where past outcomes actually landed), and NOT_VALIDATED otherwise. The 36-month view
cannot be checked yet (about 1.5 independent 3-year periods exist): it is a SCENARIO, shown only
when the 12-month projection is VALIDATED.
The forecast log records each day's projections and fills in the outcome when it comes due.
"""
from __future__ import annotations

import argparse
import csv
import json
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CLOSES = ROOT / "data" / "crypto" / "crypto_monthly_closes.csv"
OUTPUT = ROOT / "data" / "crypto" / "crypto_v2_projections.json"
LOG = ROOT / "data" / "crypto" / "crypto_v2_forecast_log.csv"
COINS = ("bitcoin", "ethereum")
WINDOW, BLOCK, PATHS, TEST_PATHS = 72, 6, 10000, 2000
HORIZONS = (12, 24, 36)
TAUS = (0.10, 0.25, 0.50, 0.75, 0.90)
RECENT_TESTS = 48
RULE = {"above_median": (0.35, 0.65), "inside_50": (0.35, 0.65), "inside_80": (0.70, 0.90)}
LOG_FIELDS = ["as_of", "asset", "horizon_months", "status", "method", "price", "p10", "p25", "p50", "p75", "p90",
              "prob_up", "due_month", "outcome_price", "outcome_percentile", "inside_50", "inside_80"]


def load(path: Path):
    series, updated = {}, ""
    with path.open(newline="", encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            try:
                close = float(r["close"])
            except (TypeError, ValueError):
                continue
            if close > 0:
                series.setdefault(r["asset"], {})[r["month"]] = close
                updated = max(updated, str(r.get("updated_utc") or ""))
    return {a: sorted(m.items()) for a, m in series.items()}, updated


def _mi(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def _month(index: int) -> str:
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


def simulate(log_returns, horizon, paths, seed):
    """Sum of `horizon` monthly log returns built from random 6-month blocks; returns simple returns, sorted."""
    v = np.asarray(log_returns, dtype=float)
    starts = np.arange(len(v) - BLOCK + 1)
    blocks = -(-horizon // BLOCK)
    rng = np.random.default_rng(seed)
    picks = rng.choice(starts, size=(paths, blocks))
    idx = (picks[:, :, None] + np.arange(BLOCK)[None, None, :]).reshape(paths, -1)[:, :horizon]
    return np.sort(np.expm1(v[idx].sum(axis=1)))


def _seed(*parts) -> int:
    return zlib.crc32("|".join(map(str, parts)).encode())


def _score(rows):
    n = len(rows)
    if not n:
        return None
    stats = {"tests": n,
             "above_median": sum(r["above"] for r in rows) / n,
             "inside_50": sum(r["in50"] for r in rows) / n,
             "inside_80": sum(r["in80"] for r in rows) / n}
    stats["passes"] = all(lo <= stats[k] <= hi for k, (lo, hi) in RULE.items())
    return stats


def walk_forward(series, horizon):
    """Raw and recalibrated walk-forward checks; returns (raw stats, recalibrated stats, current recal levels)."""
    months = [m for m, _ in series]
    prices = np.array([p for _, p in series])
    lr = np.diff(np.log(prices))
    index = {m: i for i, m in enumerate(months)}
    pits, rows_raw, rows_cal = {}, [], []
    for i, m in enumerate(months):
        if i < WINDOW + 1:
            continue
        sims = simulate(lr[i - WINDOW:i], horizon, TEST_PATHS, _seed("wf", m, horizon))
        j = index.get(_month(_mi(m) + horizon))
        known = [pits[s] for s in pits if _mi(m) - _mi(s) >= horizon]
        if j is None:
            continue
        y = prices[j] / prices[i] - 1
        pits[m] = float(np.searchsorted(sims, y) / len(sims))
        q_raw = np.quantile(sims, TAUS)
        q_cal = np.quantile(sims, np.clip(np.quantile(known, TAUS), 0, 1)) if len(known) >= 12 else None
        rows_raw.append({"above": y > q_raw[2], "in50": q_raw[1] <= y <= q_raw[3], "in80": q_raw[0] <= y <= q_raw[4]})
        if q_cal is not None:
            rows_cal.append({"above": y > q_cal[2], "in50": q_cal[1] <= y <= q_cal[3], "in80": q_cal[0] <= y <= q_cal[4]})
    known_pits = sorted(pits.values())
    levels = np.clip(np.quantile(known_pits, TAUS), 0, 1).tolist() if len(known_pits) >= 12 else None
    return _score(rows_raw[-RECENT_TESTS:]), _score(rows_cal[-RECENT_TESTS:]), (levels, known_pits)


def project(asset, series):
    months = [m for m, _ in series]
    prices = np.array([p for _, p in series])
    if len(prices) < WINDOW + 1:
        return {"status": "NOT_VALIDATED", "reason": "fewer than 72 months of prices"}
    lr = np.diff(np.log(prices))[-WINDOW:]
    price, as_of = float(prices[-1]), months[-1]
    raw12, cal12, (levels12, pits12) = walk_forward(series, 12)
    if raw12 and raw12["passes"]:
        status, method = "VALIDATED", "MONTE_CARLO"
    elif cal12 and cal12["passes"] and levels12:
        status, method = "PROVISIONAL", "MONTE_CARLO_RECALIBRATED"
    else:
        status, method = "NOT_VALIDATED", None
    out = {"status": status, "method": method, "price": price, "price_month": as_of,
           "validation_12m": {"raw": raw12, "recalibrated": cal12, "rule": RULE, "recent_tests": RECENT_TESTS},
           "horizons": {}}
    for k in HORIZONS:
        if k == 36 and status != "VALIDATED":       # the 3-year scenario extends a validated projection only
            continue
        sims = simulate(lr, k, PATHS, _seed(asset, as_of, k))
        taus, pits = list(TAUS), None
        if method == "MONTE_CARLO_RECALIBRATED" and k != 36:      # the 3-year scenario is always the plain simulation
            levels, pits = (levels12, pits12) if k == 12 else walk_forward(series, k)[2]
            taus = levels or taus
            pits = pits if levels else None

        def prob(threshold, above=True):
            raw_cdf = float(np.mean(sims <= threshold))
            cdf = float(np.searchsorted(pits, raw_cdf, side="right") / len(pits)) if pits else raw_cdf
            return 1 - cdf if above else cdf

        q = np.quantile(sims, taus)
        out["horizons"][str(k)] = {
            "kind": "SCENARIO" if k == 36 else status, "months": k,
            "returns": dict(zip(("p10", "p25", "p50", "p75", "p90"), map(float, q))),
            "prices": dict(zip(("p10", "p25", "p50", "p75", "p90"), (float(price * (1 + x)) for x in q))),
            "prob_up": prob(0.0), "prob_up_50": prob(0.5), "prob_down_30": prob(-0.3, above=False)}
    return out


def update_log(path: Path, projections: dict, closes: dict, as_of: str):
    rows = []
    if path.is_file():
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
    have = {(r["as_of"], r["asset"], r["horizon_months"]) for r in rows}
    for asset, pr in projections.items():
        for k, h in (pr.get("horizons") or {}).items():
            key = (as_of, asset, k)
            if key in have:
                continue
            rows.append({"as_of": as_of, "asset": asset, "horizon_months": k, "status": h["kind"], "method": pr.get("method") or "",
                         "price": f"{pr['price']:.8g}", **{q: f"{v:.8g}" for q, v in h["prices"].items()},
                         "prob_up": f"{h['prob_up']:.4f}", "due_month": _month(_mi(pr["price_month"]) + int(k))})
    for r in rows:                                   # score entries whose due month has a stored close
        if r.get("outcome_price"):
            continue
        due = dict(closes.get(r["asset"]) or []).get(r["due_month"])
        if due is None:
            continue
        qs = [float(r[q]) for q in ("p10", "p25", "p50", "p75", "p90")]
        r["outcome_price"] = f"{due:.8g}"
        r["outcome_percentile"] = next((lab for lab, q in zip(("below p10", "p10-p25", "p25-p50", "p50-p75", "p75-p90"), qs) if due < q), "above p90")
        r["inside_50"] = str(qs[1] <= due <= qs[3])
        r["inside_80"] = str(qs[0] <= due <= qs[4])
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=LOG_FIELDS)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["as_of"], r["asset"], int(r["horizon_months"]))))
    return len(rows)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--closes", type=Path, default=CLOSES)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--log", type=Path, default=LOG)
    args = parser.parse_args(argv)
    closes, updated = load(args.closes)
    as_of = (updated or "")[:10]
    projections = {a: project(a, closes[a]) for a in COINS if a in closes}
    args.output.write_text(json.dumps({"as_of": as_of, "window_months": WINDOW, "block_months": BLOCK, "paths": PATHS,
                                       "projections": projections}, indent=1) + "\n", encoding="utf-8")
    n = update_log(args.log, projections, closes, as_of)
    print(json.dumps({a: p["status"] for a, p in projections.items()}), f"| log rows {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
