"""Manual external accounts: Acorns snapshots and retirement statements (401(k)/403(b), HSA, pension).
Synthetic values only."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from foundation.production import external_account_performance as E

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from foundation.production.hosted_external_accounts import install_external_account_performance_routes  # noqa: E402
from foundation.production.http_service import HTTPServiceSettings, create_http_app  # noqa: E402
from foundation.production.persistence import SQLiteProductionRepository  # noqa: E402

VIEW, OPERATE = {"X-API-Key": "view-key"}, {"X-API-Key": "operate-key"}


def snap(**changes):
    kw = dict(account_id="retirement-401k", provider="Plan record-keeper", as_of=datetime(2026, 9, 30, 12, tzinfo=timezone.utc),
              current_value=Decimal("1000"), contributed_basis=Decimal("800"), recorded_by="operator")
    kw.update(changes)
    return E.create_snapshot(**kw)


def test_registry_accepts_retirement_accounts_and_keeps_acorns_rules():
    doc = snap().document()
    assert doc["account_label"] == "401(k) / 403(b)" and doc["category"] == "retirement"
    assert doc["gain_loss"] == "200" and doc["basis_known"] is True
    assert snap(account_id="hsa", provider="HSA").document()["category"] == "retirement"
    assert snap(account_id="acorns", provider="Acorns").document()["category"] == "brokerage"
    assert snap(account_id="ira:rollover-1", provider="Rollover IRA").document()["account_kind"] == "ira"
    for bad in ("roth", "acorns:x", "hsa:", "retirement-401k:Bad Name", "retirement-401k:" + "a" * 41):
        with pytest.raises(ValueError, match="unknown account"):
            snap(account_id=bad)
    with pytest.raises(ValueError, match="provider is Acorns"):
        snap(account_id="acorns", provider="Other")
    with pytest.raises(ValueError, match="provider"):
        snap(provider="  ")


def test_a_statement_without_contributions_has_no_gain_or_return():
    doc = snap(account_id="pension", provider="Pension", contributed_basis=Decimal("0")).document()
    assert doc["basis_known"] is False and doc["gain_loss"] is None and doc["return_pct"] is None
    # Acorns keeps its old meaning: a zero basis is a real basis.
    assert snap(account_id="acorns", provider="Acorns", contributed_basis=Decimal("0")).document()["gain_loss"] == "1000"


def client(tmp_path):
    production = SQLiteProductionRepository(tmp_path / "production.sqlite3")
    production.initialize()
    settings = HTTPServiceSettings(credentials={"viewer": ("view-key", ("viewer",)), "operator": ("operate-key", ("operator",))})
    app = create_http_app(settings, production)
    repo = E.SQLiteExternalAccountPerformanceRepository(sqlite3.connect(":memory:", check_same_thread=False))
    repo.initialize()
    install_external_account_performance_routes(app, settings, repo)
    return TestClient(app)


def test_routes_record_statements_and_summarize_every_account(tmp_path):
    api = client(tmp_path)
    assert api.get("/v1/external-accounts/summary").status_code == 401
    body = {"account_id": "retirement-401k", "provider": "Plan record-keeper", "as_of": "2026-09-30T12:00:00Z",
            "current_value": "1000.50", "contributed_basis": "800"}
    assert api.post("/v1/external-accounts/performance", json=body, headers=VIEW).status_code == 403
    saved = api.post("/v1/external-accounts/performance", json=body, headers=OPERATE)
    assert saved.status_code == 201 and saved.json()["created"] is True
    again = api.post("/v1/external-accounts/performance", json=body, headers=OPERATE)
    assert again.json()["created"] is False
    hsa = api.post("/v1/external-accounts/performance", headers=OPERATE,
                   json={"account_id": "hsa", "as_of": "2026-09-30T12:00:00Z", "current_value": "200"})
    assert hsa.status_code == 201 and hsa.json()["snapshot"]["provider"] == "HSA" and hsa.json()["snapshot"]["basis_known"] is False
    api.post("/v1/external-accounts/performance", headers=OPERATE,
             json={"account_id": "acorns", "as_of": "2026-09-30T12:00:00Z", "current_value": "50", "contributed_basis": "40"})
    s = api.get("/v1/external-accounts/summary", headers=VIEW).json()
    assert [a["account_id"] for a in s["accounts"]] == ["acorns", "retirement-401k", "hsa"]
    assert Decimal(s["retirement_value"]) == Decimal("1200.50") and s["retirement_accounts_entered"] == 2
    one = api.get("/v1/external-accounts/performance?account_id=retirement-401k", headers=VIEW).json()
    assert one["account_label"] == "401(k) / 403(b)" and one["items"][0]["current_value"] == "1000.50"
    # The Acorns read stays the default, as the dashboard already uses it.
    assert api.get("/v1/external-accounts/performance", headers=VIEW).json()["items"][0]["account_id"] == "acorns"


@pytest.mark.parametrize("change", [{"account_id": "roth"}, {"current_value": "-5"}, {"current_value": "NaN"},
                                    {"as_of": "2026-09-30"}, {"provider": "x" * 81}])
def test_bad_statements_are_refused(tmp_path, change):
    api = client(tmp_path)
    body = {"account_id": "pension", "as_of": "2026-09-30T12:00:00Z", "current_value": "10", **change}
    assert api.post("/v1/external-accounts/performance", json=body, headers=OPERATE).status_code == 422
    assert api.get("/v1/external-accounts/performance?account_id=roth", headers=VIEW).status_code == 422


def test_paychecks_between_counts_paydays_on_the_schedule():
    from datetime import date
    nxt = date(2026, 10, 15)
    assert E.paychecks_between(date(2026, 10, 9), date(2026, 10, 14), nxt, 14) == 0
    assert E.paychecks_between(date(2026, 10, 9), date(2026, 10, 15), nxt, 14) == 1
    assert E.paychecks_between(date(2026, 10, 9), date(2026, 11, 12), nxt, 14) == 3      # Oct 15, Oct 29, Nov 12
    assert E.paychecks_between(date(2026, 9, 30), date(2026, 10, 9), nxt, 14) == 1       # Oct 1 already passed
    assert E.paychecks_between(date(2026, 10, 15), date(2026, 10, 15), nxt, 14) == 0     # a statement on payday includes it
    assert E.monthly_equivalent("100", 14) == "217.41"


def test_several_accounts_of_one_kind_with_paychecks_estimate_today(tmp_path):
    api = client(tmp_path)
    post = lambda body: api.post("/v1/external-accounts/performance", headers=OPERATE, json={"as_of": "2026-10-09T12:00:00Z", **body})
    assert post({"account_id": "retirement-401k:plan-a", "provider": "Plan A", "current_value": "1000"}).status_code == 201
    assert post({"account_id": "retirement-401k:plan-b", "provider": "Plan B", "current_value": "500", "contributed_basis": "400"}).status_code == 201
    assert post({"account_id": "ira:old", "provider": "Old IRA", "current_value": "3.50"}).status_code == 201
    put = lambda body, key=OPERATE: api.put("/v1/external-accounts/schedule", headers=key, json=body)
    assert put({"account_id": "retirement-401k:plan-a", "per_paycheck": "100", "next_paycheck": "2026-10-15"}, VIEW).status_code == 403
    assert put({"account_id": "retirement-401k:plan-a", "per_paycheck": "100", "next_paycheck": "2026-10-15"}).status_code == 200
    assert put({"account_id": "retirement-401k:plan-b", "per_paycheck": "50", "every_days": 14, "next_paycheck": "2026-10-16"}).status_code == 200
    assert put({"account_id": "retirement-401k:nobody", "per_paycheck": "50", "next_paycheck": "2026-10-16"}).status_code == 422
    assert put({"account_id": "acorns", "per_paycheck": "50", "next_paycheck": "2026-10-16"}).status_code == 422
    assert put({"account_id": "ira:old", "per_paycheck": "-1", "next_paycheck": "2026-10-16"}).status_code == 422
    assert put({"account_id": "ira:old", "per_paycheck": "5", "every_days": 3, "next_paycheck": "2026-10-16"}).status_code == 422
    today = api.get("/v1/external-accounts/summary?today=2026-10-09", headers=VIEW).json()
    assert Decimal(today["retirement_value"]) == Decimal("1503.50") == Decimal(today["retirement_statement_value"])
    later = api.get("/v1/external-accounts/summary?today=2026-10-30", headers=VIEW).json()
    by = {a["account_id"]: a for a in later["accounts"]}
    assert by["retirement-401k:plan-a"]["estimate"]["paychecks_since"] == 2 and by["retirement-401k:plan-a"]["estimate"]["value"] == "1200"
    assert by["retirement-401k:plan-a"]["estimate"]["basis"] is None                     # contributions never entered
    assert by["retirement-401k:plan-b"]["estimate"]["value"] == "600" and by["retirement-401k:plan-b"]["estimate"]["basis"] == "500"
    assert by["retirement-401k:plan-a"]["schedule"]["monthly_equivalent"] == "217.41" and by["ira:old"]["schedule"] is None
    assert by["retirement-401k:plan-b"]["name"] == "Plan B"
    assert Decimal(later["retirement_value"]) == Decimal("1803.50") and later["retirement_accounts_entered"] == 3
    assert put({"account_id": "retirement-401k:plan-a", "clear": True}).status_code == 200
    again = api.get("/v1/external-accounts/summary?today=2026-10-30", headers=VIEW).json()
    assert {a["account_id"]: a for a in again["accounts"]}["retirement-401k:plan-a"]["schedule"] is None
