"""Crypto v2: valuation regime for new money in Bitcoin and Ethereum; context only for other coins.

Research (October 2026, Kraken month-end closes 2013-10 to 2026-10): momentum, the basis of the
legacy calls, did not predict 12-month returns (cross-coin rank correlation -0.10; alts tended to
reverse). Price relative to its 48-month average did, for BTC and ETH (rank correlation +0.58 to
+0.79 at 12-24 months): below the average was followed by large gains, above 2x by losses. For a
monthly buyer, pausing new money above 2x and redeploying it later beat steady buying in every
start year tested, but only modestly (0-8%, +30% from the 2017 peak). Altcoins lagged Bitcoin over
12 months in most months and have no validated edge, so they get no call. Few independent cycles
support any of this, so calls are regimes for new money, not return forecasts.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
CLOSES = ROOT / "data" / "crypto" / "crypto_monthly_closes.csv"
PROJECTIONS = ROOT / "data" / "crypto" / "crypto_v2_projections.json"   # built daily by scripts/build_crypto_v2_projections.py
MODEL_VERSION = "crypto-v2"
AVG_MONTHS = 48
ACCUMULATE_BELOW = 1.0
PAUSE_FROM = 2.0
CORE = ("bitcoin", "ethereum")
HALVINGS = ("2012-11", "2016-07", "2020-05", "2024-04")
ROBINHOOD_TRADABLE = {"bitcoin", "ethereum", "solana", "chainlink", "xrp", "avalanche"}   # robinhood.com coin-availability, Oct 2026
STATUS = {"ACCUMULATE": "ACCUMULATE_NEW_CAPITAL", "STEADY": "STEADY_ACCUMULATION", "PAUSE": "PAUSE_NEW_CAPITAL",
          "NO_CALL": "CONTEXT_ONLY_NO_CALL", "NO_PRICE": "NO_CURRENT_MARKET_PRICE"}


def _months_between(a: str, b: str) -> int:
    return (int(b[:4]) - int(a[:4])) * 12 + int(b[5:7]) - int(a[5:7])


def load_closes(path: Path = CLOSES) -> dict[str, list[tuple[str, float]]]:
    series: dict[str, dict[str, float]] = {}
    updated = ""
    with path.open(newline="", encoding="utf-8") as handle:
        for r in csv.DictReader(handle):
            try:
                close = float(r["close"])
            except (TypeError, ValueError):
                continue
            if close > 0:
                series.setdefault(r["asset"], {})[r["month"]] = close
                updated = max(updated, str(r.get("updated_utc") or ""))
    out = {a: sorted(m.items()) for a, m in series.items()}
    out["__updated__"] = updated     # type: ignore[assignment]
    return out


def _forward(series, k):
    idx = {m: i for i, (m, _) in enumerate(series)}
    return {m: series[i + k][1] / p - 1 for m, p in series for i in [idx[m]] if i + k < len(series)
            and _months_between(m, series[i + k][0]) == k}


def _ratios(series):
    out = {}
    for i in range(AVG_MONTHS - 1, len(series)):
        window = series[i - AVG_MONTHS + 1:i + 1]
        if _months_between(window[0][0], window[-1][0]) == AVG_MONTHS - 1:
            out[series[i][0]] = series[i][1] / (sum(p for _, p in window) / AVG_MONTHS)
    return out


def zone(ratio):
    if ratio is None:
        return None
    return "BELOW_AVERAGE" if ratio < ACCUMULATE_BELOW else "ONE_TO_TWO" if ratio < PAUSE_FROM else "OVER_TWO"


def zone_history(series):
    """In-sample: median next-12 and next-24-month return after months in each zone."""
    ratios, f12, f24 = _ratios(series), _forward(series, 12), _forward(series, 24)
    out = {}
    for z in ("BELOW_AVERAGE", "ONE_TO_TWO", "OVER_TWO"):
        ms = [m for m, r in ratios.items() if zone(r) == z]
        a = [f12[m] for m in ms if m in f12]
        b = [f24[m] for m in ms if m in f24]
        out[z] = {"months": len(ms), "median_12m": median(a) if a else None, "cases_12m": len(a),
                  "median_24m": median(b) if b else None, "cases_24m": len(b)}
    return out


def score_asset(asset, closes):
    series = closes.get(asset) or []
    if not series:
        return {"call": "NO_PRICE"}
    month, price = series[-1]
    ratios = _ratios(series)
    ratio = ratios.get(month)
    peak_month, peak = max(series, key=lambda x: x[1])
    year_ago = dict(series).get(f"{int(month[:4]) - 1}-{month[5:]}")
    hist_avg = []
    for i, (m, p) in enumerate(series[-60:]):
        hist_avg.append([m, p, round(ratios[m] and p / ratios[m], 6) if m in ratios else None])
    out = {"price": price, "price_month": month, "ratio": ratio, "avg_48m": price / ratio if ratio else None,
           "zone": zone(ratio), "peak": peak, "peak_month": peak_month, "drawdown": price / peak - 1,
           "change_12m": price / year_ago - 1 if year_ago else None, "history": hist_avg,
           "core": asset in CORE, "robinhood": asset in ROBINHOOD_TRADABLE}
    if asset in CORE:
        out["call"] = "NO_CALL" if ratio is None else "ACCUMULATE" if ratio < ACCUMULATE_BELOW else "STEADY" if ratio < PAUSE_FROM else "PAUSE"
        out["zone_history"] = zone_history(series)
    else:
        out["call"] = "NO_CALL"
        btc = dict(_forward(closes.get("bitcoin") or [], 12))
        mine = _forward(series, 12)
        rel = [mine[m] - btc[m] for m in mine if m in btc]
        out["vs_btc"] = {"cases": len(rel), "median_gap_12m": median(rel) if rel else None,
                         "share_beat_btc": sum(1 for x in rel if x > 0) / len(rel) if rel else None}
    if asset == "bitcoin":
        last = max(h for h in HALVINGS if h <= month)
        out["months_since_halving"] = _months_between(last, month)
        out["last_halving"] = last
    return out


def apply_crypto_model_decisions(records) -> int:
    """Add Crypto v2 decisions beside the certified crypto records, when UIP_CRYPTO_V2_ENABLED=1."""
    if os.environ.get("UIP_CRYPTO_V2_ENABLED") != "1":
        return 0
    path = Path(os.environ.get("UIP_CRYPTO_V2_PATH") or CLOSES)
    closes = load_closes(path)
    updated = closes.pop("__updated__", "")
    proj_path = Path(os.environ.get("UIP_CRYPTO_V2_PROJECTIONS_PATH") or PROJECTIONS)
    try:
        projections = json.loads(proj_path.read_text(encoding="utf-8")).get("projections") or {}
    except (OSError, ValueError):
        projections = {}                                   # no projection file yet: pages show no projection
    applied = 0
    for record in records:
        asset = str(record.asset_id)
        if record.record_type != "recommendation" or not asset.startswith("crypto:"):
            continue
        s = score_asset(asset.split(":", 1)[1], closes)
        call = s["call"]
        record.payload.update({
            "model_version": MODEL_VERSION, "model_call": call, "model_purchase_status": STATUS[call],
            "model_role": "CORE" if s.get("core") else "CONTEXTUAL", "model_price_usd": s.get("price"),
            "model_price_month": s.get("price_month"), "model_avg_48m_usd": s.get("avg_48m"), "model_ratio_48m": s.get("ratio"),
            "model_zone": s.get("zone"), "model_peak_usd": s.get("peak"), "model_peak_month": s.get("peak_month"),
            "model_drawdown_from_peak": s.get("drawdown"), "model_change_12m": s.get("change_12m"),
            "model_zone_history": s.get("zone_history"), "model_projection": projections.get(asset.split(":", 1)[1]), "model_vs_btc": s.get("vs_btc"),
            "model_months_since_halving": s.get("months_since_halving"), "model_last_halving": s.get("last_halving"),
            "model_robinhood_tradable": s.get("robinhood"), "model_price_history": s.get("history") or [],
            "model_thresholds": {"accumulate_below": ACCUMULATE_BELOW, "pause_from": PAUSE_FROM, "average_months": AVG_MONTHS},
            "model_as_of": updated or None,
        })
        applied += 1
    return applied
