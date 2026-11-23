"""Sealed MTG held as manual holdings (asset_type MTG_SEALED), priced from TCGCSV. Synthetic data only."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
import sqlite3
from types import SimpleNamespace

import pytest

from foundation.production.hosted_manual_holdings import mark_to_market
from foundation.production.manual_holdings import SQLiteManualHoldingRepository, create_manual_holding_snapshot
from foundation.production.mtg_sealed import (
    SealedError,
    find_group,
    refresh_sealed_prices,
    sealed_prices,
    tcgplayer_product_id,
)
from foundation.production.mtg_singles import SinglesRepository

NOW = datetime(2026, 11, 23, 14, tzinfo=timezone.utc)


def fake_tcgcsv(calls: list[str]):
    data = {
        "groups": {"results": [{"groupId": 100, "publishedOn": "2020-01-01"}, {"groupId": 200, "publishedOn": "2026-03-01"}]},
        "200/products": {"results": [{"productId": 111, "name": "Synthetic Set - Play Booster Display"}]},
        "100/products": {"results": [{"productId": 222, "name": "Old Set - Booster Box"}]},
        "200/prices": {"results": [{"productId": 111, "subTypeName": "Normal", "marketPrice": 101.5, "lowPrice": 90}]},
        "100/prices": {"results": [{"productId": 222, "subTypeName": "Normal", "marketPrice": None, "midPrice": 55.25}]},
    }

    def fetch(path: str) -> dict:
        calls.append(path)
        return data[path]
    return fetch


def singles_repo(tmp_path) -> SinglesRepository:
    repo = SinglesRepository(lambda: sqlite3.connect(tmp_path / "singles.sqlite3"))
    repo.initialize()
    return repo


def sealed_item(**overrides):
    values = dict(symbol="111", asset_name="", asset_type="MTG_SEALED", account_id="collection",
                  as_of=datetime(2026, 11, 20, 12, tzinfo=timezone.utc), shares=Decimal("5"), cost_basis=Decimal("525"),
                  current_value=Decimal("525"), recorded_by="operator", recorded_at=NOW)
    values.update(overrides)
    return create_manual_holding_snapshot(**values)


@pytest.mark.parametrize("text", ["657849", "TCG-657849", " tcg:657849 ",
                                  "https://www.tcgplayer.com/product/657849/magic-some-set-play-booster-display"])
def test_product_id_accepts_a_number_or_a_tcgplayer_link(text):
    assert tcgplayer_product_id(text) == "657849"


def test_product_id_rejects_anything_else():
    with pytest.raises(SealedError):
        tcgplayer_product_id("Play Booster box")


def test_sealed_holding_stores_the_product_id_as_its_symbol():
    item = sealed_item(symbol="https://www.tcgplayer.com/product/111/x")
    assert item.symbol == "111" and item.asset_type == "MTG_SEALED"


def test_find_group_searches_newest_sets_first(tmp_path):
    calls: list[str] = []
    assert find_group("111", fake_tcgcsv(calls)) == (200, "Synthetic Set - Play Booster Display")
    assert calls == ["groups", "200/products"]          # stopped at the newest set that has it


def test_refresh_prices_each_product_and_remembers_its_set(tmp_path):
    repo = singles_repo(tmp_path)
    calls: list[str] = []
    out = refresh_sealed_prices(repo, ["111", "https://www.tcgplayer.com/product/222/x"], fetch=fake_tcgcsv(calls), now=NOW)
    assert out == {"sealed_products": 2, "priced": 2, "not_found": 0}
    prices = sealed_prices(repo)
    assert prices["111"]["usd"] == "101.50" and prices["111"]["group_id"] == 200
    assert prices["222"]["usd"] == "55.25"                # mid price when there's no market price
    calls.clear()
    refresh_sealed_prices(repo, ["111"], fetch=fake_tcgcsv(calls), now=NOW)
    assert calls == ["200/prices"]                         # the set is remembered: one request a day


def test_unknown_product_is_counted_not_raised(tmp_path):
    out = refresh_sealed_prices(singles_repo(tmp_path), ["999"], fetch=fake_tcgcsv([]), now=NOW)
    assert out == {"sealed_products": 1, "priced": 0, "not_found": 1}


def test_sealed_prices_ignore_singles_and_singles_ignore_sealed(tmp_path):
    from foundation.production.mtg_singles import summary
    repo = singles_repo(tmp_path)
    refresh_sealed_prices(repo, ["111"], fetch=fake_tcgcsv([]), now=NOW)
    assert set(sealed_prices(repo)) == {"111"}
    assert summary(repo.lots(), repo.prices())["card_count"] == 0


def test_mark_to_market_values_sealed_boxes_at_market_times_count():
    doc = sealed_item().document()
    marked = mark_to_market([doc], {}, {"111": {"usd": "101.50", "as_of": "2026-11-23", "name": "Synthetic display"}})[0]
    assert marked["current_value"] == "507.50" and marked["gain_loss"] == "-17.50"
    assert marked["valuation_source"] == "TCGPLAYER_MARKET" and marked["tcgplayer_name"] == "Synthetic display"
    assert marked["snapshot_current_value"] == "525"


def test_sealed_without_a_price_keeps_its_entered_value():
    marked = mark_to_market([sealed_item().document()], {}, {})[0]
    assert marked["current_value"] == "525" and marked["valuation_source"] == "MANUAL_SNAPSHOT"


def test_sqlite_repository_accepts_sealed_holdings():
    repo = SQLiteManualHoldingRepository(sqlite3.connect(":memory:"))
    repo.initialize()
    repo.save(sealed_item())
    assert [(h.symbol, h.asset_type) for h in repo.current()] == [("111", "MTG_SEALED")]


def test_net_worth_counts_sealed_as_its_own_line(tmp_path):
    from foundation.production.net_worth import _investments

    repo = singles_repo(tmp_path)
    refresh_sealed_prices(repo, ["111"], fetch=fake_tcgcsv([]), now=NOW)
    etf = SimpleNamespace(cost_basis=Decimal("90"), document=lambda: {
        "symbol": "VOO", "asset_type": "ETF", "shares": "0.2", "cost_basis": "90", "current_value": "95",
        "current_price": "475", "as_of": "2026-10-01"})
    box = sealed_item()
    manual = SimpleNamespace(current=lambda: (etf, box))
    out = _investments(None, None, manual, None, singles=repo)
    assert out["manual_etfs"] == "95.00" and out["manual_basis"] == "90.00"
    assert out["mtg_sealed"] == "507.50" and out["mtg_sealed_basis"] == "525.00"
    assert out["total"] == "602.50"


def test_hosted_routes_mark_sealed_and_price_on_save(tmp_path):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from foundation.production.hosted_manual_holdings import install_manual_holding_routes

    repo_singles = singles_repo(tmp_path)
    holdings = SQLiteManualHoldingRepository(sqlite3.connect(tmp_path / "m.sqlite3", check_same_thread=False))
    holdings.initialize()
    settings = SimpleNamespace(credentials={"op": ("synthetic-key-123", ("operator",))})
    app = FastAPI()
    install_manual_holding_routes(app, settings, holdings, market_prices=lambda: {},
                                  sealed_prices=lambda: sealed_prices(repo_singles),
                                  refresh_sealed=lambda ids: refresh_sealed_prices(repo_singles, ids, fetch=fake_tcgcsv([]), now=NOW))
    client = TestClient(app)
    saved = client.post("/v1/manual-holdings", headers={"x-api-key": "synthetic-key-123"}, json={
        "symbol": "https://www.tcgplayer.com/product/111/x", "asset_type": "MTG_SEALED", "account_id": "collection",
        "as_of": "2026-11-20T12:00:00Z", "shares": "5", "cost_basis": "525", "current_value": "525"})
    assert saved.status_code == 201, saved.text
    body = client.get("/v1/manual-holdings", headers={"x-api-key": "synthetic-key-123"}).json()
    assert body["items"][0]["valuation_source"] == "TCGPLAYER_MARKET"
    assert body["mtg_sealed_value"] == "507.50" and body["mtg_sealed_cost_basis"] == "525"
    assert body["current_value"] == "507.50"
