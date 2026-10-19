"""Authenticated routes for MTG singles (Commander decks and the binder).

GET  /v1/mtg-singles                   every card held, by deck, valued at today's price; totals
POST /v1/mtg-singles/import            {deck, text, estimated, save}: read a Moxfield export; save=false previews
                                       (with prices), save=true adds the cards (operator)
POST /v1/mtg-singles/lots/{lot_id}     {action: move|sell|remove|value|paid, ...} (operator)
POST /v1/mtg-singles/refresh-prices    price every printing again now (operator); a daily job also does it
GET  /v1/mtg-singles/history           cards sold or removed
"""
from __future__ import annotations

from fastapi import Header, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .mtg_singles import (SinglesError, apply_action, lookup_prices, lot_document, new_lots, parse_any, price_key,
                          refresh_prices, scryfall_fetch, summary)
from .security import APIKeyAuthenticator, Permission

MAX_IMPORT_CHARS = 400_000


def install_mtg_singles_routes(app, settings, repository, fetch=scryfall_fetch) -> None:
    principals, hashes = {}, {}
    for pid, (cred, roles) in sorted(settings.credentials.items()):
        principals[pid] = roles
        hashes[pid] = APIKeyAuthenticator.hash_credential(cred)
    auth = APIKeyAuthenticator(principals, hashes)

    def authorize(key, permission):
        principal = auth.authenticate(key)
        if principal is None:
            return JSONResponse({"error": {"code": "UNAUTHENTICATED", "message": "valid credentials are required"}}, status_code=401)
        if not principal.permits(permission):
            return JSONResponse({"error": {"code": "FORBIDDEN", "message": "permission is required"}}, status_code=403)
        return None

    def invalid(message, status=422):
        return JSONResponse({"error": {"code": "MTG_SINGLES_INVALID", "message": str(message)}}, status_code=status)

    def current():
        return summary(repository.lots(), repository.prices())

    @app.get("/v1/mtg-singles")
    def read(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key, Permission.RUN_READ)
        return denied or current()

    @app.get("/v1/mtg-singles/history")
    def history(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key, Permission.RUN_READ)
        if denied:
            return denied
        prices = repository.prices()
        return {"lots": [lot_document(lot, prices) for lot in repository.lots(status=None) if lot.status != "held"]}

    @app.post("/v1/mtg-singles/import")
    async def import_cards(request: Request, x_api_key: str | None = Header(default=None)):
        try:
            body = await request.json()
        except Exception:  # noqa: BLE001
            return invalid("body must be JSON")
        body = body if isinstance(body, dict) else {}
        save = bool(body.get("save"))
        denied = authorize(x_api_key, Permission.RUN_SUBMIT if save else Permission.RUN_READ)
        if denied:
            return denied
        text = str(body.get("text") or "")
        if not text.strip():
            return invalid("paste a decklist or a CSV export")
        if len(text) > MAX_IMPORT_CHARS:
            return invalid("that list is too long for one import")
        try:
            cards, unread = parse_any(text, estimated=bool(body.get("estimated")))
            if not cards:
                return invalid("no card lines found (expected lines like 1 Sol Ring (C21) 263)")
            lots = new_lots(cards, str(body.get("deck") or ""))
        except SinglesError as exc:
            return invalid(exc)
        known = repository.prices()
        missing = [c for c in cards if price_key(c) not in known]
        priced_now, price_error = {}, None
        if missing:
            try:
                priced_now = await run_in_threadpool(lambda: lookup_prices(missing, fetch=fetch))
            except Exception as exc:  # noqa: BLE001 - the price source is best-effort; cards still import
                price_error = f"prices could not be fetched right now ({type(exc).__name__}); the daily refresh will add them"
        prices = {**known, **priced_now}
        preview = [lot_document(lot, prices) for lot in lots]
        if save:
            if priced_now:
                repository.save_prices(priced_now)
            repository.save(lots)
        return {"saved": save, "deck": lots[0].deck if lots else None, "cards": preview,
                "card_count": sum(c["quantity"] for c in preview),
                "not_found": [c["name"] for c in preview if c["value_source"] == "UNPRICED"],
                "unread_lines": unread, "price_error": price_error,
                "collection": current() if save else None}

    @app.post("/v1/mtg-singles/lots/{lot_id}")
    async def change(lot_id: str, request: Request, x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key, Permission.RUN_SUBMIT)
        if denied:
            return denied
        try:
            body = await request.json()
            if not isinstance(body, dict):
                raise SinglesError("body must be a JSON object")
            apply_action(repository, lot_id, body)
        except (SinglesError, ValueError, ArithmeticError) as exc:
            return invalid(exc)
        return current()

    @app.post("/v1/mtg-singles/refresh-prices")
    async def refresh(x_api_key: str | None = Header(default=None)):
        denied = authorize(x_api_key, Permission.RUN_SUBMIT)
        if denied:
            return denied
        try:
            result = await run_in_threadpool(lambda: refresh_prices(repository, fetch=fetch))
        except Exception as exc:  # noqa: BLE001
            return invalid(f"prices could not be fetched right now ({type(exc).__name__})", status=502)
        return {"refresh": result, **current()}
