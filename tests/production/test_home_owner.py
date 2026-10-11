"""Owner mode: a sample purchase (synthetic figures only)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from foundation.production.home_owner import HomeError, balance_at, home_status, normalize_home, payment, schedule, value_at

SAMPLE = {"market": "Wichita", "price": 250000, "closing_month": "2030-03", "down_payment": 25000, "closing_costs": 7000,
          "loan_amount": 225000, "rate": 0.06, "term_years": 30, "pmi_monthly": 95, "escrow_monthly": 380,
          "hoa_monthly": 20, "hpi_at_closing": 500}


def home(**over):
    return normalize_home({**SAMPLE, **over})


def test_purchase_is_validated():
    assert normalize_home(None) is None
    for bad in ({"market": "Paris"}, {"loan_amount": 300000}, {"closing_month": "spring"}, {"rate": 0.9}, {"price": 0}):
        with pytest.raises(HomeError):
            normalize_home({**SAMPLE, **bad})


def test_the_loan_follows_its_schedule_extra_principal_and_statements():
    h = home()
    pay = payment(225000, 0.06, 30)
    assert pay == pytest.approx(1348.99, abs=0.01)
    rows = schedule(h)
    assert len(rows) == 360 and rows[-1]["balance"] == 0 and rows[0]["month"] == "2030-04"
    assert rows[0]["interest"] == pytest.approx(1125.00) and rows[0]["principal"] == pytest.approx(pay - 1125, abs=0.01)
    plain = balance_at(h, "2032-03")
    extra = balance_at(home(extra_payments=[{"month": "2031-01", "amount": 5000}]), "2032-03")
    assert plain - extra > 5000                                   # the extra plus the interest it no longer accrues
    stated = home(statements=[{"month": "2031-06", "balance": 210000}])
    assert balance_at(stated, "2031-06") == 210000 and balance_at(stated, "2031-07") < 210000


def test_value_moves_with_the_index_and_an_appraisal_wins():
    assert value_at(home(), 550) == (275000.0, "PRICE_X_HPI")
    assert value_at(home(), None) == (250000.0, "PRICE")
    appraised = home(appraisals=[{"month": "2032-01", "value": 270000, "hpi": 540}])
    assert value_at(appraised, 567) == (283500.0, "APPRAISAL_X_HPI")


def test_owner_checks():
    out = home_status(home(), as_of_month="2032-03", hpi_now=525, rate_now=0.045, keep_until="2040-01")
    assert out["value"] == 262500.0 and out["equity"] == pytest.approx(out["value"] - out["loan_balance"])
    assert out["payment"]["total"] == pytest.approx(1348.99 + 95 + 380 + 20, abs=0.01)
    pmi = out["pmi"]
    assert pmi["request_month"] < pmi["automatic_month"]          # 80% on request comes before 78% automatically
    assert balance_at(home(), pmi["request_month"]) <= 0.80 * 250000 < balance_at(home(), "2032-03")
    r = out["refinance"]
    assert r["monthly_saving"] > 0 and r["break_even_months"] == -(-r["costs"] // r["monthly_saving"])
    assert r["worth_a_look"] is (r["break_even_months"] < r["keep_months"])
    no = home_status(home(), as_of_month="2032-03", rate_now=0.07)["refinance"]
    assert no["monthly_saving"] < 0 and no["worth_a_look"] is False
    x = out["extra_principal"]
    assert x["interest_saved"] > 0 and x["months_sooner"] > 0
    assert out["maintenance_year"] == [2625.0, 5250.0]


def test_owner_mode_route_previews_and_feeds_net_worth_and_retirement(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from foundation.production.hosted_household_plan import install_household_plan_routes
    from foundation.production.household_plan import SQLiteHouseholdPlanRepository, create_version, normalize_plan
    from foundation.production.net_worth import compute_net_worth
    from foundation.production.retirement_path import retirement_path
    from tests.production.test_retirement_path import RET, plan as ret_plan

    base = ret_plan(RET)
    repo = SQLiteHouseholdPlanRepository(sqlite3.connect(tmp_path / "p.sqlite3", check_same_thread=False))
    repo.initialize()
    repo.save(create_version(base, "t", datetime(2026, 10, 1, tzinfo=timezone.utc)))
    app = FastAPI()
    install_household_plan_routes(app, SimpleNamespace(credentials={"viewer": ("view-key", ("viewer",))}), repo)
    client = TestClient(app)
    h = {"X-API-Key": "view-key"}
    assert client.post("/v1/household-plan/home", json={}, headers=h).json() == {"available": True, "owned": False}
    out = client.post("/v1/household-plan/home", headers=h, json={"as_of_month": "2031-03", "hpi_now": 510, "home": SAMPLE}).json()
    assert out["preview"] is True and out["value"] == 255000.0
    assert client.post("/v1/household-plan/home", headers=h, json={"home": {**SAMPLE, "rate": "x"}}).status_code == 422

    owned_plan = normalize_plan({**base, "settings": {**base["settings"], "home": SAMPLE}})
    plans = SimpleNamespace(current=lambda: SimpleNamespace(plan=owned_plan, version_id="v"))
    presentation = SimpleNamespace(housing=lambda: {"markets": [{"market": "Wichita", "hpi": 520}]},
                                   etf_latest_prices=lambda: {})
    nw = compute_net_worth(today=datetime(2031, 3, 15).date(), plans=plans, presentation=presentation)
    assert nw["home"]["value"] == "260000.00"
    assert nw["components"]["home_equity"] == nw["home"]["equity"]
    before = compute_net_worth(today=datetime(2029, 1, 15).date(), plans=plans, presentation=presentation)
    assert before["home"] is None                                 # nothing owned before closing

    path = retirement_path(owned_plan, as_of_month="2031-03", holdings={"etf": 9000}, home_value=260000)
    assert path["house"] is None and path["other_sell_home"]["home_proceeds"] == pytest.approx(
        260000 * 0.94 - balance_at(normalize_home(SAMPLE), path["retire_month"]), abs=0.01)
