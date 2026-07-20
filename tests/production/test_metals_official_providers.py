from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pytest
from openpyxl import Workbook

from foundation.production.providers import (
    EIAUraniumProvider,
    ProviderError,
    WorldBankCommodityProvider,
)


def _world_bank_fixture(*, include_silver: bool = True) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Monthly Prices"
    headers = ["Date", "Gold"]
    if include_silver:
        headers.append("Silver")
    headers.extend(["Copper", "Platinum"])
    sheet.append(["World Bank commodity data"])
    sheet.append(headers)
    first = [datetime(2026, 5, 1), 3300]
    if include_silver:
        first.append(36)
    first.extend([9500, 1100])
    sheet.append(first)
    second = [datetime(2026, 6, 1), 3400]
    if include_silver:
        second.append(38)
    second.extend([9700, 1150])
    sheet.append(second)
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()


def test_eia_uranium_provider_returns_latest_annual_official_price() -> None:
    html = b"""
    <html><body><h1>Uranium marketing annual report</h1>
    <table>
      <tr><th>Delivery year</th><th>Spot price</th><th>Weighted-average price</th></tr>
      <tr><td>2024</td><td>$77.10</td><td>$52.35</td></tr>
      <tr><td>2025</td><td>$79.20</td><td>$55.40</td></tr>
    </table></body></html>
    """
    provider = EIAUraniumProvider(transport=lambda url, timeout: html, timeout=4)
    result = provider.latest()
    assert result.asset == "uranium"
    assert str(result.value) == "55.40"
    assert result.observation_date.isoformat() == "2025-12-31"
    assert result.provider == "eia"
    assert result.series_id == "EIA::URANIUM_WEIGHTED_AVG"


def test_eia_schema_drift_is_rejected() -> None:
    provider = EIAUraniumProvider(transport=lambda *_: b"<html><body>changed</body></html>")
    with pytest.raises(ProviderError, match="signature"):
        provider.latest()


def test_official_provider_transport_failure_does_not_expose_details() -> None:
    def failed_transport(url: str, timeout: float) -> bytes:
        raise RuntimeError("secret internal network detail")

    provider = EIAUraniumProvider(transport=failed_transport)
    with pytest.raises(ProviderError) as caught:
        provider.latest()
    assert "secret internal network detail" not in str(caught.value)
    assert "RuntimeError" in str(caught.value)


def test_world_bank_provider_normalizes_latest_monthly_values() -> None:
    payload = _world_bank_fixture()
    provider = WorldBankCommodityProvider(
        transport=lambda url, timeout: payload, timeout=6,
        workbook_url="fixture://monthly.xlsx",
    )
    results = provider.latest(["gold", "silver", "copper", "platinum"])
    by_asset = {result.asset: result for result in results}
    assert list(by_asset) == ["gold", "silver", "copper", "platinum"]
    assert str(by_asset["gold"].value) == "3400"
    assert str(by_asset["silver"].value) == "38"
    assert by_asset["copper"].observation_date.isoformat() == "2026-06-01"
    assert by_asset["platinum"].unit == "usd_per_troy_ounce"
    assert by_asset["gold"].series_id == "WORLD_BANK::GOLD_MONTHLY"


def test_world_bank_provider_accepts_year_month_text_dates() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Monthly"
    sheet.append(["Date", "Gold", "Silver"])
    sheet.append(["2026M05", 3300, 36])
    sheet.append(["2026M06", 3400, 38])
    output = BytesIO()
    workbook.save(output)
    provider = WorldBankCommodityProvider(
        transport=lambda *_: output.getvalue(), workbook_url="fixture://monthly.xlsx"
    )
    results = provider.latest(["gold", "silver"])
    assert {result.observation_date.isoformat() for result in results} == {"2026-06-01"}


def test_world_bank_schema_drift_and_invalid_assets_are_rejected() -> None:
    provider = WorldBankCommodityProvider(
        transport=lambda *_: _world_bank_fixture(include_silver=False),
        workbook_url="fixture://monthly.xlsx",
    )
    with pytest.raises(ProviderError, match="silver column"):
        provider.latest(["gold", "silver"])
    with pytest.raises(ValueError, match="unsupported"):
        provider.latest(["unobtainium"])


def test_world_bank_invalid_workbook_is_rejected() -> None:
    provider = WorldBankCommodityProvider(
        transport=lambda *_: b"not-an-xlsx", workbook_url="fixture://monthly.xlsx"
    )
    with pytest.raises(ProviderError, match="valid XLSX"):
        provider.latest(["gold"])


def test_world_bank_discovers_current_workbook_from_stable_index() -> None:
    workbook = _world_bank_fixture()
    requested: list[str] = []

    def transport(url: str, timeout: float) -> bytes:
        requested.append(url)
        if url == WorldBankCommodityProvider.INDEX_URL:
            return b'<a href="https://current.example/CMO-Historical-Data-Monthly.xlsx">Monthly prices</a>'
        return workbook

    provider = WorldBankCommodityProvider(transport=transport)
    results = provider.latest(["gold", "silver"])
    assert len(results) == 2
    assert requested == [
        WorldBankCommodityProvider.INDEX_URL,
        "https://current.example/CMO-Historical-Data-Monthly.xlsx",
    ]


def test_world_bank_missing_discovery_link_uses_guarded_fallback() -> None:
    workbook = _world_bank_fixture()
    requested: list[str] = []

    def transport(url: str, timeout: float) -> bytes:
        requested.append(url)
        return b"<html>no workbook</html>" if url == WorldBankCommodityProvider.INDEX_URL else workbook

    provider = WorldBankCommodityProvider(transport=transport)
    results = provider.latest(["gold"])
    assert len(results) == 1
    assert requested == [
        WorldBankCommodityProvider.INDEX_URL,
        WorldBankCommodityProvider.FALLBACK_URL,
    ]
