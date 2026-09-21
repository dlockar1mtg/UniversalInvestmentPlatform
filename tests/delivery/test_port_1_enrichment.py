from datetime import datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foundation.production.hosted_portfolio_accounting import install_enriched_portfolio_routes
from foundation.production.portfolio_accounting import derive_portfolio
from foundation.production.portfolio_enrichment import enrich_portfolio
from foundation.production.transaction_persistence import SQLiteTransactionRepository
from foundation.production.transactions import create_transaction


NOW = datetime(2026, 8, 23, 13, 0, tzinfo=timezone.utc)
ASSET_ID = "SECRET_LAIR_V1_1|SL-BB7E07A2986BB4"


def transaction(asset_id=ASSET_ID, domain_id="mtg", price="138.62"):
    return create_transaction(
        transaction_id="holding-buy",
        transaction_type="BUY",
        domain_id=domain_id,
        asset_id=asset_id,
        occurred_at=NOW,
        quantity="1",
        price_per_unit=price,
        fees="0",
        currency="USD",
        account_id="collection",
        recorded_by="test",
        recorded_at=NOW,
    )


class FakePresentationReader:
    def __init__(self, details):
        self.details = details

    def asset_detail(self, domain_id, asset_id):
        return self.details.get((domain_id, asset_id))


def detail(*, authority, current_price, recommendation="BUY_CANDIDATE"):
    return {
        "domain_id": "mtg",
        "asset_id": ASSET_ID,
        "records": {
            "asset": [{
                "record_key": ASSET_ID,
                "payload": {
                    "asset_name": "Drop: Secret Lair x Hatsune Miku: Winter Diva EN - Rainbow Foil Edition",
                    "asset_subclass": "SECRET_LAIR_V1_1",
                    "current_price_usd": current_price,
                    "current_price_authority_available": authority,
                    "_imported_at_utc": "2026-08-21T00:00:00+00:00",
                },
            }],
            "recommendation": [{
                "record_key": ASSET_ID,
                "payload": {
                    "native_purchase_status": recommendation,
                },
            }],
        },
    }


def test_certified_mtg_price_enriches_market_value_and_unrealized_pl():
    accounting = derive_portfolio((transaction(),))
    reader = FakePresentationReader({("mtg", ASSET_ID): detail(authority=True, current_price="150")})
    result = enrich_portfolio(accounting, reader)
    position = result.positions[0]
    assert position.asset_name.startswith("Drop: Secret Lair x Hatsune Miku")
    assert position.current_price == Decimal("150")
    assert position.market_value == Decimal("150")
    assert position.unrealized_pl == Decimal("11.38")
    assert position.pricing_status == "PRICED_CERTIFIED_CURRENT_AUTHORITY"
    assert position.recommendation == "BUY_CANDIDATE"
    assert position.recommendation_source_field == "native_purchase_status"
    document = result.document()
    assert document["pricing_coverage"] == "1/1"
    assert document["known_market_value"] == "150"
    assert document["known_unrealized_pl"] == "11.38"


def test_no_current_price_authority_stays_unpriced_even_if_value_is_present():
    accounting = derive_portfolio((transaction(),))
    reader = FakePresentationReader({("mtg", ASSET_ID): detail(authority=False, current_price="999")})
    position = enrich_portfolio(accounting, reader).positions[0]
    assert position.current_price is None
    assert position.market_value is None
    assert position.unrealized_pl is None
    assert position.pricing_status == "UNPRICED_NO_CERTIFIED_CURRENT_PRICE_AUTHORITY"


def test_missing_price_value_under_certified_authority_stays_unpriced():
    accounting = derive_portfolio((transaction(),))
    reader = FakePresentationReader({("mtg", ASSET_ID): detail(authority=True, current_price=None)})
    position = enrich_portfolio(accounting, reader).positions[0]
    assert position.current_price is None
    assert position.market_value is None
    assert position.pricing_status == "UNPRICED_CERTIFIED_AUTHORITY_HAS_NO_VALUE"


def test_missing_active_asset_identity_fails_closed():
    accounting = derive_portfolio((transaction(),))
    reader = FakePresentationReader({})
    with pytest.raises(ValueError, match="absent from active certified presentation"):
        enrich_portfolio(accounting, reader)


def test_enriched_endpoint_uses_effective_corrected_holding_and_requires_auth():
    repository = SQLiteTransactionRepository(sqlite3.connect(":memory:", check_same_thread=False))
    repository.initialize()
    original = create_transaction(
        transaction_id="original",
        transaction_type="BUY",
        domain_id="mtg",
        asset_id="typed free text",
        occurred_at=NOW,
        quantity="1",
        price_per_unit="138.62",
        account_id="collection",
        recorded_by="test",
        recorded_at=NOW,
    )
    corrected = create_transaction(
        transaction_id="corrected",
        transaction_type="BUY",
        domain_id="mtg",
        asset_id=ASSET_ID,
        occurred_at=NOW,
        quantity="1",
        price_per_unit="138.62",
        account_id="collection",
        recorded_by="test",
        corrects_transaction_id="original",
        correction_reason="governed identity",
        recorded_at=NOW,
    )
    repository.append(original)
    repository.append(corrected)
    reader = FakePresentationReader({("mtg", ASSET_ID): detail(authority=True, current_price="150")})

    app = FastAPI()
    install_enriched_portfolio_routes(
        app,
        {"viewer": ("view-key", ("viewer",))},
        repository,
        reader,
    )
    client = TestClient(app)
    assert client.get("/v1/portfolio/enriched").status_code == 401
    response = client.get("/v1/portfolio/enriched", headers={"X-API-Key": "view-key"})
    assert response.status_code == 200
    document = response.json()
    assert document["position_count"] == 1
    assert document["effective_transaction_count"] == 1
    assert document["superseded_transaction_count"] == 1
    assert document["positions"][0]["asset_id"] == ASSET_ID
    assert document["positions"][0]["market_value"] == "150"


def test_enriched_endpoint_fails_closed_when_identity_not_in_active_presentation():
    repository = SQLiteTransactionRepository(sqlite3.connect(":memory:", check_same_thread=False))
    repository.initialize()
    repository.append(transaction())
    app = FastAPI()
    install_enriched_portfolio_routes(
        app,
        {"viewer": ("view-key", ("viewer",))},
        repository,
        FakePresentationReader({}),
    )
    client = TestClient(app)
    response = client.get("/v1/portfolio/enriched", headers={"X-API-Key": "view-key"})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PORTFOLIO_ENRICHMENT_BLOCKED"


def metals_vehicle_transaction(asset_id="metals:vehicle:BIL", price="91.51"):
    return create_transaction(
        transaction_id="metals-vehicle-buy",
        transaction_type="BUY",
        domain_id="metals",
        asset_id=asset_id,
        occurred_at=NOW,
        quantity="0.081962",
        price_per_unit=price,
        fees="0",
        currency="USD",
        account_id="brokerage",
        recorded_by="test",
        recorded_at=NOW,
    )


def metals_current_price_detail(
    *,
    asset_id="metals:vehicle:BIL",
    ticker="BIL",
    current_price="91.55999755859375",
    source_authority="UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1",
    price_semantics="UNADJUSTED_CLOSE",
):
    return {
        "domain_id": "metals",
        "asset_id": asset_id,
        "records": {
            "metals_current_price": [{
                "record_key": asset_id,
                "payload": {
                    "asset_id": asset_id,
                    "ticker": ticker,
                    "observation_date": "2026-09-18",
                    "current_price_usd": current_price,
                    "price_semantics": price_semantics,
                    "source_system": "universal-market-provider",
                    "source_authority": source_authority,
                    "source_package_id": "metals-native-history-2026-09-18",
                    "source_run_id": "gha-35377147561",
                    "collected_at_utc": "2026-09-18T17:56:04.289629+00:00",
                },
            }],
        },
    }


def test_registered_metals_vehicle_can_be_enriched_from_certified_rich_price_without_generic_asset():
    accounting = derive_portfolio((metals_vehicle_transaction(),))
    reader = FakePresentationReader({
        ("metals", "metals:vehicle:BIL"): metals_current_price_detail(),
    })
    position = enrich_portfolio(accounting, reader).positions[0]
    assert position.asset_name == "SPDR Bloomberg 1-3 Month T-Bill ETF"
    assert position.asset_symbol == "BIL"
    assert position.asset_subclass == "cash_proxy"
    assert position.current_price == Decimal("91.55999755859375")
    assert position.current_price_authority_available is True
    assert position.pricing_status == "PRICED_CERTIFIED_CURRENT_AUTHORITY"
    assert position.recommendation is None
    assert position.recommendation_source_field is None
    assert position.freshness == "2026-09-18"


def test_registered_metals_vehicle_without_current_price_remains_unpriced_not_blocked():
    accounting = derive_portfolio((metals_vehicle_transaction(),))
    reader = FakePresentationReader({
        ("metals", "metals:vehicle:BIL"): {
            "domain_id": "metals",
            "asset_id": "metals:vehicle:BIL",
            "records": {"risk": [{"record_key": "metals:vehicle:BIL", "payload": {}}]},
        },
    })
    position = enrich_portfolio(accounting, reader).positions[0]
    assert position.asset_name == "SPDR Bloomberg 1-3 Month T-Bill ETF"
    assert position.current_price is None
    assert position.market_value is None
    assert position.pricing_status == "UNPRICED_NO_CERTIFIED_CURRENT_PRICE_AUTHORITY"
    assert position.recommendation is None


def test_unknown_metals_vehicle_still_fails_closed_even_with_spoofed_current_price():
    asset_id = "metals:vehicle:NOT_REGISTERED"
    accounting = derive_portfolio((metals_vehicle_transaction(asset_id=asset_id),))
    reader = FakePresentationReader({
        ("metals", asset_id): metals_current_price_detail(
            asset_id=asset_id,
            ticker="NOT_REGISTERED",
        ),
    })
    with pytest.raises(ValueError, match="not an enabled governed Metals vehicle"):
        enrich_portfolio(accounting, reader)


def test_registered_metals_vehicle_rejects_wrong_current_price_authority():
    accounting = derive_portfolio((metals_vehicle_transaction(),))
    reader = FakePresentationReader({
        ("metals", "metals:vehicle:BIL"): metals_current_price_detail(
            source_authority="UNAUTHORIZED_SOURCE",
        ),
    })
    with pytest.raises(ValueError, match="unexpected Metals current-price authority"):
        enrich_portfolio(accounting, reader)


def test_registered_metals_vehicle_rejects_wrong_price_semantics():
    accounting = derive_portfolio((metals_vehicle_transaction(),))
    reader = FakePresentationReader({
        ("metals", "metals:vehicle:BIL"): metals_current_price_detail(
            price_semantics="ADJUSTED_CLOSE",
        ),
    })
    with pytest.raises(ValueError, match="unexpected Metals current-price semantics"):
        enrich_portfolio(accounting, reader)
