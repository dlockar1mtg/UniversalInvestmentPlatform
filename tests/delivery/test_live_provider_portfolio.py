import json
from urllib.parse import parse_qs, urlparse

import pytest

from foundation.production.portfolio import PortfolioCSVValidationError, import_portfolio_csv, preview_portfolio_csv
from foundation.production.providers import AlphaVantageProvider, FREDProvider, ProviderError

HEADER = "position_id,account_id,portfolio_group,asset_type,asset_id,quantity,cost_basis,market_value,currency,as_of,symbol,name,provider_symbol,target_weight,liquidity_class,notes\n"


def test_valid_csv_normalizes_and_is_order_invariant():
    one = "p2,a1,metals,metal,gold-1,2,3000,4800,usd,2026-07-20T12:00:00Z,GLD,Gold,GLD,0.2,liquid,note\n"
    two = "p1,a1,etf,etf,spy,3,1200,1800,USD,2026-07-20T12:00:00+00:00,spy,S&P 500,spy,0.4,liquid,\n"
    a = preview_portfolio_csv(HEADER + one + two, is_text=True)
    b = preview_portfolio_csv(HEADER + two + one, is_text=True)
    assert a.valid and a.fingerprint == b.fingerprint
    assert [item.position_id for item in a.positions] == ["p1", "p2"]
    assert a.positions[0].symbol == "SPY"


def test_invalid_rows_return_row_numbered_errors_and_strict_import_fails():
    row = "p1,,bad,bad,x,-1,nope,3,US,2026-07-20,,,,2,,\n"
    report = preview_portfolio_csv(HEADER + row, is_text=True)
    assert not report.valid
    assert {error.field for error in report.errors} >= {"account_id", "portfolio_group", "asset_type", "quantity", "cost_basis", "currency", "as_of", "target_weight"}
    with pytest.raises(PortfolioCSVValidationError) as caught:
        import_portfolio_csv(HEADER + row, is_text=True)
    assert caught.value.report == report


def test_duplicate_ids_and_unknown_header_are_rejected():
    bad_header = HEADER.rstrip("\n") + ",marketvalue\n"
    report = preview_portfolio_csv(bad_header, is_text=True)
    assert report.errors[0].field == "marketvalue"
    row = "p1,a,etf,etf,x,1,1,1,USD,2026-07-20T00:00:00Z,,,,,,\n"
    duplicate = preview_portfolio_csv(HEADER + row + row, is_text=True)
    assert any(error.field == "position_id" for error in duplicate.errors)


def test_alpha_vantage_quote_is_normalized_and_parameters_encoded():
    def transport(url, timeout):
        query = parse_qs(urlparse(url).query)
        assert query["apikey"] == ["secret"] and query["symbol"] == ["SPY"] and timeout == 3
        return json.dumps({"Global Quote": {"05. price": "621.25", "07. latest trading day": "2026-07-17"}}).encode()
    quote = AlphaVantageProvider("secret", transport=transport, timeout=3).quote("spy")
    assert str(quote.price) == "621.25" and quote.provider == "alpha_vantage"


def test_alpha_vantage_provider_errors_do_not_expose_api_key():
    provider = AlphaVantageProvider("top-secret", transport=lambda *_: json.dumps({"Note": "rate limit"}).encode())
    with pytest.raises(ProviderError) as caught:
        provider.quote("SPY")
    assert "top-secret" not in str(caught.value)


def test_fred_uses_latest_numeric_observation_and_skips_missing_value():
    def transport(url, timeout):
        query = parse_qs(urlparse(url).query)
        assert query["file_type"] == ["json"] and query["sort_order"] == ["desc"]
        return json.dumps({"observations": [
            {"date": "2026-07-16", "value": "."},
            {"date": "2026-07-09", "value": "6.15"},
        ]}).encode()
    result = FREDProvider("secret", transport=transport).latest("mortgage30us")
    assert result.series_id == "MORTGAGE30US" and str(result.value) == "6.15"
