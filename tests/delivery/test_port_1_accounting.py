from datetime import datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from foundation.production.hosted_portfolio_accounting import install_transaction_portfolio_routes
from foundation.production.portfolio_accounting import derive_portfolio, resolve_effective_transactions
from foundation.production.transaction_persistence import SQLiteTransactionRepository
from foundation.production.transactions import create_transaction


NOW = datetime(2026, 8, 23, 12, 0, tzinfo=timezone.utc)


def txn(*, transaction_id, transaction_type="BUY", domain_id="mtg", asset_id="mtg:test", quantity="1", price="100", fees="0", account="collection", destination=None, corrects=None, reason=None, occurred=NOW):
    return create_transaction(
        transaction_id=transaction_id,
        transaction_type=transaction_type,
        domain_id=domain_id,
        asset_id=asset_id,
        occurred_at=occurred,
        quantity=quantity,
        price_per_unit=price,
        fees=fees,
        currency="USD",
        account_id=account,
        destination_account_id=destination,
        recorded_by="test",
        corrects_transaction_id=corrects,
        correction_reason=reason,
        recorded_at=NOW,
    )


def test_correction_chain_counts_one_effective_buy_not_two():
    original = txn(transaction_id="original", asset_id="typed free text", price="138.62")
    corrected = txn(
        transaction_id="corrected",
        asset_id="SECRET_LAIR_V1_1SL-BB7E07A2986BB4",
        price="138.62",
        corrects="original",
        reason="replace free-text identity",
    )
    effective = resolve_effective_transactions((original, corrected))
    assert [item.transaction_id for item in effective.items] == ["corrected"]
    assert effective.superseded_transaction_ids == ("original",)

    portfolio = derive_portfolio((original, corrected))
    assert portfolio.effective_transaction_count == 1
    assert portfolio.superseded_transaction_count == 1
    assert len(portfolio.positions) == 1
    position = portfolio.positions[0]
    assert position.asset_id == "SECRET_LAIR_V1_1SL-BB7E07A2986BB4"
    assert position.quantity == Decimal("1")
    assert position.cost_basis == Decimal("138.62")
    assert position.average_cost == Decimal("138.62")
    assert position.basis_status == "KNOWN"


def test_buy_fees_are_included_in_cost_basis():
    portfolio = derive_portfolio((txn(transaction_id="buy", quantity="2", price="10", fees="3"),))
    position = portfolio.positions[0]
    assert position.quantity == Decimal("2")
    assert position.cost_basis == Decimal("23")
    assert position.average_cost == Decimal("11.5")


def test_unknown_basis_stays_unknown_not_zero():
    portfolio = derive_portfolio((txn(transaction_id="gift", transaction_type="GIFT", price=None),))
    position = portfolio.positions[0]
    assert position.basis_status == "UNKNOWN"
    assert position.cost_basis is None
    assert position.average_cost is None
    assert position.unknown_basis_quantity == Decimal("1")


def test_known_basis_sell_calculates_realized_pl_and_remaining_basis():
    buy = txn(transaction_id="buy", quantity="2", price="100", fees="0")
    sell = txn(transaction_id="sell", transaction_type="SELL", quantity="1", price="150", fees="5")
    portfolio = derive_portfolio((buy, sell))
    position = portfolio.positions[0]
    assert position.quantity == Decimal("1")
    assert position.cost_basis == Decimal("100")
    assert position.realized_pl == Decimal("45")


def test_transfer_moves_basis_without_changing_total_quantity():
    buy = txn(transaction_id="buy", quantity="2", price="50", account="vault")
    transfer = txn(
        transaction_id="transfer",
        transaction_type="TRANSFER",
        quantity="1",
        price=None,
        account="vault",
        destination="display-case",
    )
    portfolio = derive_portfolio((buy, transfer))
    assert sum((item.quantity for item in portfolio.positions), Decimal("0")) == Decimal("2")
    by_account = {item.account_id: item for item in portfolio.positions}
    assert by_account["vault"].cost_basis == Decimal("50")
    assert by_account["display-case"].cost_basis == Decimal("50")


def test_partial_basis_sell_fails_closed_without_lot_policy():
    known = txn(transaction_id="known", quantity="1", price="100")
    unknown = txn(transaction_id="unknown", transaction_type="GIFT", quantity="1", price=None)
    sell = txn(transaction_id="sell", transaction_type="SELL", quantity="1", price="150")
    with pytest.raises(ValueError, match="partial-basis"):
        derive_portfolio((known, unknown, sell))


def test_correction_fork_is_rejected_as_ambiguous():
    original = txn(transaction_id="original")
    first = txn(transaction_id="first", corrects="original", reason="first")
    second = txn(transaction_id="second", corrects="original", reason="second")
    with pytest.raises(ValueError, match="fork"):
        resolve_effective_transactions((original, first, second))


def test_derived_portfolio_endpoint_requires_auth_and_returns_effective_holding():
    repository = SQLiteTransactionRepository(sqlite3.connect(":memory:", check_same_thread=False))
    repository.initialize()
    original = txn(transaction_id="original", asset_id="typed free text", price="138.62")
    corrected = txn(
        transaction_id="corrected",
        asset_id="SECRET_LAIR_V1_1SL-BB7E07A2986BB4",
        price="138.62",
        corrects="original",
        reason="replace free-text identity",
    )
    repository.append(original)
    repository.append(corrected)

    app = FastAPI()
    install_transaction_portfolio_routes(
        app,
        {"viewer": ("view-key", ("viewer",))},
        repository,
    )
    client = TestClient(app)
    assert client.get("/v1/portfolio/derived").status_code == 401
    response = client.get("/v1/portfolio/derived", headers={"X-API-Key": "view-key"})
    assert response.status_code == 200
    document = response.json()
    assert document["position_count"] == 1
    assert document["effective_transaction_count"] == 1
    assert document["superseded_transaction_count"] == 1
    assert document["positions"][0]["quantity"] == "1"
    assert document["positions"][0]["asset_id"] == "SECRET_LAIR_V1_1SL-BB7E07A2986BB4"
    assert document["pricing_status"] == "NOT_JOINED_YET"
