"""Live Alpha Vantage and FRED adapters with injectable HTTP transport."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
import json
import os
from typing import Callable, Mapping
from urllib.parse import urlencode
from urllib.request import urlopen

Transport = Callable[[str, float], bytes]


class ProviderError(RuntimeError):
    pass


def _default_transport(url: str, timeout: float) -> bytes:
    with urlopen(url, timeout=timeout) as response:  # noqa: S310 - fixed provider URLs
        return response.read()


def _json_request(base_url: str, parameters: Mapping[str, str], transport: Transport, timeout: float) -> dict:
    url = f"{base_url}?{urlencode(parameters)}"
    try:
        payload = json.loads(transport(url, timeout).decode("utf-8"))
    except Exception as exc:
        raise ProviderError(f"provider request failed: {type(exc).__name__}") from exc
    if not isinstance(payload, dict):
        raise ProviderError("provider returned an invalid payload")
    for key in ("Error Message", "Note", "Information", "error_message"):
        if payload.get(key):
            raise ProviderError(f"provider rejected request: {payload[key]}")
    return payload


@dataclass(frozen=True)
class MarketQuote:
    symbol: str
    price: Decimal
    trading_date: date
    provider: str


@dataclass(frozen=True)
class EconomicObservation:
    series_id: str
    value: Decimal
    observation_date: date
    provider: str = "fred"


class AlphaVantageProvider:
    BASE_URL = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str | None = None, *, transport: Transport = _default_transport, timeout: float = 15.0):
        self._api_key = (api_key or os.getenv("UIIP_ALPHA_VANTAGE_API_KEY", "")).strip()
        if not self._api_key:
            raise ValueError("UIIP_ALPHA_VANTAGE_API_KEY is required")
        self._transport = transport
        self._timeout = timeout

    def quote(self, symbol: str) -> MarketQuote:
        normalized = symbol.strip().upper()
        if not normalized:
            raise ValueError("symbol is required")
        payload = _json_request(self.BASE_URL, {
            "function": "GLOBAL_QUOTE", "symbol": normalized, "apikey": self._api_key,
        }, self._transport, self._timeout)
        quote = payload.get("Global Quote")
        if not isinstance(quote, dict) or not quote:
            raise ProviderError("Alpha Vantage returned no quote")
        try:
            price = Decimal(str(quote["05. price"]))
            trading_date = date.fromisoformat(str(quote["07. latest trading day"]))
        except (KeyError, InvalidOperation, ValueError) as exc:
            raise ProviderError("Alpha Vantage quote fields were invalid") from exc
        if not price.is_finite() or price < 0:
            raise ProviderError("Alpha Vantage quote price was invalid")
        return MarketQuote(normalized, price, trading_date, "alpha_vantage")


class FREDProvider:
    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    def __init__(self, api_key: str | None = None, *, transport: Transport = _default_transport, timeout: float = 15.0):
        self._api_key = (api_key or os.getenv("UIIP_FRED_API_KEY", "")).strip()
        if not self._api_key:
            raise ValueError("UIIP_FRED_API_KEY is required")
        self._transport = transport
        self._timeout = timeout

    def latest(self, series_id: str) -> EconomicObservation:
        normalized = series_id.strip().upper()
        if not normalized:
            raise ValueError("series_id is required")
        payload = _json_request(self.BASE_URL, {
            "series_id": normalized, "api_key": self._api_key, "file_type": "json",
            "sort_order": "desc", "limit": "10",
        }, self._transport, self._timeout)
        observations = payload.get("observations", [])
        for observation in observations if isinstance(observations, list) else []:
            value = str(observation.get("value", "."))
            if value == ".":
                continue
            try:
                parsed = Decimal(value)
                observed = date.fromisoformat(str(observation["date"]))
            except (InvalidOperation, KeyError, ValueError) as exc:
                raise ProviderError("FRED observation fields were invalid") from exc
            if parsed.is_finite():
                return EconomicObservation(normalized, parsed, observed)
        raise ProviderError("FRED returned no numeric observation")
