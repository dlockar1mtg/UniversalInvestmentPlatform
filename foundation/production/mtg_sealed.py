"""Daily TCGplayer market prices for sealed MTG products held as manual holdings (asset_type MTG_SEALED).

The certified MTG lanes price Secret Lairs, Collector displays and pre-Collector boxes. Anything else sealed
(Play Booster boxes, bundles, cases, a new set's displays) is entered once as a manual holding keyed by its
TCGplayer product id, and priced here from TCGCSV, the same free TCGplayer feed the MTG pipeline uses:

  /tcgplayer/1/groups                  every Magic set ("group"), newest first by published date
  /tcgplayer/1/{group}/products        a set's products, to find which group a product id belongs to (once)
  /tcgplayer/1/{group}/prices          market prices for every product in the set

Prices are stored in the singles price table under "sealed:<product id>", so no new table or schedule is needed:
the daily singles price job refreshes them too.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Callable, Iterable

TCGCSV = "https://tcgcsv.com/tcgplayer/1"
SOURCE = "TCGCSV_TCGPLAYER_MARKET"
KEY_PREFIX = "sealed:"
MAX_GROUP_SCAN = 600  # how many sets to search, newest first, before giving up on an unknown product id

Fetch = Callable[[str], dict]


class SealedError(ValueError):
    pass


def tcgplayer_product_id(text: object) -> str:
    """'657849', 'TCG-657849' or a tcgplayer.com/product/657849/... link -> '657849'."""
    value = str(text or "").strip()
    match = re.search(r"/product/(\d+)", value) or re.fullmatch(r"(?:tcg[-:\s]?)?(\d{3,12})", value, re.IGNORECASE)
    if not match:
        raise SealedError("enter the TCGplayer product id (the number in the product's tcgplayer.com link)")
    return match.group(1)


def price_key(product_id: str) -> str:
    return f"{KEY_PREFIX}{product_id}"


def tcgcsv_fetch(path: str, *, opener=None) -> dict:
    import urllib.request

    request = urllib.request.Request(f"{TCGCSV}/{path.lstrip('/')}", headers={
        "User-Agent": "Mozilla/5.0 (compatible; UIP-sealed-prices/1.0)", "Accept": "application/json"})
    with (opener or urllib.request.urlopen)(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _results(payload: dict) -> list[dict]:
    rows = payload.get("results") if isinstance(payload, dict) else None
    return rows if isinstance(rows, list) else []


def find_group(product_id: str, fetch: Fetch, limit: int = MAX_GROUP_SCAN) -> tuple[int, str] | None:
    """The TCGCSV group (set) holding a product, searching newest sets first. Returns (group id, product name)."""
    groups = sorted(_results(fetch("groups")), key=lambda g: str(g.get("publishedOn") or ""), reverse=True)
    for group in groups[:limit]:
        gid = group.get("groupId")
        if gid is None:
            continue
        for product in _results(fetch(f"{gid}/products")):
            if str(product.get("productId")) == product_id:
                return int(gid), str(product.get("name") or "")
    return None


def _market(rows: Iterable[dict], product_id: str) -> float | None:
    """Market price for a sealed product; the 'Normal' sub-type when there are several."""
    mine = [r for r in rows if str(r.get("productId")) == product_id]
    mine.sort(key=lambda r: 0 if str(r.get("subTypeName") or "Normal") == "Normal" else 1)
    for row in mine:
        for field in ("marketPrice", "midPrice", "lowPrice"):
            value = row.get(field)
            if isinstance(value, (int, float)) and value > 0:
                return float(value)
    return None


def refresh_sealed_prices(repo, product_ids: Iterable[str], *, fetch: Fetch = tcgcsv_fetch,
                          now: datetime | None = None) -> dict:
    """Price each product id and save it in the singles price table. Returns counts only (safe for public logs)."""
    now = now or datetime.now(timezone.utc)
    wanted = sorted({tcgplayer_product_id(p) for p in product_ids})
    known = repo.prices() if wanted else {}
    by_group: dict[int, list[tuple[str, str]]] = {}
    not_found = 0
    for pid in wanted:
        previous = known.get(price_key(pid)) or {}
        if previous.get("group_id"):
            by_group.setdefault(int(previous["group_id"]), []).append((pid, str(previous.get("name") or "")))
            continue
        located = find_group(pid, fetch)
        if located is None:
            not_found += 1
            continue
        by_group.setdefault(located[0], []).append((pid, located[1]))
    found: dict[str, dict] = {}
    for gid, items in by_group.items():
        rows = _results(fetch(f"{gid}/prices"))
        for pid, name in items:
            usd = _market(rows, pid)
            found[price_key(pid)] = {
                "usd": None if usd is None else f"{usd:.2f}", "group_id": gid, "product_id": pid, "name": name,
                "source": SOURCE, "as_of": now.date().isoformat(), "fetched_at": now.isoformat(),
            }
    if found:
        repo.save_prices(found)
    return {"sealed_products": len(wanted), "priced": sum(1 for d in found.values() if d["usd"]), "not_found": not_found}


def sealed_prices(repo) -> dict[str, dict]:
    """{product id: price document} for every stored sealed price."""
    try:
        stored = repo.prices()
    except Exception:  # noqa: BLE001 - pricing is best-effort; holdings still serve their entered value
        return {}
    return {k[len(KEY_PREFIX):]: v for k, v in stored.items() if k.startswith(KEY_PREFIX)}
