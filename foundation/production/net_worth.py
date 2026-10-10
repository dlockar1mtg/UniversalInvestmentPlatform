"""Net worth: what everything adds up to today, and a month-by-month history kept for good.

Owner decision (2026-10-10): the Treasury and the Hall show investments only; retirement accounts and the bank
count here, in net worth, which the Homestead shows. Debts and home equity join when those parts exist.

compute_net_worth() reads the same sources the dashboard reads:
  investments  certified holdings (transaction ledger x active presentation prices), manual ETF holdings at the
               Merchants' Guild close, and the latest Acorns snapshot
  retirement   each retirement account's latest statement plus paycheck deposits since (no market move assumed)
  bank         the household plan's bank balance for this month (a check-in when there is one, else rolled forward)
  house fund   the plan's house-fund balance for this month
  home equity  the plan's home-equity figure for this month (0 until a home is recorded)

NetWorthHistory keeps one row per month. The current month's row is refreshed on every capture; a month that has
ended is frozen and never rewritten. Months before the first capture can be seeded from the plan's ledger rows
whose balances you entered as actuals (source PLAN_LEDGER_ACTUALS).
"""
from __future__ import annotations

import json
from contextlib import closing
from datetime import date, datetime, timezone
from decimal import Decimal

COMPONENTS = ("investments", "retirement", "bank", "house_fund", "home_equity")


def _money(value) -> str:
    return str(Decimal(str(value)).quantize(Decimal("0.01")))


def _investments(transactions, presentation, manual, external) -> dict:
    from .hosted_manual_holdings import mark_to_market
    from .portfolio_accounting import derive_portfolio
    from .portfolio_enrichment import enrich_portfolio

    out: dict = {"certified": None, "certified_basis": None, "manual_etfs": None, "manual_basis": None,
                 "acorns": None, "acorns_basis": None, "notes": []}
    if transactions is not None and presentation is not None:
        try:
            enriched = enrich_portfolio(derive_portfolio(transactions.list(limit=500, offset=0)), presentation).document()
            out["certified"] = _money(enriched.get("known_market_value") or 0)
            out["certified_basis"] = _money(enriched.get("matched_cost_basis") or enriched.get("known_cost_basis") or 0)
        except ValueError as exc:            # an identity missing from the presentation: leave the part out, say why
            out["notes"].append(f"certified holdings unavailable: {exc}")
    if manual is not None:
        items = manual.current()
        try:
            prices = presentation.etf_latest_prices() if presentation is not None else {}
        except Exception:                    # pricing is best-effort, as on the dashboard
            prices = {}
        docs = mark_to_market([item.document() for item in items], prices or {})
        out["manual_etfs"] = _money(sum((Decimal(d["current_value"]) for d in docs), Decimal(0)))
        out["manual_basis"] = _money(sum((item.cost_basis for item in items), Decimal(0)))
    if external is not None:
        acorns = external.history("acorns", 1)
        if acorns:
            out["acorns"] = _money(acorns[0].current_value)
            out["acorns_basis"] = _money(acorns[0].contributed_basis) if acorns[0].basis_known else None
    parts = [out[k] for k in ("certified", "manual_etfs", "acorns") if out[k] is not None]
    out["total"] = _money(sum((Decimal(p) for p in parts), Decimal(0)))
    return out


def _retirement(external, today: date) -> dict:
    from .external_account_performance import KINDS, estimate, kind_of

    if external is None:
        return {"total": None, "accounts": 0}
    schedules = external.schedules()
    total, count = Decimal(0), 0
    for account in external.accounts():
        if KINDS[kind_of(account)][1] != "retirement":
            continue
        items = external.history(account, 1)
        if not items:
            continue
        total += Decimal(estimate(items[0], schedules.get(account), today)["value"])
        count += 1
    return {"total": _money(total) if count else None, "accounts": count}


def _plan_month(plans, month: str) -> dict | None:
    from .household_plan import roll_forward

    if plans is None:
        return None
    version = plans.current()
    if version is None:
        return None
    rows = roll_forward(version.plan)
    row = next((r for r in rows if r["month"] == month), None)
    if row is None:
        return None
    return {"month": row["month"], "bank": _money(row["bank_balance"]), "house_fund": _money(row["house_fund_balance"]),
            "home_equity": _money(row["home_equity"]), "bank_checked": bool(row.get("bank_check")),
            "plan_version": version.version_id}


def compute_net_worth(*, today: date | None = None, transactions=None, presentation=None, manual=None,
                      external=None, plans=None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    month = today.strftime("%Y-%m")
    investments = _investments(transactions, presentation, manual, external)
    retirement = _retirement(external, today)
    plan = _plan_month(plans, month)
    parts = {"investments": investments["total"], "retirement": retirement["total"],
             "bank": plan["bank"] if plan else None, "house_fund": plan["house_fund"] if plan else None,
             "home_equity": plan["home_equity"] if plan else None}
    worth = sum((Decimal(v) for v in parts.values() if v is not None), Decimal(0))
    return {"month": month, "as_of_date": today.isoformat(), "net_worth": _money(worth), "components": parts,
            "investments": investments, "retirement": retirement, "plan": plan,
            "missing": [k for k, v in parts.items() if v is None], "debts": None}


def plan_ledger_actuals(plans) -> list[dict]:
    """Past months whose plan balances were entered as actuals: a starting history before the first capture."""
    from .household_plan import roll_forward

    version = plans.current() if plans is not None else None
    if version is None:
        return []
    out = []
    for row in roll_forward(version.plan):
        if not row.get("anchored"):
            continue
        parts = {"investments": _money(row["investment_balance"]), "retirement": _money(row["retirement_balance"]),
                 "bank": _money(row["bank_balance"]), "house_fund": _money(row["house_fund_balance"]),
                 "home_equity": _money(row["home_equity"])}
        out.append({"month": row["month"], "as_of_date": f"{row['month']}-28", "net_worth": _money(row["net_worth"]),
                    "components": parts, "missing": [], "debts": None, "plan": {"plan_version": version.version_id}})
    return out


# ---------------------------------------------------------------- history storage
SCHEMA = """CREATE TABLE IF NOT EXISTS net_worth_months (
    month TEXT PRIMARY KEY,
    captured_at TEXT NOT NULL,
    net_worth NUMERIC NOT NULL,
    source TEXT NOT NULL,
    document TEXT NOT NULL
)"""


class NetWorthHistory:
    """One row per month. Works on SQLite (tests, local) and PostgreSQL (hosted) through a DB-API factory."""

    def __init__(self, connection_factory, placeholder: str = "?"):
        self.connection_factory = connection_factory
        self.p = placeholder

    @classmethod
    def from_dsn(cls, dsn: str) -> "NetWorthHistory":
        import psycopg
        return cls(lambda: psycopg.connect(dsn), "%s")

    @classmethod
    def sqlite(cls, path) -> "NetWorthHistory":
        import sqlite3
        return cls(lambda: sqlite3.connect(str(path)), "?")

    def initialize(self) -> None:
        with closing(self.connection_factory()) as db:
            db.cursor().execute(SCHEMA)
            db.commit()

    def months(self) -> list[dict]:
        with closing(self.connection_factory()) as db:
            cur = db.cursor()
            cur.execute("SELECT month, captured_at, net_worth, source, document FROM net_worth_months ORDER BY month")
            rows = cur.fetchall()
        return [{**json.loads(doc), "month": m, "captured_at": at, "net_worth": str(Decimal(str(nw)).quantize(Decimal("0.01"))),
                 "source": src} for m, at, nw, src, doc in rows]

    def record(self, snapshot: dict, *, source: str = "DAILY_CAPTURE", now: datetime | None = None) -> str:
        """Write this month's row. Returns WRITTEN, or FROZEN when the month has already ended and has a row."""
        now = now or datetime.now(timezone.utc)
        month = snapshot["month"]
        p = self.p
        with closing(self.connection_factory()) as db:
            cur = db.cursor()
            cur.execute(f"SELECT month FROM net_worth_months WHERE month={p}", (month,))
            exists = cur.fetchone() is not None
            if exists and month < now.strftime("%Y-%m"):
                return "FROZEN"
            doc = json.dumps({k: v for k, v in snapshot.items() if k not in ("month", "net_worth")}, sort_keys=True, default=str)
            if exists:
                cur.execute(f"UPDATE net_worth_months SET captured_at={p}, net_worth={p}, source={p}, document={p} WHERE month={p}",
                            (now.isoformat(), snapshot["net_worth"], source, doc, month))
            else:
                cur.execute(f"INSERT INTO net_worth_months (month, captured_at, net_worth, source, document) VALUES ({p},{p},{p},{p},{p})",
                            (month, now.isoformat(), snapshot["net_worth"], source, doc))
            db.commit()
        return "WRITTEN"

    def seed(self, rows: list[dict], *, now: datetime | None = None) -> int:
        """Add plan-ledger actuals for months that have no row yet and come before the first captured month."""
        existing = {r["month"]: r for r in self.months()}
        first_capture = min((m for m, r in existing.items() if r["source"] != "PLAN_LEDGER_ACTUALS"), default=None)
        this_month = (now or datetime.now(timezone.utc)).strftime("%Y-%m")
        added = 0
        for row in rows:
            m = row["month"]
            if m in existing or m >= this_month or (first_capture and m >= first_capture):
                continue
            self.record(row, source="PLAN_LEDGER_ACTUALS", now=now)
            added += 1
        return added


def capture(history: NetWorthHistory, **sources) -> dict:
    """Compute today's net worth, seed earlier months from the plan's actuals, and store this month's row."""
    snapshot = compute_net_worth(**sources)
    seeded = history.seed(plan_ledger_actuals(sources.get("plans")))
    status = history.record(snapshot)
    return {"status": status, "seeded_months": seeded, "snapshot": snapshot}
