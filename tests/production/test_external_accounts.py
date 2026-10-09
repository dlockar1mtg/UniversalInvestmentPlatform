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
    with pytest.raises(ValueError, match="unknown account"):
        snap(account_id="ira")
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
    assert [a["account_id"] for a in s["accounts"]] == list(E.ACCOUNTS)
    assert Decimal(s["retirement_value"]) == Decimal("1200.50") and s["retirement_accounts_entered"] == 2
    one = api.get("/v1/external-accounts/performance?account_id=retirement-401k", headers=VIEW).json()
    assert one["account_label"] == "401(k) / 403(b)" and one["items"][0]["current_value"] == "1000.50"
    # The Acorns read stays the default, as the dashboard already uses it.
    assert api.get("/v1/external-accounts/performance", headers=VIEW).json()["items"][0]["account_id"] == "acorns"


@pytest.mark.parametrize("change", [{"account_id": "ira"}, {"current_value": "-5"}, {"current_value": "NaN"},
                                    {"as_of": "2026-09-30"}, {"provider": "x" * 81}])
def test_bad_statements_are_refused(tmp_path, change):
    api = client(tmp_path)
    body = {"account_id": "pension", "as_of": "2026-09-30T12:00:00Z", "current_value": "10", **change}
    assert api.post("/v1/external-accounts/performance", json=body, headers=OPERATE).status_code == 422
    assert api.get("/v1/external-accounts/performance?account_id=ira", headers=VIEW).status_code == 422
