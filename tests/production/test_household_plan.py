"""The household plan (Homestead): workbook import, roll-forward, versions, projection and routes.

The workbook here is synthetic: it has the Monthly Tracker's shape and formulas, never real figures.
"""
from __future__ import annotations

import copy
import sqlite3
from datetime import datetime, timezone

import pytest

openpyxl = pytest.importorskip("openpyxl")

from foundation.production import household_plan as H  # noqa: E402
from foundation.production.household_projection import monthly_payment, project  # noqa: E402

HEADERS = ["Month", "Income (Job 1)", "Income (Job 2)", "Total Income", "Rent", "Car", "Total Expenses", "Net Cash Flow",
           "Investment Contribution", "House Fund Contribution", "Net to Bank", "Bank Balance", "Retirement Balance",
           "Investment Balance", "House Fund Balance", "Home Equity", "Net Worth"]


def books(months=6, rate=0.10):
    """A tiny tracker: two anchored months, then rows rolling forward exactly like the real workbook."""
    f, v = openpyxl.Workbook(), openpyxl.Workbook()
    for wb in (f, v):
        ws = wb.active
        ws.title = "Monthly Tracker"
        ws["A1"] = "Monthly Tracker"
        for c, h in enumerate(HEADERS, 1):
            ws.cell(3, c, h)
        planner = wb.create_sheet("Investment Planner")
        planner["C7"] = rate
        house = wb.create_sheet("House Purchase Planner")
        house["C8"], house["C9"], house["C19"], house["C20"] = 0.2, 0.03, 0.065, 30
    F, V = f["Monthly Tracker"], v["Monthly Tracker"]
    bank, ret, inv = 0.0, 0.0, 0.0
    for k in range(months):
        r = 4 + k
        month = f"{['Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb'][k]}-{2026 if k < 6 else 2027}"
        inc1, inc2, rent, car, contrib = 4000.0, 3000.0, -1200.0, -800.0, 2000.0
        net = inc1 + inc2 + rent + car
        for ws in (F, V):
            ws.cell(r, 1, month)
            for c, x in ((2, inc1), (3, inc2), (5, rent), (6, car), (9, contrib)):
                ws.cell(r, c, x)
        if k < 2:                                  # anchored starting points (constants, as typed)
            bank, ret, inv = 5000.0 + k * 100, 9000.0 + k * 50, 3000.0 + k * 25
            formulas = (bank, ret, inv)
        else:
            bank = bank + net - contrib
            ret = ret * (1 + 0.10 / 12) + 550.0 * 2
            inv = inv * (1 + rate / 12) + contrib
            formulas = (f"=L{r - 1}+K{r}", f"=M{r - 1}*(1+(0.1/12))+(300*2)+(250*2)",
                        f"=N{r - 1}*(1+'Investment Planner'!$C$7/12)+I{r}")
        for c, (formula, value) in zip((12, 13, 14), zip(formulas, (bank, ret, inv))):
            F.cell(r, c, formula)
            V.cell(r, c, value)
        V.cell(r, 17, bank + ret + inv)
        F.cell(r, 17, f"=L{r}+M{r}+N{r}+O{r}+P{r}")
    return f, v


def test_import_reproduces_the_workbook_and_marks_anchors():
    plan = H.import_books(*books(), "abc")
    assert plan["income_lines"] == ["Income (Job 1)", "Income (Job 2)"]
    assert plan["expense_lines"] == ["Rent", "Car"]
    assert [m["month"] for m in plan["months"]][:3] == ["2026-07", "2026-08", "2026-09"]
    assert plan["months"][0]["bank_balance"] == 5000 and plan["months"][2]["bank_balance"] is None
    assert plan["months"][3]["retirement_contribution"] == pytest.approx(1100.0, abs=0.01)
    assert plan["source"]["largest_monthly_difference"] <= 0.02
    assert plan["settings"]["plan_investment_return"] == 0.10 and plan["settings"]["mortgage_rate"] == 0.065
    rows = H.roll_forward(plan)
    assert rows[-1]["net_worth"] == pytest.approx(plan["source"]["workbook_end_net_worth"], abs=0.05)


def test_import_refuses_a_workbook_it_cannot_reproduce():
    f, v = books()
    v["Monthly Tracker"].cell(9, 17, 999999)        # Net Worth that the formulas do not produce
    with pytest.raises(H.HouseholdPlanError, match="differs from the workbook"):
        H.import_books(f, v, "abc")
    with pytest.raises(H.HouseholdPlanError, match="readable"):
        H.import_workbook(b"not a workbook")


def test_validation_rejects_bad_plans():
    plan = H.import_books(*books(), "abc")
    for change, message in (({"target_month": "2029-13"}, "target_month"), ({"contribution_mix": {"stocks": 0.5}}, "100%"),
                            ({"contribution_mix": {"gold": 1}}, "unknown"), ({"home_price_high": 1}, "at least")):
        bad = copy.deepcopy(plan)
        bad["settings"].update(change)
        with pytest.raises(H.HouseholdPlanError, match=message):
            H.normalize_plan(bad)
    bad = copy.deepcopy(plan)
    bad["months"].append(dict(bad["months"][0]))
    with pytest.raises(H.HouseholdPlanError, match="twice"):
        H.normalize_plan(bad)


def test_an_entered_actual_replaces_the_rolled_balance():
    plan = H.import_books(*books(), "abc")
    plan["months"][3]["bank_balance"] = 1234.0
    rows = H.roll_forward(H.normalize_plan(plan))
    assert rows[3]["bank_balance"] == 1234.0 and "bank_balance" in rows[3]["anchored"]
    assert rows[4]["bank_balance"] == pytest.approx(1234.0 + rows[4]["net_to_bank"])


def test_versions_are_immutable_and_identical_saves_are_not_duplicated():
    repo = H.SQLiteHouseholdPlanRepository(sqlite3.connect(":memory:"))
    repo.initialize()
    plan = H.import_books(*books(), "abc")
    first = repo.save(H.create_version(plan, "operator", datetime(2026, 10, 7, 12, tzinfo=timezone.utc)))
    again = repo.save(H.create_version(plan, "operator", datetime(2026, 10, 7, 13, tzinfo=timezone.utc)))
    assert again.version_id == first.version_id
    plan["settings"]["home_price_low"] = 360000
    second = repo.save(H.create_version(plan, "operator", datetime(2026, 10, 8, tzinfo=timezone.utc)))
    assert repo.current().version_id == second.version_id
    assert [v.version_id for v in repo.history()] == [second.version_id, first.version_id]


def test_projection_ranges_house_goal_and_live_holdings():
    plan = H.import_books(*books(months=8), "abc")
    plan["settings"]["target_month"] = "2027-02"
    result = project(plan, as_of_month="2026-09", holdings={"etf": 1000, "crypto": 500, "mtg": 400})
    assert result["starting_investments_source"] == "LIVE_UIP_HOLDINGS" and result["starting_investments"] == 1900
    assert result["start_month"] == "2026-09" and result["target_month"] == "2027-02"
    t = result["target"]["net_worth"]
    assert t["p10"] < t["p50"] < t["p90"]
    assert result["safety_fund"] == pytest.approx(6 * 2000)
    need = result["house"]["need_low"]
    assert need == pytest.approx(350000 * 0.23 + 12000)
    assert all(0 <= c["chance"] <= 1 for c in result["house"]["chances"])
    assert result["house"]["capacity"][0]["twenty_pct_payment"] == monthly_payment(280000, 0.065, 30)
    again = project(plan, as_of_month="2026-09", holdings={"etf": 1000, "crypto": 500, "mtg": 400})
    assert again["target"] == result["target"]                     # seeded: the same plan gives the same ranges
    assert "Taxes on gains are not included; MTG is counted after about 12% selling costs." in result["limitations"]
    with pytest.raises(ValueError, match="unknown holding"):
        project(plan, as_of_month="2026-09", holdings={"stamps": 10})


def test_retirement_statements_start_the_retirement_balance_and_never_join_the_investments():
    plan = H.import_books(*books(months=8), "abc")
    plan["settings"]["target_month"] = "2027-02"
    base = project(plan, as_of_month="2026-09", holdings={"etf": 1000})
    assert base["starting_retirement_source"] == "PLAN_BALANCE"
    out = project(plan, as_of_month="2026-09", holdings={"etf": 1000, "retirement": 50000})
    assert out["starting_retirement_source"] == "RETIREMENT_STATEMENTS" and out["starting_retirement"] == 50000
    assert out["starting_investments"] == 1000 and "retirement" not in out["starting_by_sleeve"]
    assert out["target_by_sleeve_median"]["retirement"] > 50000 * 0.9
    assert out["house"]["need_low"] == base["house"]["need_low"]          # house money unchanged: retirement is not counted


def test_retirement_is_left_out_of_house_money_by_default():
    plan = H.import_books(*books(months=8), "abc")
    plan["settings"]["target_month"] = "2027-02"
    out = project(plan, as_of_month="2026-09")
    plan["settings"]["house_counts_retirement"] = True
    inc = project(H.normalize_plan(plan), as_of_month="2026-09")
    assert inc["target"]["house_usable"]["p50"] > out["target"]["house_usable"]["p50"] + 9000


def test_payment_formula():
    assert monthly_payment(280000, 0.065, 30) == pytest.approx(1769.79, abs=0.01)
    assert monthly_payment(0, 0.065, 30) == 0


pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from foundation.production.hosted_household_plan import install_household_plan_routes  # noqa: E402
from foundation.production.http_service import HTTPServiceSettings, create_http_app  # noqa: E402
from foundation.production.persistence import SQLiteProductionRepository  # noqa: E402


def client(tmp_path):
    production = SQLiteProductionRepository(tmp_path / "production.sqlite3")
    production.initialize()
    settings = HTTPServiceSettings(credentials={"viewer": ("view-key", ("viewer",)), "operator": ("operate-key", ("operator",))})
    app = create_http_app(settings, production)
    repo = H.SQLiteHouseholdPlanRepository(sqlite3.connect(":memory:", check_same_thread=False))
    repo.initialize()
    install_household_plan_routes(app, settings, repo)
    return TestClient(app), repo


def workbook_bytes(tmp_path):
    f, _ = books()
    path = tmp_path / "tracker.xlsx"
    f.save(path)
    return path.read_bytes()


def test_routes_require_keys_and_the_operator_to_write(tmp_path):
    api, _ = client(tmp_path)
    assert api.get("/v1/household-plan").status_code == 401
    assert api.get("/v1/household-plan", headers={"X-API-Key": "view-key"}).json() == {"available": False}
    plan = H.import_books(*books(), "abc")
    assert api.post("/v1/household-plan", json={"plan": plan}, headers={"X-API-Key": "view-key"}).status_code == 403
    saved = api.post("/v1/household-plan", json={"plan": plan}, headers={"X-API-Key": "operate-key"})
    assert saved.status_code == 201
    read = api.get("/v1/household-plan", headers={"X-API-Key": "view-key"}).json()
    assert read["available"] and read["rows"][-1]["net_worth"] == saved.json()["rows"][-1]["net_worth"]
    bad = api.post("/v1/household-plan", json={"plan": {"months": []}}, headers={"X-API-Key": "operate-key"})
    assert bad.status_code == 422


def test_import_preview_saves_nothing(tmp_path):
    api, repo = client(tmp_path)
    # openpyxl-written files carry no saved values, so the formulas cannot be checked: the import refuses.
    refused = api.post("/v1/household-plan/import", content=workbook_bytes(tmp_path), headers={"X-API-Key": "operate-key"})
    assert refused.status_code == 422
    assert api.post("/v1/household-plan/import", content=b"", headers={"X-API-Key": "operate-key"}).status_code == 422
    assert api.post("/v1/household-plan/import", content=b"x", headers={"X-API-Key": "view-key"}).status_code == 403
    assert repo.current() is None


def test_projection_route_uses_the_saved_plan_and_live_holdings(tmp_path):
    api, _ = client(tmp_path)
    plan = H.import_books(*books(months=8), "abc")
    plan["settings"]["target_month"] = "2027-02"
    api.post("/v1/household-plan", json={"plan": plan}, headers={"X-API-Key": "operate-key"})
    out = api.post("/v1/household-plan/projection", json={"as_of_month": "2026-09", "holdings": {"etf": 1000}},
                   headers={"X-API-Key": "view-key"}).json()
    assert out["available"] and out["starting_investments"] == 1000
    tried = api.post("/v1/household-plan/projection", json={"as_of_month": "2026-09", "settings": {"home_price_low": 300000}},
                     headers={"X-API-Key": "view-key"}).json()
    assert tried["house"]["price_low"] == 300000
    assert api.post("/v1/household-plan/projection", json={}, headers={}).status_code == 401


def test_home_prices_grow_to_the_target_month():
    plan = H.import_books(*books(months=8), "abc")
    plan["settings"]["target_month"] = "2027-02"
    flat = project(H.normalize_plan(plan), as_of_month="2026-08")
    plan["settings"]["home_price_growth"] = 0.03
    grown = project(H.normalize_plan(plan), as_of_month="2026-08")
    years = 6 / 12
    assert grown["house"]["price_low_at_target"] == pytest.approx(350000 * 1.03 ** years, abs=0.01)
    assert grown["house"]["need_low"] > flat["house"]["need_low"]
    assert grown["house"]["capacity"][0]["price"] == 350000 and grown["house"]["capacity"][0]["price_at_target"] > 350000
    with pytest.raises(H.HouseholdPlanError, match="home_price_growth"):
        plan["settings"]["home_price_growth"] = 0.9
        H.normalize_plan(plan)


def test_a_bank_check_in_projects_the_month_end_from_what_is_still_to_come():
    plan = H.import_books(*books(), "abc")
    m = plan["months"][3]                                  # Oct 2026: +4000 +3000, rent -1200, car -800, invest 2000
    inc1, inc2 = plan["income_lines"]
    m["bank_check"] = {"balance": 2500.0, "as_of": "2026-10-08", "done": [f"income:{inc1}", "expenses:Car"]}
    rows = H.roll_forward(H.normalize_plan(plan))
    # still to come: job 2 pay +3000, rent -1200, the 2000 investment transfer
    assert rows[3]["bank_balance"] == pytest.approx(2500 + 3000 - 1200 - 2000)
    assert rows[3]["bank_check"] == {"as_of": "2026-10-08", "balance": 2500.0, "still_to_come": -200.0}
    assert rows[4]["bank_balance"] == pytest.approx(rows[3]["bank_balance"] + rows[4]["net_to_bank"])
    # a lower car payment counts once it is still to come
    m["bank_check"]["done"] = [f"income:{inc1}"]
    m["expenses"]["Car"] = -500.0
    assert H.roll_forward(H.normalize_plan(plan))[3]["bank_balance"] == pytest.approx(2500 + 3000 - 1200 - 500 - 2000)
    # an entered month-end balance still wins
    m["bank_balance"] = 999.0
    row = H.roll_forward(H.normalize_plan(plan))[3]
    assert row["bank_balance"] == 999.0 and row["bank_check"] is None


@pytest.mark.parametrize("check,message", [
    ({"as_of": "2026-10-08"}, "needs a balance"),
    ({"balance": 1, "as_of": "2026-11-01"}, "day in that month"),
    ({"balance": 1, "as_of": "2026-10-08", "done": ["expenses:Boat"]}, "unknown line"),
])
def test_bad_bank_check_ins_are_refused(check, message):
    plan = H.import_books(*books(), "abc")
    plan["months"][3]["bank_check"] = check
    with pytest.raises(H.HouseholdPlanError, match=message):
        H.normalize_plan(plan)
