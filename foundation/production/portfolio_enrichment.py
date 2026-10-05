"""Certified identity, price, and recommendation enrichment for PORT-1 holdings."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from foundation.production.metals_registry import load_metals_registry
from foundation.presentation.crypto_current_price_projection import (
    AUTHORITY as CRYPTO_PRICE_AUTHORITY,
    PRESENTATION_SEMANTICS as CRYPTO_PRESENTATION_SEMANTICS,
    PRICE_SEMANTICS as CRYPTO_PRICE_SEMANTICS,
    SOURCE_TABLE as CRYPTO_PRICE_SOURCE_TABLE,
)
from foundation.production.portfolio_accounting import PortfolioAccountingResult, PortfolioPosition


class PresentationAssetReader(Protocol):
    def asset_detail(self, domain_id: str, asset_id: str) -> dict[str, object] | None: ...


@dataclass(frozen=True)
class EnrichedPortfolioPosition:
    domain_id: str
    asset_id: str
    asset_name: str
    asset_symbol: str | None
    asset_subclass: str | None
    account_id: str
    currency: str
    quantity: Decimal
    basis_status: str
    cost_basis: Decimal | None
    average_cost: Decimal | None
    realized_pl: Decimal | None
    current_price: Decimal | None
    current_price_authority_available: bool
    pricing_status: str
    market_value: Decimal | None
    unrealized_pl: Decimal | None
    recommendation: str | None
    recommendation_source_field: str | None
    freshness: str | None

    def document(self) -> dict[str, object]:
        def amount(value: Decimal | None) -> str | None:
            return None if value is None else str(value)

        return {
            "domain_id": self.domain_id,
            "asset_id": self.asset_id,
            "asset_name": self.asset_name,
            "asset_symbol": self.asset_symbol,
            "asset_subclass": self.asset_subclass,
            "account_id": self.account_id,
            "currency": self.currency,
            "quantity": str(self.quantity),
            "basis_status": self.basis_status,
            "cost_basis": amount(self.cost_basis),
            "average_cost": amount(self.average_cost),
            "realized_pl": amount(self.realized_pl),
            "current_price": amount(self.current_price),
            "current_price_authority_available": self.current_price_authority_available,
            "pricing_status": self.pricing_status,
            "market_value": amount(self.market_value),
            "unrealized_pl": amount(self.unrealized_pl),
            "recommendation": self.recommendation,
            "recommendation_source_field": self.recommendation_source_field,
            "freshness": self.freshness,
        }


@dataclass(frozen=True)
class EnrichedPortfolioResult:
    positions: tuple[EnrichedPortfolioPosition, ...]
    effective_transaction_count: int
    superseded_transaction_count: int

    def document(self) -> dict[str, object]:
        priced = tuple(item for item in self.positions if item.market_value is not None)
        known_basis = tuple(item for item in self.positions if item.cost_basis is not None)
        market_value = sum((item.market_value for item in priced if item.market_value is not None), Decimal("0"))
        cost_basis = sum((item.cost_basis for item in known_basis if item.cost_basis is not None), Decimal("0"))
        unrealized = sum(
            (item.unrealized_pl for item in self.positions if item.unrealized_pl is not None),
            Decimal("0"),
        )
        return {
            "positions": [item.document() for item in self.positions],
            "position_count": len(self.positions),
            "effective_transaction_count": self.effective_transaction_count,
            "superseded_transaction_count": self.superseded_transaction_count,
            "priced_position_count": len(priced),
            "pricing_coverage": (
                "0/0" if not self.positions else f"{len(priced)}/{len(self.positions)}"
            ),
            "known_basis_position_count": len(known_basis),
            "basis_coverage": (
                "0/0" if not self.positions else f"{len(known_basis)}/{len(self.positions)}"
            ),
            "known_market_value": str(market_value),
            "known_cost_basis": str(cost_basis),
            "known_unrealized_pl": str(unrealized),
            "market_value_complete": len(priced) == len(self.positions),
            "cost_basis_complete": len(known_basis) == len(self.positions),
        }


def _first_payload(detail: dict[str, object], record_type: str) -> dict[str, object] | None:
    records = detail.get("records", {})
    if not isinstance(records, dict):
        return None
    values = records.get(record_type, [])
    if not isinstance(values, list) or not values:
        return None
    item = values[0]
    if not isinstance(item, dict):
        return None
    payload = item.get("payload")
    return dict(payload) if isinstance(payload, dict) else None


def _decimal(value: object | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _recommendation(payload: dict[str, object] | None) -> tuple[str | None, str | None]:
    if payload is None:
        return None, None
    # A daily model decision (Secret Lair v2) travels beside the certified native status; prefer it.
    if payload.get("model_version") and payload.get("model_purchase_status"):
        return str(payload["model_purchase_status"]), "model_purchase_status"
    for field in ("native_purchase_status", "native_recommendation", "recommendation"):
        value = payload.get(field)
        if value is not None and str(value).strip():
            return str(value), field
    return None, None


def _freshness(asset: dict[str, object]) -> str | None:
    for field in (
        "last_updated_at_utc",
        "last_observed_date",
        "_imported_at_utc",
        "observation_date",
        "collected_at_utc",
    ):
        value = asset.get(field)
        if value is not None and str(value).strip():
            return str(value)
    return None


def _enrich_position(
    position: PortfolioPosition,
    reader: PresentationAssetReader,
) -> EnrichedPortfolioPosition:
    detail = reader.asset_detail(position.domain_id, position.asset_id)
    if detail is None:
        raise ValueError(
            f"holding identity is absent from active certified presentation: "
            f"{position.domain_id}/{position.asset_id}"
        )
    asset = _first_payload(detail, "asset")
    recommendation_payload = _first_payload(detail, "recommendation")
    recommendation, recommendation_field = _recommendation(recommendation_payload)

    if asset is not None:
        asset_name = str(asset.get("asset_name") or position.asset_id)
        asset_symbol = None if asset.get("asset_symbol") is None else str(asset.get("asset_symbol"))
        asset_subclass = (
            None if asset.get("asset_subclass") is None else str(asset.get("asset_subclass"))
        )
        authority = asset.get("current_price_authority_available") is True
        raw_price = asset.get("current_price_usd")
        freshness = _freshness(asset)
        if position.domain_id == "crypto" and not authority:
            certified_price = _first_payload(detail, "crypto_current_price")
            if certified_price is not None:
                expected = {
                    "universal_asset_id": position.asset_id,
                    "asset_id": position.asset_id.removeprefix("crypto:"),
                    "authority_id": CRYPTO_PRICE_AUTHORITY,
                    "source_table": CRYPTO_PRICE_SOURCE_TABLE,
                    "price_semantics": CRYPTO_PRICE_SEMANTICS,
                    "presentation_semantics": CRYPTO_PRESENTATION_SEMANTICS,
                    "schema_version": "1.0.0",
                    "methodology_version": "1.0.0",
                    "_certified_manifest_status": "CRYPTO_CURRENT_PRICE_V1_PASS",
                }
                certified_digest = str(certified_price.get("_certified_csv_sha256") or "").strip().lower()
                valid_digest = (
                    len(certified_digest) == 64
                    and all(ch in "0123456789abcdef" for ch in certified_digest)
                )
                if (
                    any(certified_price.get(key) != value for key, value in expected.items())
                    or not valid_digest
                ):
                    raise ValueError(f"certified Crypto current-price authority mismatch: {position.asset_id}")
                authority = True
                raw_price = certified_price.get("current_price_usd")
                freshness = _freshness(certified_price)
    elif position.domain_id == "metals" and position.asset_id.startswith("metals:vehicle:"):
        registry = load_metals_registry()
        vehicle = next(
            (
                item
                for item in registry.vehicles
                if item.vehicle_id == position.asset_id and item.enabled
            ),
            None,
        )
        if vehicle is None:
            raise ValueError(
                f"holding is not an enabled governed Metals vehicle: {position.asset_id}"
            )
        current_price_record = _first_payload(detail, "metals_current_price")
        asset_name = vehicle.name
        asset_symbol = vehicle.ticker
        asset_subclass = vehicle.vehicle_type
        recommendation = None
        recommendation_field = None
        if current_price_record is None:
            authority = False
            raw_price = None
            freshness = None
        else:
            if current_price_record.get("asset_id") != position.asset_id:
                raise ValueError(
                    f"certified Metals current-price identity mismatch: {position.asset_id}"
                )
            if current_price_record.get("ticker") != vehicle.ticker:
                raise ValueError(
                    f"certified Metals current-price ticker mismatch: {position.asset_id}"
                )
            if (
                current_price_record.get("source_authority")
                != "UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1"
            ):
                raise ValueError(
                    f"unexpected Metals current-price authority: {position.asset_id}"
                )
            if current_price_record.get("price_semantics") != "UNADJUSTED_CLOSE":
                raise ValueError(
                    f"unexpected Metals current-price semantics: {position.asset_id}"
                )
            authority = True
            raw_price = current_price_record.get("current_price_usd")
            freshness = _freshness(current_price_record)
    else:
        raise ValueError(
            f"holding has no active certified asset record: {position.domain_id}/{position.asset_id}"
        )

    if not authority:
        current_price = None
        pricing_status = "UNPRICED_NO_CERTIFIED_CURRENT_PRICE_AUTHORITY"
    elif raw_price is None:
        current_price = None
        pricing_status = "UNPRICED_CERTIFIED_AUTHORITY_HAS_NO_VALUE"
    else:
        current_price = _decimal(raw_price)
        if current_price is None or not current_price.is_finite() or current_price <= 0:
            raise ValueError(
                f"invalid certified current price for {position.domain_id}/{position.asset_id}"
            )
        pricing_status = "PRICED_CERTIFIED_CURRENT_AUTHORITY"

    market_value = None if current_price is None else position.quantity * current_price
    unrealized = (
        None
        if market_value is None or position.cost_basis is None
        else market_value - position.cost_basis
    )
    return EnrichedPortfolioPosition(
        domain_id=position.domain_id,
        asset_id=position.asset_id,
        asset_name=asset_name,
        asset_symbol=asset_symbol,
        asset_subclass=asset_subclass,
        account_id=position.account_id,
        currency=position.currency,
        quantity=position.quantity,
        basis_status=position.basis_status,
        cost_basis=position.cost_basis,
        average_cost=position.average_cost,
        realized_pl=position.realized_pl,
        current_price=current_price,
        current_price_authority_available=authority,
        pricing_status=pricing_status,
        market_value=market_value,
        unrealized_pl=unrealized,
        recommendation=recommendation,
        recommendation_source_field=recommendation_field,
        freshness=freshness,
    )


def enrich_portfolio(
    accounting: PortfolioAccountingResult,
    reader: PresentationAssetReader,
) -> EnrichedPortfolioResult:
    positions = tuple(_enrich_position(item, reader) for item in accounting.positions)
    return EnrichedPortfolioResult(
        positions=positions,
        effective_transaction_count=accounting.effective_transaction_count,
        superseded_transaction_count=accounting.superseded_transaction_count,
    )
