"""Net worth today and its month-by-month history (synthetic figures only)."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from foundation.production.external_account_performance import SQLiteExternalAccountPerformanceRepository, create_snapshot
from foundation.production.net_worth import NetWorthHistory, capture, compute_net_worth, plan_ledger_actuals

NOW = datetime(2026, 10, 10, 18, 0, tzinfo=timezone.utc)


def month(m, *, bank=None, ret=None, inv=None, check=None):
    return {"month": m, "income": {"Income (Job 1)": 4000.0}, "expenses": {"Rent": -1200.0},
            "investment_contribution": 500.0, "house_fund_contribution": 0.0, "retirement_contribution": 0.0,
            "bank_balance": bank, "retirement_balance": ret, "investment_balance": inv, "house_fund_balance": None,
            "home_equity": None, "bank_check": check}


class Plans:
    def __init__(self):
        self.plan = {"settings": {"plan_investment_return": 0.0, "plan_retirement_return": 0.0},
                     "months": [month("2026-08", bank=5000.0, ret=9000.0, inv=3000.0), month("2026-09", bank=6000.0, ret=9100.0, inv=3500.0),
                                month("2026-10"), month("2026-11")]}

    def current(self):
        return SimpleNamespace(plan=self.plan, version_id="plan-v1")


class Manual:
    def current(self):
        return (SimpleNamespace(cost_basis=Decimal("90"), document=lambda: {"symbol": "VOO", "asset_type": "ETF", "shares": "0.2", "cost_basis": "90",
                                                                             "current_value": "95", "current_price": "475", "as_of": "2026-10-01"}),)


def external(tmp_path):
    repo = SQLiteExternalAccountPerformanceRepository(sqlite3.connect(tmp_path / "ext.sqlite3", check_same_thread=False))
    repo.initialize()
    at = datetime(2026, 10, 9, 12, tzinfo=timezone.utc)
    repo.save(create_snapshot(account_id="acorns", provider="Acorns", as_of=at, current_value=Decimal("1500"), contributed_basis=Decimal("1400"), recorded_by="t"))
    repo.save(create_snapshot(account_id="retirement-401k:plan-a", provider="Plan A", as_of=at, current_value=Decimal("9000"), contributed_basis=Decimal("0"), recorded_by="t"))
    repo.save(create_snapshot(account_id="hsa", provider="HSA", as_of=at, current_value=Decimal("1000"), contributed_basis=Decimal("0"), recorded_by="t"))
    repo.save_schedule("retirement-401k:plan-a", {"per_paycheck": "100", "every_days": 14, "next_paycheck": "2026-10-15"}, "t")
    return repo


def test_net_worth_adds_investments_retirement_and_bank(tmp_path):
    ext = external(tmp_path)
    out = compute_net_worth(today=date(2026, 10, 20), manual=Manual(), external=ext, plans=Plans(), presentation=None)
    assert out["month"] == "2026-10"
    # VOO stays at its entered $95 (no package close), Acorns $1,500
    assert out["investments"]["manual_etfs"] == "95.00" and out["investments"]["acorns"] == "1500.00"
    assert out["components"]["investments"] == "1595.00"
    # retirement: $9,000 + one paycheck (Oct 15) of $100, plus the $1,000 HSA
    assert out["components"]["retirement"] == "10100.00" and out["retirement"]["accounts"] == 2
    # bank rolls forward from September's $6,000 + $2,800 - $500 invested
    assert out["components"]["bank"] == "8300.00"
    assert out["net_worth"] == str(Decimal("1595") + Decimal("10100") + Decimal("8300") + Decimal("0") + Decimal("0")) + ".00"
    assert out["missing"] == []


def test_a_missing_source_is_named_not_guessed():
    out = compute_net_worth(today=date(2026, 10, 20))
    assert out["net_worth"] == "0.00" and set(out["missing"]) == {"retirement", "bank", "house_fund", "home_equity"}


def test_history_refreshes_this_month_freezes_past_months_and_seeds_earlier_actuals(tmp_path):
    history = NetWorthHistory.sqlite(tmp_path / "nw.sqlite3")
    history.initialize()
    snap = {"month": "2026-10", "net_worth": "100.00", "components": {}}
    assert history.record(snap, now=NOW) == "WRITTEN"
    assert history.record({**snap, "net_worth": "150.00"}, now=NOW) == "WRITTEN"
    assert [m["net_worth"] for m in history.months()] == ["150.00"]
    later = datetime(2026, 11, 2, tzinfo=timezone.utc)
    assert history.record({**snap, "net_worth": "999.00"}, now=later) == "FROZEN"
    assert history.months()[0]["net_worth"] == "150.00"
    actuals = plan_ledger_actuals(Plans())
    assert [a["month"] for a in actuals] == ["2026-08", "2026-09"]
    assert history.seed(actuals, now=NOW) == 2
    assert history.seed(actuals, now=NOW) == 0
    months = history.months()
    assert [(m["month"], m["source"]) for m in months] == [("2026-08", "PLAN_LEDGER_ACTUALS"), ("2026-09", "PLAN_LEDGER_ACTUALS"), ("2026-10", "DAILY_CAPTURE")]
    assert months[1]["net_worth"] == "18600.00"           # 6,000 bank + 9,100 retirement + 3,500 investments


def test_capture_and_routes(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from foundation.production.hosted_net_worth import install_net_worth_routes

    history = NetWorthHistory.sqlite(tmp_path / "nw.sqlite3")
    history.initialize()
    settings = SimpleNamespace(credentials={"viewer": ("view-key", ("viewer",)), "operator": ("op-key", ("operator",))})
    app = FastAPI()
    install_net_worth_routes(app, settings, history, external=external(tmp_path), plans=Plans(), manual=Manual())
    client = TestClient(app)
    assert client.get("/v1/net-worth").status_code == 401
    assert client.post("/v1/net-worth/capture", headers={"X-API-Key": "view-key"}).status_code == 403
    body = client.get("/v1/net-worth", headers={"X-API-Key": "view-key"}).json()
    this_month = datetime.now(timezone.utc).strftime("%Y-%m")
    assert body["current"]["month"] == this_month and any(m["month"] == this_month for m in body["months"])
    out = client.post("/v1/net-worth/capture", headers={"X-API-Key": "op-key"}).json()
    assert out["status"] == "WRITTEN"


def test_download_my_data_has_every_entered_record(tmp_path):
    pytest.importorskip("fastapi")
    import json
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from foundation.production.data_export import FORMAT, install_data_export_routes
    from foundation.production.household_plan import SQLiteHouseholdPlanRepository, create_version
    from foundation.production.manual_holdings import SQLiteManualHoldingRepository, create_manual_holding_snapshot
    from foundation.production.transaction_persistence import SQLiteTransactionRepository

    def db(name):
        return sqlite3.connect(tmp_path / name, check_same_thread=False)

    transactions = SQLiteTransactionRepository(db("tx.sqlite3")); transactions.initialize()
    manual = SQLiteManualHoldingRepository(db("manual.sqlite3")); manual.initialize()
    manual.save(create_manual_holding_snapshot(symbol="VOO", asset_name="Vanguard S&P 500", asset_type="ETF", account_id="brokerage",
                                               as_of=datetime(2026, 10, 1, tzinfo=timezone.utc), shares=Decimal("0.2"),
                                               cost_basis=Decimal("90"), current_value=Decimal("95"), recorded_by="t"))
    plans = SQLiteHouseholdPlanRepository(db("plan.sqlite3")); plans.initialize()
    plan = {"income_lines": ["Income (Job 1)"], "expense_lines": ["Rent"], "months": Plans().plan["months"]}
    plans.save(create_version(plan, "t"))
    history = NetWorthHistory.sqlite(tmp_path / "nw.sqlite3"); history.initialize()
    history.record({"month": "2026-10", "net_worth": "100.00", "components": {}}, now=NOW)

    settings = SimpleNamespace(credentials={"viewer": ("view-key", ("viewer",))})
    app = FastAPI()
    install_data_export_routes(app, settings, transactions=transactions, manual=manual, external=external(tmp_path), plans=plans, history=history)
    client = TestClient(app)
    assert client.get("/v1/my-data/export").status_code == 401
    r = client.get("/v1/my-data/export", headers={"X-API-Key": "view-key"})
    assert r.status_code == 200 and r.headers["content-disposition"].startswith('attachment; filename="uip-my-data-')
    doc = json.loads(r.text)
    assert doc["format"] == FORMAT and doc["notes"] == [] and doc["transactions"] == []
    assert doc["manual_holdings"][0]["current"]["symbol"] == "VOO" and len(doc["manual_holdings"][0]["history"]) == 1
    assert set(doc["external_accounts"]["accounts"]) == {"acorns", "hsa", "retirement-401k:plan-a"}
    assert doc["external_accounts"]["schedules"]["retirement-401k:plan-a"]["every_days"] == 14
    assert len(doc["household_plan"]["current"]["plan"]["months"]) == 4 and len(doc["household_plan"]["versions"]) == 1
    assert [m["month"] for m in doc["net_worth_months"]] == ["2026-10"]


def test_homestead_shows_net_worth_history_extends_the_plan_and_downloads_data():
    from pathlib import Path
    page = (Path(__file__).resolve().parents[2] / "foundation/production/dashboard_assets/homestead.js").read_text()
    assert 'call("/v1/net-worth")' in page and 'fetch("/v1/my-data/export"' in page
    assert "Net worth, month by month" in page and "Download my data" in page
    assert "const HORIZON=36;" in page and "data-home-extend" in page
    assert "${netWorth()}${emergency()}${p?goal(p)" in page          # net worth leads the page; the Treasury stays investments only
    assert page.isascii() and "style=" not in page
