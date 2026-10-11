"""The retirement path: can the plan retire early, and what closes the gap if not.

Everything is in today's dollars (each sleeve's growth is the projection's planning assumption minus inflation).
Month by month, from today to age 95, over the same simulated markets as the Homestead:

  working     new money goes in as the plan says (after the plan's last month, its last 12 months' saving
              repeats, or the figure you set); retirement accounts get the paycheck deposits; in the house month
              the down payment and closing costs the bank and house fund cannot cover come out of investments
  the bridge  from the retirement age to 59 1/2, spending comes out of the investments you can reach (brokerage,
              Acorns, crypto, metals, MTG after selling costs). If they run out, retirement accounts are tapped
              early: tax plus the 10% penalty (72(t) payments or a Roth ladder can avoid the penalty; not modelled)
  after 59 1/2 spending comes out of retirement accounts first (less tax), then the rest; Social Security,
              when entered, lowers the spending from its start age

A path succeeds when the money lasts to 95. "On track" means at least 85% of simulated markets succeed.
Rules of thumb and limits are labelled as such; this is planning, not personal tax or investment advice.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from .household_plan import essential_spending, open_goals, roll_forward
from .household_projection import load_assumptions, monthly_payment

ROOT = Path(__file__).resolve().parents[2]
RULES = ROOT / "config" / "household" / "retirement_rules_2026.json"
ON_TRACK = 0.85
END_AGE = 95
PATHS = 1500
SEED = 20381001
SELL_HOME_COST = 0.06


def load_rules(path: Path = RULES) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _index(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def _month(index: int) -> str:
    return f"{index // 12}-{index % 12 + 1:02d}"


def _loan_balance(loan: float, rate: float, years: int, months_paid: int) -> float:
    pay = monthly_payment(loan, rate, years)
    i = rate / 12
    if months_paid >= years * 12:
        return 0.0
    if i == 0:
        return max(0.0, loan - pay * months_paid)
    return max(0.0, loan * (1 + i) ** months_paid - pay * ((1 + i) ** months_paid - 1) / i)


class _Inputs:
    """Everything one simulation needs, worked out once from the plan and the live figures."""

    def __init__(self, plan, as_of_month, holdings, retirement_start, retirement_monthly, a):
        s, r = plan["settings"], plan["settings"]["retirement"]
        self.r = r
        rows = roll_forward(plan)
        by_month = {row["month"]: row for row in rows}
        self.start = _index(as_of_month)
        self.age_now = r["age"] + (self.start - _index(r["age_as_of"])) / 12
        self.n = max(1, int(round((END_AGE - self.age_now) * 12)))
        now_row = by_month.get(as_of_month) or rows[-1]
        self.default_spending = round(abs(now_row["expenses"]) * 12, 2)
        self.spending = r["spending_year"] if r["spending_year"] is not None else self.default_spending
        last12 = rows[-12:]
        self.default_after_plan = round(sum(x["investment_contribution"] + x["house_fund_contribution"] for x in last12) / len(last12), 2)
        self.after_plan = r["after_plan_monthly_investing"] if r["after_plan_monthly_investing"] is not None else self.default_after_plan
        self.plan_end = _index(rows[-1]["month"])
        self.contrib = np.array([by_month[_month(self.start + k)]["investment_contribution"] if self.start + k <= self.plan_end
                                 else self.after_plan for k in range(self.n + 1)], dtype=float)

        # the house: what the bank and house fund cannot cover comes out of investments in the target month
        self.house_k, self.house_draw, self.house = None, 0.0, None
        target = s["target_month"]
        if target in by_month and _index(target) > self.start:
            t = by_month[target]
            years = (_index(target) - self.start) / 12
            price = (s["home_price_low"] + s["home_price_high"]) / 2 * (1 + s["home_price_growth"]) ** years
            safety = s["safety_fund"] if s["safety_fund"] is not None else essential_spending(plan, target) * s["safety_fund_months"]
            cash = t["house_fund_balance"] + max(0.0, t["bank_balance"] - safety)
            self.house_k = _index(target) - self.start
            self.house_draw = max(0.0, price * (s["down_payment_pct"] + s["closing_cost_pct"]) - cash)
            self.house = {"month": target, "price": round(price, 2), "from_investments": round(self.house_draw, 2),
                          "loan": round(price * (1 - s["down_payment_pct"]), 2)}
        self.mortgage = (s["mortgage_rate"], s["loan_years"])
        # goals besides the house, in today's dollars, paid from reachable investments when they can be (else postponed)
        self.goals = [(_index(g["month"]) - self.start, g) for g in open_goals(plan) if _index(g["month"]) > self.start]

        order = a["correlation_order"]
        self.invest_keys = [k for k in order if k != "retirement"]
        sleeves = a["sleeves"]
        infl = math.log1p(r["inflation"])
        self.drift = np.array([math.log1p(sleeves[k]["annual_return"]) - infl for k in order]) / 12
        self.vol = np.array([sleeves[k]["annual_volatility"] for k in order]) / math.sqrt(12)
        self.chol = np.linalg.cholesky(np.array(a["correlation"], dtype=float))
        self.keep = np.array([1 - sleeves[k]["sell_cost"] for k in self.invest_keys])
        mix = s["contribution_mix"]
        self.mix = np.array([mix.get(k, 0.0) for k in self.invest_keys])
        begin = {k: 0.0 for k in self.invest_keys}
        live = {k: float(v) for k, v in (holdings or {}).items() if k != "retirement" and isinstance(v, (int, float)) and v > 0}
        if live:
            for key, value in live.items():
                sleeve = a["holding_sleeves"].get(key)
                if sleeve is None:
                    raise ValueError(f"unknown holding kind: {key}")
                begin[sleeve] += value
            self.source = "LIVE_UIP_HOLDINGS"
        else:
            for sleeve, share in mix.items():
                begin[sleeve] += (by_month.get(as_of_month) or rows[0])["investment_balance"] * share
            self.source = "PLAN_BALANCE"
        self.begin = np.array([begin[k] for k in self.invest_keys])
        self.retirement_start = float(retirement_start or 0.0)
        self.retirement_monthly = float(retirement_monthly or 0.0)
        self.tax = r["withdrawal_tax"]
        self.ss = (r["social_security_monthly"] or 0.0, r["social_security_age"])

    def home_proceeds(self, retire_k: int) -> float:
        if self.house_k is None or retire_k <= self.house_k:
            return 0.0
        rate, years = self.mortgage
        owed = _loan_balance(self.house["loan"], rate, years, retire_k - self.house_k)
        return max(0.0, self.house["price"] * (1 - SELL_HOME_COST) - owed)


def _withdraw(inv, keep, need):
    """Sell evenly across sleeves (after each sleeve's selling cost); returns what could not be raised."""
    liquid = (inv * keep).sum(axis=1)
    frac = np.where(liquid > 0, np.minimum(1.0, need / np.where(liquid > 0, liquid, 1.0)), 0.0)
    inv *= (1 - frac)[:, None]
    return need - frac * liquid


def _simulate(x: _Inputs, retire_age: float, spending: float, *, extra_monthly=0.0, sell_home=False, paths=PATHS, record=False,
              goals=True):
    rng = np.random.default_rng(SEED)              # the same markets for every case, so cases compare fairly
    retire_k = max(0, int(round((retire_age - x.age_now) * 12)))
    access_k = int(round((59.5 - x.age_now) * 12))
    ss_k = int(round((x.ss[1] - x.age_now) * 12))
    inv = np.tile(x.begin, (paths, 1)).astype(float)
    ret = np.full(paths, x.retirement_start)
    failed = np.zeros(paths, dtype=bool)
    early = np.zeros(paths, dtype=bool)
    spend_m = spending / 12
    penalty = 0.10
    ages, acc, rets = [], [], []
    goal_at = {}
    for gk, g in (x.goals if goals else []):
        goal_at.setdefault(gk, []).append(g)
    goal_chance = {}

    def snap(k):
        ages.append(round(x.age_now + k / 12, 1))
        acc.append(np.percentile(inv.sum(axis=1), [10, 50, 90]))
        rets.append(np.percentile(ret, [10, 50, 90]))

    if record:
        snap(0)
    for k in range(1, x.n + 1):
        g = np.exp(x.drift + x.vol * (rng.standard_normal((paths, len(x.drift))) @ x.chol.T))
        inv *= g[:, :-1]
        ret *= g[:, -1]
        if k < retire_k:
            inv += (x.contrib[k] + extra_monthly) * x.mix
            ret += x.retirement_monthly
        if k == x.house_k and x.house_draw > 0:
            short = _withdraw(inv, x.keep, np.full(paths, x.house_draw))
            ret -= short                            # rare: the house is never bought with retirement money in the plan
        for g in goal_at.get(k, []):
            liquid = (inv * x.keep).sum(axis=1)
            covered = liquid >= g["amount"]
            _withdraw(inv, x.keep, np.where(covered, g["amount"], 0.0))
            goal_chance[g["id"]] = round(float(np.mean(covered)), 3)
        if sell_home and k == retire_k:
            inv[:, 0] += x.home_proceeds(retire_k)
        if k >= retire_k:
            need = np.full(paths, max(0.0, spend_m - (x.ss[0] if k >= ss_k else 0.0)))
            if k < access_k:
                short = _withdraw(inv, x.keep, need)
                gross = short / (1 - x.tax - penalty)
                touched = short > 0.005
                early |= touched
                take = np.minimum(ret, gross)
                ret -= take
                failed |= (gross - take) > 0.5
            else:
                gross = need / (1 - x.tax)
                take = np.minimum(ret, gross)
                ret -= take
                rest = (gross - take) * (1 - x.tax)
                failed |= _withdraw(inv, x.keep, rest) > 0.5
        ret = np.maximum(ret, 0.0)
        if record and k % 12 == 0:
            snap(k)
    out = {"chance": round(float(np.mean(~failed)), 3), "chance_bridge_without_retirement": round(float(np.mean(~early)), 3),
           "goal_chance": goal_chance}
    if record:
        out["by_age"] = [{"age": a, "investments": {f"p{p}": round(float(v), 2) for p, v in zip((10, 50, 90), i)},
                          "retirement": {f"p{p}": round(float(v), 2) for p, v in zip((10, 50, 90), r)}} for a, i, r in zip(ages, acc, rets)]
    return out


def _at_age(by_age, age):
    return min(by_age, key=lambda row: abs(row["age"] - age))


def _earliest_age(x: _Inputs, spending, sell_home, lo, hi=70):
    if _simulate(x, hi, spending, sell_home=sell_home, paths=800)["chance"] < ON_TRACK:
        return None
    while lo < hi:                                    # the chance rises with the retirement age
        mid = (lo + hi) // 2
        if _simulate(x, mid, spending, sell_home=sell_home, paths=800)["chance"] >= ON_TRACK:
            hi = mid
        else:
            lo = mid + 1
    return lo


def _extra_saving(x: _Inputs, age, spending, sell_home):
    if _simulate(x, age, spending, sell_home=sell_home, paths=800)["chance"] >= ON_TRACK:
        return 0.0
    lo, hi = 0.0, 20000.0
    if _simulate(x, age, spending, extra_monthly=hi, sell_home=sell_home, paths=800)["chance"] < ON_TRACK:
        return None
    for _ in range(11):
        mid = (lo + hi) / 2
        if _simulate(x, age, spending, extra_monthly=mid, sell_home=sell_home, paths=800)["chance"] >= ON_TRACK:
            hi = mid
        else:
            lo = mid
    return round(math.ceil(hi / 50) * 50, 2)


def match_check(jobs: list[dict], deposits: dict | None, rules: dict) -> dict:
    """Is each job's full match taken, and how much pre-tax room is left this year (one limit across jobs)."""
    out, employee_total = [], 0.0
    for job in jobs:
        dep = (deposits or {}).get(job.get("account_id") or "")
        deposit_year = None
        if dep and dep.get("per_paycheck") is not None and dep.get("every_days"):
            deposit_year = float(dep["per_paycheck"]) * 365 / float(dep["every_days"])
        salary, match = job["salary"], job.get("match_pct")
        total_pct = deposit_year / salary if deposit_year is not None and salary else None
        you = job.get("you_pct")
        inferred = you is None and total_pct is not None and match is not None
        if inferred:
            you = max(0.0, total_pct - match)        # the deposit is read as your part plus the match
        full = None if you is None or match is None else you + 1e-4 >= match
        missed = None if full is None or full else round((match - you) * salary, 2)
        employee = None if you is None else round(you * salary, 2)
        employee_total += employee or 0.0
        out.append({"label": job["label"], "salary": salary, "bonus": job.get("bonus", 0.0), "match_pct": match,
                    "you_pct": None if you is None else round(you, 4), "you_pct_inferred": inferred,
                    "deposit_year": None if deposit_year is None else round(deposit_year, 2),
                    "deposit_pct_of_pay": None if total_pct is None else round(total_pct, 4),
                    "match_year": None if match is None else round(match * salary, 2),
                    "full_match": full, "match_missed_year": missed, "employee_year": employee})
    limit = rules["employee_deferral_limit"]
    return {"jobs": out, "employee_total_year": round(employee_total, 2), "employee_limit": limit,
            "room_left_year": round(max(0.0, limit - employee_total), 2), "rules_year": rules["year"]}


def retirement_path(plan: dict, *, as_of_month: str, holdings: dict | None = None, retirement_start: float = 0.0,
                    retirement_monthly: float = 0.0, deposits: dict | None = None, assumptions: dict | None = None,
                    rules: dict | None = None) -> dict:
    r = plan["settings"].get("retirement")
    if not r:
        return {"configured": False}
    a = assumptions or load_assumptions()
    rules = rules or load_rules()
    x = _Inputs(plan, as_of_month, holdings, retirement_start, retirement_monthly, a)
    target_age = r["retire_age"]
    sell = r["sell_home_at_retirement"]
    main = _simulate(x, target_age, x.spending, sell_home=sell, record=True)
    lo = max(int(math.ceil(x.age_now)) + 1, 30)
    at_ret = _at_age(main["by_age"], target_age)
    at_access = _at_age(main["by_age"], 59.5)
    bridge_years = max(0.0, 59.5 - target_age)
    cases = [{"case": "home", "label": "As planned", "spending_year": x.spending, "chance": main["chance"],
              "earliest_age": _earliest_age(x, x.spending, sell, lo),
              "extra_monthly_for_target": _extra_saving(x, target_age, x.spending, sell)}]
    if r["spending_abroad_year"]:
        abroad = _simulate(x, target_age, r["spending_abroad_year"], sell_home=sell, paths=800)
        cases.append({"case": "abroad", "label": "Spending abroad", "spending_year": r["spending_abroad_year"],
                      "chance": abroad["chance"], "earliest_age": _earliest_age(x, r["spending_abroad_year"], sell, lo),
                      "extra_monthly_for_target": _extra_saving(x, target_age, r["spending_abroad_year"], sell)})
    without_goals = _simulate(x, target_age, x.spending, sell_home=sell, goals=False)["chance"] if x.goals else None   # same markets as the main run
    goals_out = [{"id": g["id"], "name": g["name"], "month": g["month"], "amount": g["amount"],
                  "chance": main["goal_chance"].get(g["id"])} for _, g in x.goals]
    other_sell = None
    if x.house is not None:
        alt = _simulate(x, target_age, x.spending, sell_home=not sell, paths=800)
        other_sell = {"sell_home": not sell, "chance": alt["chance"], "home_proceeds": round(x.home_proceeds(int(round((target_age - x.age_now) * 12))), 2)}
    retire_month = _month(x.start + int(round((target_age - x.age_now) * 12)))
    access_month = _month(x.start + int(round((59.5 - x.age_now) * 12)))
    plan_saving_year = round(float(x.contrib[1:13].sum()), 2)
    deposits_year = round(x.retirement_monthly * 12, 2)
    gross = sum(j["salary"] + j.get("bonus", 0.0) for j in r["jobs"])
    return {
        "configured": True, "on_track_threshold": ON_TRACK, "end_age": END_AGE, "paths": PATHS,
        "age_now": round(x.age_now, 2), "retire_age": target_age, "retire_month": retire_month,
        "access_age": 59.5, "access_month": access_month, "bridge_years": bridge_years,
        "spending_year": x.spending, "spending_default_year": x.default_spending,
        "spending_abroad_year": r["spending_abroad_year"], "withdrawal_rate": r["withdrawal_rate"],
        "fi_number": round(x.spending / r["withdrawal_rate"], 2), "fi_number_4pct": round(x.spending / 0.04, 2),
        "bridge_need": round(x.spending * bridge_years, 2),
        "chance": main["chance"], "chance_bridge_without_retirement": main["chance_bridge_without_retirement"],
        "at_retirement": at_ret, "at_access": at_access, "by_age": main["by_age"],
        "cases": cases, "goals": goals_out, "chance_without_goals": without_goals, "sell_home": sell, "other_sell_home": other_sell, "house": x.house,
        "starting_investments": round(float(x.begin.sum()), 2), "starting_investments_source": x.source,
        "starting_retirement": round(x.retirement_start, 2), "retirement_monthly": round(x.retirement_monthly, 2),
        "after_plan_monthly_investing": x.after_plan, "after_plan_default": x.default_after_plan,
        "plan_ends": _month(x.plan_end),
        "savings_rate": None if not gross else round((plan_saving_year + deposits_year) / gross, 3),
        "saving_next_12_months": {"investments": plan_saving_year, "retirement_deposits": deposits_year, "gross_pay": round(gross, 2)},
        "match": match_check(r["jobs"], deposits, rules),
        "rules": {k: rules[k] for k in ("year", "employee_deferral_limit", "ira_limit", "roth_ira_phaseout_single",
                                        "hsa_limit_self_only", "hsa_limit_family", "sources")},
        "assumptions": {"inflation": r["inflation"], "withdrawal_tax": r["withdrawal_tax"],
                        "real_returns": {k: round(math.expm1(float(d) * 12), 4) for k, d in zip(a["correlation_order"], x.drift)}},
        "limitations": [
            "Today's dollars throughout: growth is the Homestead's planning assumption less inflation.",
            "The monthly plan is taken as written; after its last month its last 12 months' saving repeats (or your figure).",
            "Before 59 1/2, retirement money is reached only with tax and the 10% penalty; 72(t) payments or a Roth conversion ladder can avoid the penalty but are not modelled.",
            "Taxes are a flat share of retirement-account withdrawals; capital-gains tax and health insurance before Medicare are not modelled. Add them to spending.",
            "The mix does not get safer with age yet.",
            "Goals besides the house are paid from reachable investments in their month; one the money cannot cover is left unpaid on that path.",
            "Social Security is left out unless you enter an estimate; retiring at 48 lowers it, since it counts your 35 highest-earning years.",
        ],
    }
