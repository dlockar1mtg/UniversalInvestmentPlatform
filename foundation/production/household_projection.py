"""Ranges for the household plan: what the plan could be worth by the target month, and the house goal.

The monthly savings plan is taken as written (it is the part Devon controls). What is simulated is
the markets: each sleeve (stock ETFs, crypto, metals, MTG, T-bills, retirement) moves with its own
typical growth and yearly swing, and the sleeves move together through a correlation matrix, so a
bad year for stocks is usually a bad year for crypto too. Starting investments are the live UIP
holdings when the dashboard sends them; new money is split by the plan's contribution mix.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .household_plan import essential_spending, roll_forward

ROOT = Path(__file__).resolve().parents[2]
ASSUMPTIONS = ROOT / "config" / "household" / "projection_assumptions.json"


def load_assumptions(path: Path = ASSUMPTIONS) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _pcts(values: np.ndarray, levels) -> dict:
    return {f"p{p}": round(float(np.percentile(values, p)), 2) for p in levels}


def house_need(price: float, settings: dict, safety_fund: float) -> float:
    return round(price * (settings["down_payment_pct"] + settings["closing_cost_pct"]) + safety_fund, 2)


def monthly_payment(loan: float, rate: float, years: int) -> float:
    """Principal and interest only (no tax, insurance, PMI or HOA)."""
    if loan <= 0:
        return 0.0
    n, i = years * 12, rate / 12
    return round(loan / n if i == 0 else loan * i / (1 - (1 + i) ** -n), 2)


def project(plan: dict, *, as_of_month: str, holdings: dict | None = None, assumptions: dict | None = None) -> dict:
    a = assumptions or load_assumptions()
    s = plan["settings"]
    rows = roll_forward(plan)
    months = [r["month"] for r in rows]
    target = s["target_month"]
    end = max((k for k, m in enumerate(months) if m <= target), default=len(months) - 1)
    start = max((k for k, m in enumerate(months) if m <= as_of_month), default=0)
    start = min(start, end)
    order = a["correlation_order"]
    sleeves = a["sleeves"]
    invest_keys = [k for k in order if k != "retirement"]
    levels = a["percentiles"]

    # Starting point: live holdings by sleeve when the dashboard sends them, else the plan's balance.
    begin = {k: 0.0 for k in invest_keys}
    live = {k: float(v) for k, v in (holdings or {}).items() if isinstance(v, (int, float)) and v > 0}
    # Retirement statements (when entered) start the retirement balance; they are never an investment sleeve.
    live_retirement = live.pop("retirement", None)
    if live:
        for key, value in live.items():
            sleeve = a["holding_sleeves"].get(key)
            if sleeve is None:
                raise ValueError(f"unknown holding kind: {key}")
            begin[sleeve] += value
        source = "LIVE_UIP_HOLDINGS"
    else:
        for sleeve, share in s["contribution_mix"].items():
            begin[sleeve] += rows[start]["investment_balance"] * share
        source = "PLAN_BALANCE"
    start_investments = sum(begin.values())

    n_paths = int(a["paths"])
    steps = end - start
    rng = np.random.default_rng(int(a["seed"]))
    corr = np.array(a["correlation"], dtype=float)
    chol = np.linalg.cholesky(corr)
    vol = np.array([sleeves[k]["annual_volatility"] for k in order]) / math.sqrt(12)
    drift = np.array([math.log1p(sleeves[k]["annual_return"]) for k in order]) / 12
    mix = np.array([s["contribution_mix"].get(k, 0.0) for k in invest_keys])
    keep = np.array([1 - sleeves[k]["sell_cost"] for k in invest_keys])

    inv = np.tile(np.array([begin[k] for k in invest_keys]), (n_paths, 1))
    start_retirement = live_retirement if live_retirement is not None else rows[start]["retirement_balance"]
    ret = np.full(n_paths, start_retirement)
    series = []

    def snapshot(k, inv, ret):
        r = rows[k]
        cash_side = r["bank_balance"] + r["house_fund_balance"]
        invest_total = inv.sum(axis=1)
        usable = cash_side + (inv * keep).sum(axis=1) + (ret if s["house_counts_retirement"] else 0)
        worth = cash_side + r["home_equity"] + invest_total + ret
        return {"month": r["month"], "net_worth": _pcts(worth, levels), "investments": _pcts(invest_total, levels),
                "house_usable": _pcts(usable, levels), "plan_net_worth": r["net_worth"],
                "plan_house_usable": round(cash_side + r["investment_balance"] + (r["retirement_balance"] if s["house_counts_retirement"] else 0), 2)}, worth, usable

    snap, worth, usable = snapshot(start, inv, ret)
    series.append(snap)
    for k in range(start + 1, end + 1):
        shocks = rng.standard_normal((n_paths, len(order))) @ chol.T
        growth = np.exp(drift + vol * shocks)
        inv = inv * growth[:, :len(invest_keys)] + rows[k]["investment_contribution"] * mix
        ret = ret * growth[:, len(invest_keys)] + rows[k]["retirement_contribution"]
        snap, worth, usable = snapshot(k, inv, ret)
        series.append(snap)

    target_row = rows[end]
    # The safety fund is months of essential bills (every bill line unless the plan picks the essential ones).
    safety = s["safety_fund"] if s["safety_fund"] is not None else round(essential_spending(plan, target_row["month"]) * s["safety_fund_months"], 2)
    # Prices are entered in today's dollars; grow them to the target month at the plan's home-price growth.
    years = max(0, (int(months[end][:4]) - int(months[start][:4])) * 12 + int(months[end][5:7]) - int(months[start][5:7])) / 12
    grow = (1 + s["home_price_growth"]) ** years
    at = lambda p: round(p * grow, 2)  # noqa: E731
    ladder = sorted(set(a["price_ladder"]) | {s["home_price_low"], s["home_price_high"]})
    chances = [{"price": p, "price_at_target": at(p), "cash_needed": house_need(at(p), s, safety),
                "chance": round(float(np.mean(usable >= house_need(at(p), s, safety))), 3),
                "plan_reaches": series[-1]["plan_house_usable"] >= house_need(at(p), s, safety)} for p in ladder]
    dp_cc = s["down_payment_pct"] + s["closing_cost_pct"]
    max_price = {f"p{p}": round(max(0.0, (float(np.percentile(usable, p)) - safety) / dp_cc), -3) for p in (10, 50, 90)} if dp_cc > 0 else {}
    capacity = []
    for today_price in (s["home_price_low"], s["home_price_high"]):
        price = at(today_price)
        closing = price * s["closing_cost_pct"]
        row = {"price": today_price, "price_at_target": price, "closing_costs": round(closing, 2),
               "twenty_pct_payment": monthly_payment(price * (1 - s["down_payment_pct"]), s["mortgage_rate"], s["loan_years"])}
        for p in (10, 50, 90):
            down = min(price, max(0.0, float(np.percentile(usable, p)) - closing - safety))
            row[f"down_p{p}"] = round(down, 2)
            row[f"down_pct_p{p}"] = round(down / price, 3) if price else None
            row[f"payment_p{p}"] = monthly_payment(price - down, s["mortgage_rate"], s["loan_years"])
        capacity.append(row)
    by_sleeve = {k: round(float(np.median(inv[:, i])), 2) for i, k in enumerate(invest_keys)}
    by_sleeve["retirement"] = round(float(np.median(ret)), 2)
    contributed = sum(rows[k]["investment_contribution"] for k in range(start + 1, end + 1))
    return {
        "assumptions_id": a["assumptions_id"], "status": a["status"], "paths": n_paths,
        "start_month": months[start], "target_month": months[end], "requested_target_month": target,
        "target_in_plan": target in months, "starting_investments": round(start_investments, 2),
        "starting_investments_source": source, "starting_by_sleeve": {k: round(v, 2) for k, v in begin.items()},
        "investment_contributions_ahead": round(contributed, 2),
        "starting_retirement": round(float(start_retirement), 2),
        "starting_retirement_source": "RETIREMENT_STATEMENTS" if live_retirement is not None else "PLAN_BALANCE",
        "safety_fund": safety, "house_counts_retirement": s["house_counts_retirement"],
        "series": series, "target": series[-1],
        "target_by_sleeve_median": by_sleeve,
        "chance_below_plan_net_worth": round(float(np.mean(worth < target_row["net_worth"])), 3),
        "chance_investments_below_money_put_in": round(float(np.mean(inv.sum(axis=1) < start_investments + contributed)), 3),
        "house": {"price_low": s["home_price_low"], "price_high": s["home_price_high"],
                  "home_price_growth": s["home_price_growth"], "years_to_target": round(years, 2),
                  "price_low_at_target": at(s["home_price_low"]), "price_high_at_target": at(s["home_price_high"]),
                  "max_price_today_dollars": {k: round(v / grow, -3) for k, v in max_price.items()},
                  "down_payment_pct": s["down_payment_pct"], "closing_cost_pct": s["closing_cost_pct"],
                  "need_low": house_need(at(s["home_price_low"]), s, safety), "need_high": house_need(at(s["home_price_high"]), s, safety),
                  "chances": chances, "max_price_at_down_payment_pct": max_price, "capacity": capacity,
                  "mortgage_rate": s["mortgage_rate"], "loan_years": s["loan_years"]},
        "sleeves": {k: {"label": v["label"], "annual_return": v["annual_return"], "annual_volatility": v["annual_volatility"],
                        "sell_cost": v["sell_cost"]} for k, v in sleeves.items()},
        "limitations": [
            "Your monthly plan (income, bills, contributions) is assumed to happen as written.",
            "Market growth and swings are planning assumptions, not forecasts.",
            "Taxes on gains are not included; MTG is counted after about 12% selling costs.",
            "Mortgage payments are principal and interest only, at the plan's placeholder rate, not a live quote.",
            "Retirement accounts are left out of the house money unless the plan says otherwise.",
        ],
    }
