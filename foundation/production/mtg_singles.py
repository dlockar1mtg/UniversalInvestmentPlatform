"""MTG singles: the Commander cards Devon owns, by deck, priced daily at the exact printing he owns.

A *lot* is a card printing in one deck (or the binder) with a quantity and, when known, the price paid per
copy (an estimate is flagged as one). Cards come in from a Moxfield export, either the text format
("1 Smothering Tithe (RNA) 22 *F*", optionally followed by "$18.50" or "~$18.50" for a price paid or an
estimate) or a CSV with Count / Name / Edition / Collector Number / Foil / Purchase Price columns. Upgrades are
the same paste into an existing deck; cuts move a lot to the binder, mark it sold, or remove it.

Prices come from Scryfall (TCGplayer market price for the normal, foil or etched finish of that exact set and
collector number). A printing with no Scryfall price (some serialized cards) can carry a value you enter.
The collection lives only in the UIP database, never in the repository.
"""
from __future__ import annotations

import csv
import io
import json
import re
import time
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

FINISHES = ("nonfoil", "foil", "etched")
BINDER = "Binder"
SELL_COST = Decimal("0.12")          # marketplace fees and shipping, as for sealed product
SCRYFALL_COLLECTION = "https://api.scryfall.com/cards/collection"
SCRYFALL_BATCH = 75                  # Scryfall's limit per collection request


class SinglesError(ValueError):
    pass


def _money(value) -> str | None:
    return None if value is None else str(Decimal(str(value)).quantize(Decimal("0.01")))


# ---------------------------------------------------------------- parsing Moxfield exports
LINE = re.compile(
    r"""^\s*(?P<qty>\d+)\s*x?\s+(?P<name>.+?)
        (?:\s+\((?P<set>[A-Za-z0-9]{2,6})\)\s+(?P<number>[^\s*$~]+))?
        (?P<flags>(?:\s+\*[A-Za-z]+\*)*)
        (?:\s+(?P<est>~)?\$(?P<price>\d+(?:\.\d{1,2})?))?\s*$""",
    re.X,
)
SKIP_SECTIONS = re.compile(r"^\s*(maybeboard|considering|tokens?)\b", re.I)


def _finish(flags: str) -> str:
    f = flags.upper()
    return "etched" if "*E*" in f else "foil" if "*F*" in f else "nonfoil"


def parse_text(text: str, *, estimated: bool = False) -> tuple[list[dict], list[str]]:
    """Moxfield text export (also the plain "1 Card Name" form). Returns (cards, lines it could not read)."""
    cards, unread, skipping = [], [], False
    for raw in str(text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        if not line[0].isdigit():                      # a section header: Commander, Deck, Sideboard, Maybeboard
            skipping = bool(SKIP_SECTIONS.match(line))
            continue
        if skipping:
            continue
        m = LINE.match(line)
        if not m:
            unread.append(line)
            continue
        price = m.group("price")
        cards.append({
            "quantity": int(m.group("qty")), "name": m.group("name").strip(),
            "set_code": (m.group("set") or "").lower() or None, "collector_number": m.group("number"),
            "finish": _finish(m.group("flags") or ""),
            "price_paid": float(price) if price else None,
            "paid_estimated": bool(price) and (estimated or bool(m.group("est"))),
        })
    return cards, unread


HEADERS = {
    "quantity": ("count", "quantity", "qty", "amount"),
    "name": ("name", "card name", "card"),
    "set_code": ("edition", "set", "set code", "edition code"),
    "collector_number": ("collector number", "collector_number", "number", "cn"),
    "finish": ("foil", "finish", "printing"),
    "price_paid": ("purchase price", "price paid", "paid", "purchase_price", "price"),
    "deck": ("deck", "deck name"),
    "board": ("board", "section"),
}


def parse_csv(text: str, *, estimated: bool = False) -> tuple[list[dict], list[str]]:
    reader = csv.DictReader(io.StringIO(str(text or "").lstrip("﻿")))
    if not reader.fieldnames:
        raise SinglesError("the CSV has no header row")
    lookup = {h.strip().lower(): h for h in reader.fieldnames}
    col = {key: next((lookup[a] for a in names if a in lookup), None) for key, names in HEADERS.items()}
    if not col["name"]:
        raise SinglesError("the CSV needs a Name column")
    cards, unread = [], []
    for n, row in enumerate(reader, start=2):
        name = (row.get(col["name"]) or "").strip()
        if not name:
            continue
        board = (row.get(col["board"]) or "").strip().lower() if col["board"] else ""
        if board in ("maybeboard", "considering", "tokens"):
            continue
        try:
            qty = int(float((row.get(col["quantity"]) or "1").strip() or 1)) if col["quantity"] else 1
        except ValueError:
            unread.append(f"row {n}: {name} (count)")
            continue
        finish_raw = (row.get(col["finish"]) or "").strip().lower() if col["finish"] else ""
        finish = "etched" if "etch" in finish_raw else "foil" if finish_raw in ("foil", "true", "yes", "1", "f") else "nonfoil"
        price_raw = (row.get(col["price_paid"]) or "").replace("$", "").replace(",", "").strip() if col["price_paid"] else ""
        try:
            price = float(price_raw) if price_raw else None
        except ValueError:
            price = None
        cards.append({
            "quantity": qty, "name": name,
            "set_code": ((row.get(col["set_code"]) or "").strip().lower() or None) if col["set_code"] else None,
            "collector_number": ((row.get(col["collector_number"]) or "").strip() or None) if col["collector_number"] else None,
            "finish": finish, "price_paid": price, "paid_estimated": price is not None and estimated,
            "deck": ((row.get(col["deck"]) or "").strip() or None) if col["deck"] else None,
        })
    return cards, unread


def parse_any(text: str, *, estimated: bool = False) -> tuple[list[dict], list[str]]:
    first = next((ln for ln in str(text or "").splitlines() if ln.strip()), "")
    if "," in first and not first.strip()[:1].isdigit() and re.search(r"(?i)\bname\b", first):
        return parse_csv(text, estimated=estimated)
    return parse_text(text, estimated=estimated)


# ---------------------------------------------------------------- prices (Scryfall)
def price_key(card: dict) -> str:
    if card.get("set_code") and card.get("collector_number"):
        return f"{card['set_code'].lower()}|{card['collector_number']}|{card['finish']}"
    return f"name:{card['name'].lower()}|{card['finish']}"


def _identifier(card: dict) -> dict:
    if card.get("set_code") and card.get("collector_number"):
        return {"set": card["set_code"].lower(), "collector_number": str(card["collector_number"])}
    return {"name": card["name"]}


def scryfall_fetch(identifiers: list[dict], *, session=None) -> dict:
    """POST /cards/collection. Returns {"data": [...], "not_found": [...]} (network; Scryfall asks for a UA)."""
    import requests

    s = session or requests.Session()
    r = s.post(SCRYFALL_COLLECTION, json={"identifiers": identifiers}, timeout=30,
               headers={"User-Agent": "UIP-MTG-singles/1.0", "Accept": "application/json"})
    r.raise_for_status()
    return r.json()


def lookup_prices(cards: list[dict], *, fetch=scryfall_fetch, now: datetime | None = None) -> dict[str, dict]:
    """Price each distinct printing+finish. Returns {price_key: price row}; a printing Scryfall lacks is absent."""
    now = now or datetime.now(timezone.utc)
    wanted: dict[str, dict] = {}
    for c in cards:
        wanted.setdefault(price_key(c), c)
    ids = {}
    for key, c in wanted.items():
        ident = json.dumps(_identifier(c), sort_keys=True)
        ids.setdefault(ident, []).append(key)
    out: dict[str, dict] = {}
    idents = list(ids)
    for start in range(0, len(idents), SCRYFALL_BATCH):
        batch = [json.loads(i) for i in idents[start:start + SCRYFALL_BATCH]]
        doc = fetch(batch)
        for card in doc.get("data", []):
            prices = card.get("prices") or {}
            by_set = json.dumps({"set": card.get("set"), "collector_number": card.get("collector_number")}, sort_keys=True)
            by_name = json.dumps({"name": card.get("name")}, sort_keys=True)
            keys = ids.get(by_set) or ids.get(by_name) or []
            if not keys:                               # a name lookup matched a differently written name (e.g. a // card)
                low = str(card.get("name", "")).lower()
                keys = [k for i, ks in ids.items() for k in ks if json.loads(i).get("name", "").lower() in (low, low.split(" // ")[0])]
            image = (card.get("image_uris") or {}).get("small") or (((card.get("card_faces") or [{}])[0].get("image_uris") or {}).get("small"))
            for key in keys:
                finish = wanted[key]["finish"]
                usd = prices.get({"nonfoil": "usd", "foil": "usd_foil", "etched": "usd_etched"}[finish])
                out[key] = {"key": key, "scryfall_id": card.get("id"), "name": card.get("name"),
                            "set_code": card.get("set"), "set_name": card.get("set_name"),
                            "collector_number": card.get("collector_number"), "finish": finish,
                            "usd": float(usd) if usd not in (None, "") else None, "image": image,
                            "scryfall_uri": card.get("scryfall_uri"), "as_of": now.date().isoformat(),
                            "fetched_at": now.isoformat()}
        if start + SCRYFALL_BATCH < len(idents):
            time.sleep(0.12)                           # Scryfall asks for 50-100 ms between requests
    return out


# ---------------------------------------------------------------- storage
SCHEMA = (
    """CREATE TABLE IF NOT EXISTS mtg_single_lots (
        lot_id TEXT PRIMARY KEY, deck TEXT NOT NULL, name TEXT NOT NULL, set_code TEXT, collector_number TEXT,
        finish TEXT NOT NULL, quantity INTEGER NOT NULL, price_paid NUMERIC, paid_estimated BOOLEAN NOT NULL,
        manual_value NUMERIC, status TEXT NOT NULL, added_at TEXT NOT NULL, closed_at TEXT, sold_price NUMERIC,
        note TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS mtg_single_prices (
        price_key TEXT PRIMARY KEY, document TEXT NOT NULL, usd NUMERIC, as_of TEXT NOT NULL, fetched_at TEXT NOT NULL)""",
)
LOT_COLS = ("lot_id", "deck", "name", "set_code", "collector_number", "finish", "quantity", "price_paid",
            "paid_estimated", "manual_value", "status", "added_at", "closed_at", "sold_price", "note")


@dataclass
class Lot:
    lot_id: str
    deck: str
    name: str
    set_code: str | None
    collector_number: str | None
    finish: str
    quantity: int
    price_paid: Decimal | None
    paid_estimated: bool
    manual_value: Decimal | None
    status: str
    added_at: str
    closed_at: str | None
    sold_price: Decimal | None
    note: str

    @property
    def key(self) -> str:
        return price_key({"set_code": self.set_code, "collector_number": self.collector_number,
                          "name": self.name, "finish": self.finish})

    def row(self):
        return tuple(getattr(self, c) for c in LOT_COLS)


def _lot(row) -> Lot:
    d = dict(zip(LOT_COLS, row))
    for k in ("price_paid", "manual_value", "sold_price"):
        d[k] = None if d[k] is None else Decimal(str(d[k]))
    d["paid_estimated"] = bool(d["paid_estimated"])
    d["quantity"] = int(d["quantity"])
    return Lot(**d)


class SinglesRepository:
    """SQLite (tests, local) or PostgreSQL (hosted) through a DB-API connection factory."""

    def __init__(self, connection_factory, placeholder: str = "?"):
        self.connect = connection_factory
        self.p = placeholder

    @classmethod
    def from_dsn(cls, dsn: str) -> "SinglesRepository":
        import psycopg
        return cls(lambda: psycopg.connect(dsn), "%s")

    @classmethod
    def sqlite(cls, path) -> "SinglesRepository":
        import sqlite3
        return cls(lambda: sqlite3.connect(str(path)), "?")

    def initialize(self) -> None:
        with closing(self.connect()) as db:
            cur = db.cursor()
            for ddl in SCHEMA:
                cur.execute(ddl)
            db.commit()

    def lots(self, *, status: str | None = "held") -> list[Lot]:
        with closing(self.connect()) as db:
            cur = db.cursor()
            sql = f"SELECT {','.join(LOT_COLS)} FROM mtg_single_lots"
            if status:
                cur.execute(sql + f" WHERE status={self.p} ORDER BY deck, name", (status,))
            else:
                cur.execute(sql + " ORDER BY deck, name")
            return [_lot(r) for r in cur.fetchall()]

    def lot(self, lot_id: str) -> Lot | None:
        with closing(self.connect()) as db:
            cur = db.cursor()
            cur.execute(f"SELECT {','.join(LOT_COLS)} FROM mtg_single_lots WHERE lot_id={self.p}", (lot_id,))
            r = cur.fetchone()
            return _lot(r) if r else None

    def save(self, lots: list[Lot]) -> None:
        p = self.p
        with closing(self.connect()) as db:
            cur = db.cursor()
            for lot in lots:
                cur.execute(f"DELETE FROM mtg_single_lots WHERE lot_id={p}", (lot.lot_id,))
                cur.execute(f"INSERT INTO mtg_single_lots ({','.join(LOT_COLS)}) VALUES ({','.join([p] * len(LOT_COLS))})",
                            tuple(str(v) if isinstance(v, Decimal) else v for v in lot.row()))
            db.commit()

    def prices(self) -> dict[str, dict]:
        with closing(self.connect()) as db:
            cur = db.cursor()
            cur.execute("SELECT price_key, document FROM mtg_single_prices")
            return {k: json.loads(doc) for k, doc in cur.fetchall()}

    def save_prices(self, rows: dict[str, dict]) -> None:
        p = self.p
        with closing(self.connect()) as db:
            cur = db.cursor()
            for key, doc in rows.items():
                cur.execute(f"DELETE FROM mtg_single_prices WHERE price_key={p}", (key,))
                cur.execute(f"INSERT INTO mtg_single_prices (price_key, document, usd, as_of, fetched_at) VALUES ({p},{p},{p},{p},{p})",
                            (key, json.dumps(doc, sort_keys=True), doc.get("usd"), doc["as_of"], doc["fetched_at"]))
            db.commit()


# ---------------------------------------------------------------- the collection
def new_lots(cards: list[dict], deck: str, now: datetime | None = None) -> list[Lot]:
    now = now or datetime.now(timezone.utc)
    deck = (deck or "").strip()[:80] or BINDER
    out = []
    for c in cards:
        if c["finish"] not in FINISHES or not 1 <= int(c["quantity"]) <= 999:
            raise SinglesError(f"bad card line: {c.get('name')}")
        paid = c.get("price_paid")
        if paid is not None and not 0 <= float(paid) <= 1_000_000:
            raise SinglesError(f"bad price paid for {c['name']}")
        out.append(Lot(lot_id=uuid.uuid4().hex, deck=(c.get("deck") or deck)[:80], name=c["name"][:200],
                       set_code=c.get("set_code"), collector_number=c.get("collector_number"), finish=c["finish"],
                       quantity=int(c["quantity"]), price_paid=None if paid is None else Decimal(str(paid)).quantize(Decimal("0.01")),
                       paid_estimated=bool(c.get("paid_estimated")), manual_value=None, status="held",
                       added_at=now.isoformat(), closed_at=None, sold_price=None, note=""))
    return out


def lot_document(lot: Lot, prices: dict[str, dict]) -> dict:
    price = prices.get(lot.key)
    unit = lot.manual_value if lot.manual_value is not None else (
        Decimal(str(price["usd"])) if price and price.get("usd") is not None else None)
    worth = None if unit is None else unit * lot.quantity
    paid = None if lot.price_paid is None else lot.price_paid * lot.quantity
    return {"lot_id": lot.lot_id, "deck": lot.deck, "name": (price or {}).get("name") or lot.name,
            "set_code": lot.set_code or (price or {}).get("set_code"), "set_name": (price or {}).get("set_name"),
            "collector_number": lot.collector_number or (price or {}).get("collector_number"), "finish": lot.finish,
            "quantity": lot.quantity, "exact_printing": bool(lot.set_code and lot.collector_number),
            "unit_value": _money(unit),
            "value_source": "MANUAL" if lot.manual_value is not None else ("SCRYFALL_TCGPLAYER_MARKET" if unit is not None else "UNPRICED"),
            "value": _money(worth), "price_paid": _money(lot.price_paid), "paid": _money(paid),
            "paid_estimated": lot.paid_estimated,
            "gain": None if worth is None or paid is None else _money(worth - paid),
            "price_as_of": (price or {}).get("as_of"), "image": (price or {}).get("image"),
            "scryfall_uri": (price or {}).get("scryfall_uri"), "status": lot.status, "added_at": lot.added_at,
            "closed_at": lot.closed_at, "sold_price": _money(lot.sold_price), "note": lot.note}


def summary(lots: list[Lot], prices: dict[str, dict]) -> dict:
    docs = [lot_document(lot, prices) for lot in lots]
    decks: dict[str, dict] = {}
    for d in docs:
        g = decks.setdefault(d["deck"], {"deck": d["deck"], "cards": 0, "value": Decimal(0), "paid_known": Decimal(0),
                                          "value_with_paid": Decimal(0), "unpriced": 0, "estimated_paid": 0,
                                          "cards_with_paid": 0})
        g["cards"] += d["quantity"]
        if d["value"] is not None:
            g["value"] += Decimal(d["value"])
        else:
            g["unpriced"] += d["quantity"]
        if d["paid"] is not None:
            g["paid_known"] += Decimal(d["paid"])
            g["value_with_paid"] += Decimal(d["value"] or 0)
            g["estimated_paid"] += d["quantity"] if d["paid_estimated"] else 0
            g["cards_with_paid"] += d["quantity"]
    deck_rows = []
    for g in sorted(decks.values(), key=lambda g: (g["deck"] == BINDER, -g["value"])):
        deck_rows.append({**g, "value": _money(g["value"]), "paid_known": _money(g["paid_known"]),
                          "gain_known": _money(g["value_with_paid"] - g["paid_known"]),
                          "value_with_paid": _money(g["value_with_paid"])})
    value = sum((Decimal(d["value"]) for d in docs if d["value"] is not None), Decimal(0))
    paid = sum((Decimal(d["paid"]) for d in docs if d["paid"] is not None), Decimal(0))
    unknown_paid_value = sum((Decimal(d["value"]) for d in docs if d["paid"] is None and d["value"] is not None), Decimal(0))
    as_of = max((d["price_as_of"] for d in docs if d["price_as_of"]), default=None)
    return {
        "lots": docs, "decks": deck_rows,
        "card_count": sum(d["quantity"] for d in docs),
        "value": _money(value), "paid_known": _money(paid),
        # For investment totals, a card with no price paid counts its value as its basis (no invented gain).
        "basis_for_totals": _money(paid + unknown_paid_value),
        "gain_known": _money(sum((Decimal(d["gain"]) for d in docs if d["gain"] is not None), Decimal(0))),
        "after_selling_costs": _money(value * (1 - SELL_COST)),
        "unpriced_cards": sum(d["quantity"] for d in docs if d["value"] is None),
        "prices_as_of": as_of, "authority_state": "MANUAL_COLLECTION_PRICED_BY_SCRYFALL",
    }


def refresh_prices(repo: SinglesRepository, *, fetch=scryfall_fetch, now=None) -> dict:
    lots = repo.lots()
    cards = [{"set_code": lot.set_code, "collector_number": lot.collector_number, "name": lot.name,
              "finish": lot.finish} for lot in lots]
    found = lookup_prices(cards, fetch=fetch, now=now) if cards else {}
    repo.save_prices(found)
    keys = {price_key(c) for c in cards}
    return {"printings": len(keys), "priced": sum(1 for k in keys if (found.get(k) or {}).get("usd") is not None),
            "not_found": len(keys - set(found))}


def apply_action(repo: SinglesRepository, lot_id: str, body: dict, now: datetime | None = None) -> list[Lot]:
    """move / sell / remove a lot (whole or part), or set its value or price paid. Returns the changed lots."""
    now = now or datetime.now(timezone.utc)
    lot = repo.lot(lot_id)
    if lot is None or lot.status != "held":
        raise SinglesError("that card is not in the collection")
    action = str(body.get("action") or "")
    qty = int(body.get("quantity") or lot.quantity)
    if not 1 <= qty <= lot.quantity:
        raise SinglesError(f"quantity must be between 1 and {lot.quantity}")
    changed: list[Lot] = []
    if action in ("move", "sell", "remove") and qty < lot.quantity:
        rest = Lot(**{**lot.__dict__, "quantity": lot.quantity - qty})
        lot = Lot(**{**lot.__dict__, "lot_id": uuid.uuid4().hex, "quantity": qty})
        changed.append(rest)
        repo.save([rest])
    if action == "move":
        deck = str(body.get("deck") or "").strip()[:80] or BINDER
        lot.deck = deck
    elif action == "sell":
        price = body.get("sold_price")
        lot.status, lot.closed_at = "sold", now.isoformat()
        lot.sold_price = None if price in (None, "") else Decimal(str(price)).quantize(Decimal("0.01"))
    elif action == "remove":
        lot.status, lot.closed_at = "removed", now.isoformat()
    elif action == "value":
        v = body.get("manual_value")
        lot.manual_value = None if v in (None, "") else Decimal(str(v)).quantize(Decimal("0.01"))
    elif action == "paid":
        v = body.get("price_paid")
        lot.price_paid = None if v in (None, "") else Decimal(str(v)).quantize(Decimal("0.01"))
        lot.paid_estimated = bool(body.get("estimated"))
    else:
        raise SinglesError("action must be move, sell, remove, value or paid")
    repo.save([lot])
    return changed + [lot]
