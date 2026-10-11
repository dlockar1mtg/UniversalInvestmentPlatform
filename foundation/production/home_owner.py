"""Owner mode for the Homestead: the home once it is bought.

Recorded once at closing (stored in the plan, never in the repository): price, closing month, down payment,
closing costs, the loan (amount, rate, term), and the monthly PMI, escrow (property tax and insurance) and HOA.
After that, the page keeps:

  the loan balance   the amortization schedule, moved on by every extra principal payment you record; a balance
                     from a statement replaces the schedule from that month
  the home's value   the price moved with the market's house price index (the Housing platform's FHFA index for
                     Wichita or Dallas-Fort Worth) since closing; a newer appraisal replaces it
  equity             value minus the loan, a line of net worth (never money you can spend)

and runs the checks an owner needs: when PMI can come off (80% of the original value on request, 78% on its
own), whether refinancing at today's rate pays back its costs, extra principal against investing, a maintenance
fund, and what the monthly payment is made of. Rules of thumb, not lending or tax advice.
"""
from __future__ import annotations

import re

MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
MARKETS = ("Wichita", "DFW Composite")
REFI_COST_PCT = 0.025          # typical refinance closing costs, share of the balance
MAINTENANCE = (0.01, 0.02)     # a year, share of the home's value


class HomeError(ValueError):
    pass


def _idx(month: str) -> int:
    return int(month[:4]) * 12 + int(month[5:7]) - 1


def _month(i: int) -> str:
    return f"{i // 12}-{i % 12 + 1:02d}"


def _num(v, name, *, lo=0.0, hi=1e8, allow_none=False):
    if v in (None, ""):
        if allow_none:
            return None
        raise HomeError(f"home {name} is required")
    try:
        n = float(v)
    except (TypeError, ValueError):
        raise HomeError(f"home {name} must be a number") from None
    if not (lo <= n <= hi) or n != n:
        raise HomeError(f"home {name} is out of range")
    return round(n, 6) if hi <= 1 else round(n, 2)


def _month_of(v, name):
    v = str(v or "")
    if not MONTH.match(v):
        raise HomeError(f"home {name} must look like 2029-12")
    return v


def normalize_home(raw) -> dict | None:
    if raw in (None, {}):
        return None
    if not isinstance(raw, dict):
        raise HomeError("home must be an object")
    h = {
        "market": str(raw.get("market") or "Wichita"),
        "price": _num(raw.get("price"), "price", lo=1),
        "closing_month": _month_of(raw.get("closing_month"), "closing_month"),
        "down_payment": _num(raw.get("down_payment"), "down_payment"),
        "closing_costs": _num(raw.get("closing_costs") or 0, "closing_costs"),
        "loan_amount": _num(raw.get("loan_amount"), "loan_amount"),
        "rate": _num(raw.get("rate"), "rate", hi=0.3),
        "term_years": int(_num(raw.get("term_years") or 30, "term_years", lo=5, hi=40)),
        "pmi_monthly": _num(raw.get("pmi_monthly") or 0, "pmi_monthly"),
        "escrow_monthly": _num(raw.get("escrow_monthly") or 0, "escrow_monthly"),
        "hoa_monthly": _num(raw.get("hoa_monthly") or 0, "hoa_monthly"),
        "hpi_at_closing": _num(raw.get("hpi_at_closing"), "hpi_at_closing", lo=0.0001, allow_none=True),
    }
    if h["market"] not in MARKETS:
        raise HomeError(f"home market must be one of {', '.join(MARKETS)}")
    if h["loan_amount"] > h["price"]:
        raise HomeError("home loan_amount cannot be more than the price")

    def items(key, fields):
        out = []
        for item in raw.get(key) or []:
            if not isinstance(item, dict):
                raise HomeError(f"each home {key} entry must be an object")
            row = {"month": _month_of(item.get("month"), f"{key} month")}
            for f, kw in fields.items():
                row[f] = _num(item.get(f), f"{key} {f}", **kw)
            out.append(row)
        if len(out) > 600:
            raise HomeError(f"too many home {key}")
        return sorted(out, key=lambda r: r["month"])

    h["statements"] = items("statements", {"balance": {}})
    h["extra_payments"] = items("extra_payments", {"amount": {"lo": 0.01}})
    h["appraisals"] = items("appraisals", {"value": {"lo": 1}, "hpi": {"lo": 0.0001, "allow_none": True}})
    return h


def payment(loan: float, rate: float, years: int) -> float:
    n, i = years * 12, rate / 12
    if loan <= 0:
        return 0.0
    return loan / n if i == 0 else loan * i / (1 - (1 + i) ** -n)


def schedule(home: dict, *, through: str | None = None, extra_monthly: float = 0.0, from_balance=None) -> list[dict]:
    """Month-by-month loan: the scheduled payment, extra principal recorded (and any test extra), statements."""
    pay = payment(home["loan_amount"], home["rate"], home["term_years"])
    i = home["rate"] / 12
    start = _idx(home["closing_month"])
    extras = {}
    for e in home["extra_payments"]:
        extras[e["month"]] = extras.get(e["month"], 0.0) + e["amount"]
    stmts = {s["month"]: s["balance"] for s in home["statements"]}
    bal = home["loan_amount"] if from_balance is None else from_balance[1]
    k0 = start if from_balance is None else _idx(from_balance[0])
    end = _idx(through) if through else start + home["term_years"] * 12
    rows = []
    k = k0
    while bal > 0.005 and k < end:
        k += 1
        m = _month(k)
        interest = bal * i
        principal = min(bal, pay - interest)
        extra = min(bal - principal, extras.get(m, 0.0) + extra_monthly)
        bal = bal - principal - extra
        if m in stmts and from_balance is None:
            bal = stmts[m]                             # the lender's figure wins
        rows.append({"month": m, "interest": round(interest, 2), "principal": round(principal, 2),
                     "extra": round(extra, 2), "balance": round(max(bal, 0.0), 2)})
    return rows


def balance_at(home: dict, month: str) -> float:
    if month <= home["closing_month"]:
        return home["loan_amount"]
    rows = schedule(home, through=month)
    return rows[-1]["balance"] if rows else 0.0


def value_at(home: dict, hpi_now: float | None) -> tuple[float, str]:
    """The price (or the newest appraisal) moved with the house price index since then."""
    base_value, base_hpi, source = home["price"], home.get("hpi_at_closing"), "PRICE_X_HPI"
    if home["appraisals"]:
        a = home["appraisals"][-1]
        base_value, base_hpi, source = a["value"], a.get("hpi"), "APPRAISAL_X_HPI"
    if hpi_now and base_hpi:
        return round(base_value * hpi_now / base_hpi, 2), source
    return round(base_value, 2), "APPRAISAL" if home["appraisals"] else "PRICE"


def _first_month_at(rows, limit):
    return next((r["month"] for r in rows if r["balance"] <= limit), None)


def home_status(home: dict, *, as_of_month: str, hpi_now: float | None = None, rate_now: float | None = None,
                extra_test: float = 100.0, refi_cost_pct: float = REFI_COST_PCT, keep_until: str | None = None) -> dict:
    bal = balance_at(home, as_of_month)
    value, value_source = value_at(home, hpi_now)
    pi = payment(home["loan_amount"], home["rate"], home["term_years"])
    ahead = schedule(home, from_balance=(as_of_month, bal))
    payoff = ahead[-1]["month"] if ahead else as_of_month
    interest_left = round(sum(r["interest"] for r in ahead), 2)
    faster = schedule(home, from_balance=(as_of_month, bal), extra_monthly=extra_test)
    saved = round(interest_left - sum(r["interest"] for r in faster), 2)
    months_sooner = len(ahead) - len(faster)

    pmi = None
    if home["pmi_monthly"] > 0:
        original = home["price"]
        req, auto = _first_month_at(ahead, 0.80 * original), _first_month_at(ahead, 0.78 * original)
        if bal <= 0.80 * original:
            req = as_of_month
        if bal <= 0.78 * original:
            auto = as_of_month
        pmi = {"monthly": home["pmi_monthly"], "request_month": req, "automatic_month": auto,
               "ltv_original": round(bal / original, 4), "ltv_today_value": round(bal / value, 4) if value else None}

    refi = None
    if rate_now is not None and bal > 0 and ahead:
        months_left = len(ahead)
        now_pay = payment(bal, home["rate"], months_left / 12)
        new_pay = payment(bal, rate_now, months_left / 12)
        cost = bal * refi_cost_pct
        saving = now_pay - new_pay
        even = None if saving <= 0 else int(-(-cost // saving))
        stay = _idx(keep_until) - _idx(as_of_month) if keep_until else 60   # without a sale date: 5 years
        refi = {"rate_now": rate_now, "rate_drop": round(home["rate"] - rate_now, 4), "costs": round(cost, 2),
                "monthly_saving": round(saving, 2), "break_even_months": even, "keep_months": stay,
                "keep_until": keep_until, "worth_a_look": even is not None and even < stay}

    lo, hi = MAINTENANCE
    return {
        "as_of_month": as_of_month, "value": value, "value_source": value_source, "loan_balance": round(bal, 2),
        "equity": round(value - bal, 2), "equity_share": round((value - bal) / value, 4) if value else None,
        "gain_since_closing": round(value - home["price"], 2),
        "payment": {"principal_and_interest": round(pi, 2), "pmi": home["pmi_monthly"], "escrow": home["escrow_monthly"],
                    "hoa": home["hoa_monthly"],
                    "total": round(pi + home["pmi_monthly"] + home["escrow_monthly"] + home["hoa_monthly"], 2)},
        "payoff_month": payoff, "interest_left": interest_left,
        "extra_principal": {"monthly": extra_test, "interest_saved": saved, "months_sooner": months_sooner,
                            "guaranteed_return": home["rate"]},
        "pmi": pmi, "refinance": refi,
        "maintenance_year": [round(value * lo, 2), round(value * hi, 2)],
        "maintenance_month": [round(value * lo / 12, 2), round(value * hi / 12, 2)],
        "limitations": [
            "The value follows the market's price index, not your street; an appraisal is the better figure when you have one.",
            "Refinance costs are taken as 2.5% of the balance; a lender's quote replaces that.",
            "PMI dates follow the original schedule and price (conventional loans); lenders may also drop PMI on a new appraisal, under their own rules. FHA mortgage insurance follows different rules.",
        ],
    }
