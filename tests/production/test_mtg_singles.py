"""MTG singles: Moxfield import, exact-printing prices, decks and the binder (synthetic cards, fake Scryfall)."""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from foundation.production.mtg_singles import (BINDER, SinglesError, SinglesRepository, apply_action, lookup_prices,
                                               new_lots, parse_any, parse_csv, parse_text, price_key, refresh_prices,
                                               summary)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 10, 19, 15, tzinfo=timezone.utc)

TEXT = """Commander
1 Atraxa, Praetors' Voice (2X2) 190 *F* $40.00

Deck
1 Smothering Tithe (RNA) 22 *F* ~$18.50
2 Island (UNF) 236 *E*
1 Wear // Tear (STX) 245
1 Arcane Signet
1 Serialized Thing (SLD) 999z

Maybeboard
1 Mana Crypt (2XM) 270
"""

CATALOG = {
    ("2x2", "190"): {"name": "Atraxa, Praetors' Voice", "usd": "20.00", "usd_foil": "55.00"},
    ("rna", "22"): {"name": "Smothering Tithe", "usd": "15.00", "usd_foil": "30.00"},
    ("unf", "236"): {"name": "Island", "usd": "0.40", "usd_etched": "1.50"},
    ("stx", "245"): {"name": "Wear // Tear", "usd": "0.80"},
    ("sld", "999z"): {"name": "Serialized Thing", "usd": None},
}


def fake_fetch(identifiers, calls=None):
    if calls is not None:
        calls.append(len(identifiers))
    data, missing = [], []
    for ident in identifiers:
        if "name" in ident:
            if ident["name"] == "Arcane Signet":
                data.append({"id": "as", "name": "Arcane Signet", "set": "cmr", "collector_number": "297",
                             "prices": {"usd": "0.90"}, "image_uris": {"small": "https://img.test/as.jpg"}})
            else:
                missing.append(ident)
            continue
        hit = CATALOG.get((ident["set"], ident["collector_number"]))
        if hit is None:
            missing.append(ident)
            continue
        data.append({"id": f"{ident['set']}-{ident['collector_number']}", "name": hit["name"], "set": ident["set"],
                     "collector_number": ident["collector_number"], "set_name": ident["set"].upper(),
                     "prices": {"usd": hit.get("usd"), "usd_foil": hit.get("usd_foil"), "usd_etched": hit.get("usd_etched")},
                     "scryfall_uri": "https://scryfall.test/card"})
    return {"data": data, "not_found": missing}


def repo(tmp_path):
    r = SinglesRepository.sqlite(tmp_path / "singles.sqlite3")
    r.initialize()
    return r


def test_moxfield_text_reads_printings_finishes_and_prices_paid():
    cards, unread = parse_text(TEXT)
    assert unread == []
    assert [c["name"] for c in cards] == ["Atraxa, Praetors' Voice", "Smothering Tithe", "Island", "Wear // Tear",
                                          "Arcane Signet", "Serialized Thing"]          # the maybeboard is left out
    atraxa, tithe, island = cards[0], cards[1], cards[2]
    assert (atraxa["set_code"], atraxa["collector_number"], atraxa["finish"], atraxa["price_paid"], atraxa["paid_estimated"]) == ("2x2", "190", "foil", 40.0, False)
    assert tithe["paid_estimated"] is True and tithe["price_paid"] == 18.5
    assert island["quantity"] == 2 and island["finish"] == "etched"
    assert cards[4]["set_code"] is None and cards[4]["price_paid"] is None
    # a number after the name without $ is never read as a price
    assert parse_text("1 Sol Ring (C21) 263")[0][0]["price_paid"] is None


def test_moxfield_csv_and_auto_detection():
    csv_text = "Count,Name,Edition,Foil,Collector Number,Purchase Price\n1,Sol Ring,c21,foil,263,$3.50\n2,Island,unf,etched,236,\n"
    cards, _ = parse_csv(csv_text, estimated=True)
    assert cards[0] == {"quantity": 1, "name": "Sol Ring", "set_code": "c21", "collector_number": "263", "finish": "foil",
                        "price_paid": 3.5, "paid_estimated": True, "deck": None}
    assert cards[1]["finish"] == "etched" and cards[1]["price_paid"] is None
    assert parse_any(csv_text)[0][0]["name"] == "Sol Ring"
    assert parse_any(TEXT)[0][0]["name"] == "Atraxa, Praetors' Voice"
    with pytest.raises(SinglesError):
        parse_csv("Count,Edition\n1,c21\n")


def test_prices_follow_the_exact_printing_and_finish():
    cards, _ = parse_text(TEXT)
    calls = []
    prices = lookup_prices(cards, fetch=lambda ids: fake_fetch(ids, calls), now=NOW)
    assert prices[price_key(cards[0])]["usd"] == 55.0            # foil Atraxa, not the nonfoil 20.00
    assert prices[price_key(cards[2])]["usd"] == 1.5             # etched Island
    assert prices[price_key(cards[4])]["usd"] == 0.9 and prices[price_key(cards[4])]["set_code"] == "cmr"
    assert prices[price_key(cards[5])]["usd"] is None            # a printing with no market price
    assert calls == [6]                                          # one request for up to 75 printings


def test_collection_summary_decks_and_honest_gain(tmp_path):
    r = repo(tmp_path)
    cards, _ = parse_text(TEXT)
    r.save(new_lots(cards, "Atraxa", now=NOW))
    assert refresh_prices(r, fetch=fake_fetch, now=NOW) == {"printings": 6, "priced": 5, "not_found": 0}
    doc = summary(r.lots(), r.prices())
    # 55 + 30 + 2 x 1.50 + 0.80 + 0.90 = 89.70; the serialized card has no price
    assert doc["value"] == "89.70" and doc["card_count"] == 7 and doc["unpriced_cards"] == 1
    assert doc["paid_known"] == "58.50"                          # Atraxa 40 + Tithe 18.50 (estimate)
    assert doc["gain_known"] == "26.50"                          # (55 - 40) + (30 - 18.50)
    # for totals, a card with no price paid counts its value as paid: no invented gain
    assert doc["basis_for_totals"] == str(Decimal("58.50") + Decimal("3.00") + Decimal("0.80") + Decimal("0.90"))
    assert doc["after_selling_costs"] == "78.94"
    deck = doc["decks"][0]
    assert deck["deck"] == "Atraxa" and deck["cards"] == 7 and deck["estimated_paid"] == 1 and deck["cards_with_paid"] == 2
    tithe = next(c for c in doc["lots"] if c["name"] == "Smothering Tithe")
    assert tithe["paid_estimated"] and tithe["exact_printing"] and tithe["value_source"] == "SCRYFALL_TCGPLAYER_MARKET"


def test_upgrades_cuts_sales_and_own_values(tmp_path):
    r = repo(tmp_path)
    r.save(new_lots(parse_text("2 Island (UNF) 236 *E* $1.00\n1 Serialized Thing (SLD) 999z")[0], "Atraxa", now=NOW))
    refresh_prices(r, fetch=fake_fetch, now=NOW)
    island = next(l for l in r.lots() if l.name == "Island")
    apply_action(r, island.lot_id, {"action": "move", "quantity": 1, "deck": ""}, now=NOW)   # one copy to the binder
    decks = {(l.deck, l.name): l.quantity for l in r.lots()}
    assert decks[("Atraxa", "Island")] == 1 and decks[(BINDER, "Island")] == 1
    binder = next(l for l in r.lots() if l.deck == BINDER)
    apply_action(r, binder.lot_id, {"action": "sell", "sold_price": "1.25"}, now=NOW)
    assert all(l.deck != BINDER for l in r.lots())
    sold = [l for l in r.lots(status=None) if l.status == "sold"]
    assert len(sold) == 1 and sold[0].sold_price == Decimal("1.25")
    serial = next(l for l in r.lots() if l.name == "Serialized Thing")
    apply_action(r, serial.lot_id, {"action": "value", "manual_value": "300"}, now=NOW)
    doc = summary(r.lots(), r.prices())
    assert doc["unpriced_cards"] == 0 and next(c for c in doc["lots"] if c["name"] == "Serialized Thing")["value_source"] == "MANUAL"
    apply_action(r, serial.lot_id, {"action": "paid", "price_paid": "250", "estimated": True}, now=NOW)
    assert next(l for l in r.lots() if l.name == "Serialized Thing").paid_estimated
    with pytest.raises(SinglesError):
        apply_action(r, serial.lot_id, {"action": "move", "quantity": 5})
    apply_action(r, serial.lot_id, {"action": "remove"}, now=NOW)
    assert [l.name for l in r.lots()] == ["Island"]


def test_routes_preview_then_save_and_change(tmp_path):
    pytest.importorskip("fastapi")
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from foundation.production.hosted_mtg_singles import install_mtg_singles_routes

    import sqlite3
    r = SinglesRepository(lambda: sqlite3.connect(str(tmp_path / "s.sqlite3"), check_same_thread=False))
    r.initialize()
    app = FastAPI()
    settings = SimpleNamespace(credentials={"viewer": ("view-key", ("viewer",)), "operator": ("op-key", ("operator",))})
    install_mtg_singles_routes(app, settings, r, fetch=fake_fetch)
    c = TestClient(app)
    view, op = {"X-API-Key": "view-key"}, {"X-API-Key": "op-key"}
    assert c.get("/v1/mtg-singles").status_code == 401
    assert c.get("/v1/mtg-singles", headers=view).json()["card_count"] == 0
    preview = c.post("/v1/mtg-singles/import", headers=view, json={"deck": "Atraxa", "text": TEXT}).json()
    assert preview["saved"] is False and preview["card_count"] == 7 and preview["not_found"] == ["Serialized Thing"]
    assert c.get("/v1/mtg-singles", headers=view).json()["card_count"] == 0            # a preview saves nothing
    assert c.post("/v1/mtg-singles/import", headers=view, json={"deck": "Atraxa", "text": TEXT, "save": True}).status_code == 403
    saved = c.post("/v1/mtg-singles/import", headers=op, json={"deck": "Atraxa", "text": TEXT, "save": True}).json()
    assert saved["saved"] and saved["collection"]["value"] == "89.70"
    upgrade = c.post("/v1/mtg-singles/import", headers=op, json={"deck": "Atraxa", "text": "1 Sol Ring (C21) 263 $2.00", "save": True}).json()
    assert upgrade["collection"]["card_count"] == 8 and upgrade["not_found"] == ["Sol Ring"]
    lot = next(l for l in upgrade["collection"]["lots"] if l["name"] == "Sol Ring")
    moved = c.post(f"/v1/mtg-singles/lots/{lot['lot_id']}", headers=op, json={"action": "move", "deck": "Binder"}).json()
    assert {d["deck"] for d in moved["decks"]} == {"Atraxa", "Binder"}
    assert c.post(f"/v1/mtg-singles/lots/{lot['lot_id']}", headers=op, json={"action": "fly"}).status_code == 422
    assert c.post("/v1/mtg-singles/import", headers=view, json={"deck": "x", "text": "just words"}).status_code == 422
    refreshed = c.post("/v1/mtg-singles/refresh-prices", headers=op).json()
    assert refreshed["refresh"]["printings"] == 7


def test_singles_join_net_worth_and_the_data_download(tmp_path):
    from foundation.production.data_export import build_export
    from foundation.production.net_worth import compute_net_worth

    r = repo(tmp_path)
    r.save(new_lots(parse_text("1 Smothering Tithe (RNA) 22 *F* $18.50")[0], "Atraxa", now=NOW))
    refresh_prices(r, fetch=fake_fetch, now=NOW)
    out = compute_net_worth(today=date(2026, 10, 20), singles=r)
    assert out["investments"]["mtg_singles"] == "30.00" and out["components"]["investments"] == "30.00"
    assert out["investments"]["mtg_singles_basis"] == "18.50"
    export = build_export(singles=r, now=NOW)
    assert export["mtg_singles"]["lots"][0]["name"] == "Smothering Tithe"


def test_dashboard_shows_and_counts_singles():
    assets = ROOT / "foundation" / "production" / "dashboard_assets"
    page = (assets / "mtg_singles.js").read_text(encoding="utf-8")
    assert page.isascii() and "style=" not in page and "localStorage" not in page
    for hook in ('call("/v1/mtg-singles")', 'post("/v1/mtg-singles/import"', "/v1/mtg-singles/lots/", 'post("/v1/mtg-singles/refresh-prices"',
                 "uip:mtg-singles-changed", "data-singles-preview", "singles-jump"):
        assert hook in page, hook
    html = (assets / "dashboard.html").read_text(encoding="utf-8")
    assert '<script src="/dashboard/assets/mtg_singles.js" defer></script>' in html
    assert '@app.get("/dashboard/assets/mtg_singles.js"' in (ROOT / "foundation/production/http_service.py").read_text()
    dash = (assets / "dashboard.js").read_text(encoding="utf-8")
    assert dash.count("const totalValue=coreMarket+acornsValue+manualValue+singlesValue;") == 2
    assert 'optional("/v1/mtg-singles")' in dash and "mtgSingles,transactions:transactionItems}" in dash
    realm = (assets / "rpg_realm.js").read_text(encoding="utf-8")
    assert "totals.mtg+=num(d.mtgSingles?.value)||0;" in realm and 'key:"mtg:SINGLES"' in realm
