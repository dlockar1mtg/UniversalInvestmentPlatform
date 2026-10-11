"""The early-retirement path (synthetic figures only; never the owner's)."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from foundation.production.household_plan import HouseholdPlanError, normalize_plan, normalize_retirement
from foundation.production.retirement_path import load_rules, match_check, retirement_path


def plan(retirement=None, months=30):
    rows = []
    for i in range(months):
        y, m = 2026 + (9 + i) // 12, (9 + i) % 12 + 1
        rows.append({"month": f"{y}-{m:02d}", "income": {"Pay": 7000}, "expenses": {"Rent": -1200, "Food": -600},
                     "investment_contribution": 2000, "house_fund_contribution": 800, "retirement_contribution": 0,
                     "bank_balance": 6000.0 if i == 0 else None, "investment_balance": 15000.0 if i == 0 else None})
    settings = {"target_month": "2028-06"}
    if retirement is not None:
        settings["retirement"] = retirement
    return normalize_plan({"income_lines": ["Pay"], "expense_lines": ["Rent", "Food"], "months": rows, "settings": settings})


RET = {"age": 30, "age_as_of": "2026-10", "retire_age": 50, "spending_abroad_year": 20000,
       "jobs": [{"label": "Day job", "account_id": "retirement-401k:a", "salary": 65000, "match_pct": 0.03}]}


def test_retirement_inputs_are_validated_and_optional():
    assert plan()["settings"]["retirement"] is None
    out = normalize_retirement(RET)
    assert out["withdrawal_rate"] == 0.035 and out["inflation"] == 0.025 and out["jobs"][0]["you_pct"] is None
    for bad in ({**RET, "age_as_of": "soon"}, {**RET, "retire_age": 12}, {**RET, "withdrawal_rate": 0},
                {**RET, "jobs": [{"salary": 1, "match_pct": 3}]}):
        with pytest.raises(HouseholdPlanError):
            normalize_retirement(bad)


def test_not_set_up_says_so():
    assert retirement_path(plan(), as_of_month="2026-10") == {"configured": False}


def test_path_has_the_bridge_the_number_and_the_cases():
    out = retirement_path(plan(RET), as_of_month="2026-10", holdings={"etf": 9000, "crypto": 1000},
                          retirement_start=5000, retirement_monthly=500,
                          deposits={"retirement-401k:a": {"per_paycheck": 250, "every_days": 14}})
    assert out["configured"] and out["retire_month"] == "2046-10" and out["access_month"] == "2056-04"
    assert out["spending_year"] == 21600.0                       # blank spending = 12 x this month's bills
    assert out["fi_number"] == pytest.approx(21600 / 0.035, abs=0.01) and out["bridge_need"] == pytest.approx(21600 * 9.5)
    assert out["after_plan_monthly_investing"] == 2800.0         # investing + house fund once the plan ends
    assert out["house"]["month"] == "2028-06" and out["house"]["from_investments"] >= 0
    assert 0 <= out["chance"] <= 1 and [c["case"] for c in out["cases"]] == ["home", "abroad"]
    assert out["cases"][1]["chance"] >= out["chance"]            # spending less abroad never lowers the chance
    ages = [row["age"] for row in out["by_age"]]
    assert ages[0] == 30 and ages[-1] == 95
    assert out["at_retirement"]["age"] == 50
    again = retirement_path(plan(RET), as_of_month="2026-10", holdings={"etf": 9000, "crypto": 1000},
                            retirement_start=5000, retirement_monthly=500)
    assert again["chance"] == out["chance"]                      # the same markets every time


def test_retiring_later_or_saving_more_helps():
    base = retirement_path(plan({**RET, "retire_age": 45}), as_of_month="2026-10", holdings={"etf": 9000})
    later = retirement_path(plan({**RET, "retire_age": 58}), as_of_month="2026-10", holdings={"etf": 9000})
    assert later["chance"] >= base["chance"]
    case = base["cases"][0]
    if base["chance"] < base["on_track_threshold"]:
        assert case["extra_monthly_for_target"] is None or case["extra_monthly_for_target"] > 0
        assert case["earliest_age"] is None or case["earliest_age"] > 45


def test_match_check_reads_the_deposits_and_the_shared_limit():
    rules = load_rules()
    assert rules["employee_deferral_limit"] == 24500 and rules["year"] == 2026
    jobs = [{"label": "A", "account_id": "a", "salary": 52000, "bonus": 0, "match_pct": 0.03, "you_pct": None},
            {"label": "B", "account_id": None, "salary": 40000, "bonus": 0, "match_pct": 0.05, "you_pct": 0.02}]
    out = match_check(jobs, {"a": {"per_paycheck": 200, "every_days": 14}}, rules)
    a, b = out["jobs"]
    assert a["you_pct_inferred"] and a["deposit_pct_of_pay"] == pytest.approx(200 * 365 / 14 / 52000, abs=1e-4)
    assert a["full_match"] is True                                # 10.0% in all, 3% of it the match
    assert b["full_match"] is False and b["match_missed_year"] == pytest.approx(1200.0)
    assert out["room_left_year"] == pytest.approx(24500 - a["employee_year"] - 800, abs=0.01)


def test_route_runs_the_path_and_tries_unsaved_inputs(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from foundation.production.hosted_household_plan import install_household_plan_routes
    from foundation.production.household_plan import SQLiteHouseholdPlanRepository, create_version

    repo = SQLiteHouseholdPlanRepository(sqlite3.connect(tmp_path / "p.sqlite3", check_same_thread=False))
    repo.initialize()
    repo.save(create_version(plan(), "t", datetime(2026, 10, 1, tzinfo=timezone.utc)))
    app = FastAPI()
    install_household_plan_routes(app, SimpleNamespace(credentials={"viewer": ("view-key", ("viewer",))}), repo)
    client = TestClient(app)
    assert client.post("/v1/household-plan/retirement-path", json={}).status_code == 401
    h = {"X-API-Key": "view-key"}
    assert client.post("/v1/household-plan/retirement-path", json={"as_of_month": "2026-10"}, headers=h).json()["configured"] is False
    out = client.post("/v1/household-plan/retirement-path", headers=h,
                      json={"as_of_month": "2026-10", "retirement": RET, "holdings": {"etf": 9000}}).json()
    assert out["available"] and out["configured"] and out["retire_age"] == 50
    bad = client.post("/v1/household-plan/retirement-path", headers=h, json={"retirement": {**RET, "age_as_of": "x"}})
    assert bad.status_code == 422


def test_homestead_shows_the_retirement_path():
    from pathlib import Path
    page = (Path(__file__).resolve().parents[2] / "foundation/production/dashboard_assets/homestead.js").read_text()
    assert 'post("/v1/household-plan/retirement-path"' in page and "The road to early retirement" in page
    assert "${retirementSection()}${purse()}" in page and "data-ret-keep" in page
    assert "Reaching the money before 59" in page
    assert page.isascii() and "style=" not in page
