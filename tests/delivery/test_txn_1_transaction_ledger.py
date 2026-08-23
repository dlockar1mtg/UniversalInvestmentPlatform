from datetime import datetime, timezone
from decimal import Decimal
import sqlite3

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from foundation.production.hosted_transactions import install_hosted_transaction_routes
from foundation.production.http_service import HTTPServiceSettings, create_http_app
from foundation.production.persistence import SQLiteProductionRepository
from foundation.production.transaction_persistence import SQLiteTransactionRepository
from foundation.production.transactions import TransactionType, create_transaction


def _repo():
    repo = SQLiteTransactionRepository(sqlite3.connect(":memory:", check_same_thread=False))
    repo.initialize()
    return repo


def _client(tmp_path):
    production = SQLiteProductionRepository(tmp_path / "production.sqlite3")
    production.initialize()
    settings = HTTPServiceSettings(credentials={
        "viewer": ("view-key", ("viewer",)),
        "operator": ("operate-key", ("operator",)),
    })
    app = create_http_app(settings, production)
    ledger = _repo()
    install_hosted_transaction_routes(app, settings, ledger)
    return TestClient(app), ledger


def _payload(**overrides):
    data = {
        "transaction_type": "BUY",
        "domain_id": "crypto",
        "asset_id": "bitcoin",
        "occurred_at": "2026-08-22T12:30:00-05:00",
        "quantity": "0.01",
        "price_per_unit": "64000",
        "fees": "4.50",
        "currency": "USD",
        "account_id": "coinbase",
        "venue": "Coinbase",
        "external_reference": "",
        "notes": "Initial retained holding entry",
    }
    data.update(overrides)
    return data


def test_transaction_model_preserves_unknown_price_and_requires_transfer_destination():
    item = create_transaction(
        transaction_type="GIFT",
        domain_id="mtg",
        asset_id="gifted-sealed-product",
        occurred_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        quantity="1",
        price_per_unit=None,
        account_id="collection",
        recorded_by="operator",
    )
    assert item.price_per_unit is None
    assert item.transaction_type is TransactionType.GIFT
    with pytest.raises(ValueError, match="destination_account_id"):
        create_transaction(
            transaction_type="TRANSFER",
            domain_id="crypto",
            asset_id="bitcoin",
            occurred_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            quantity="0.01",
            price_per_unit=None,
            account_id="wallet-a",
            recorded_by="operator",
        )


def test_repository_is_append_only_and_correction_is_a_new_row():
    repo = _repo()
    original = create_transaction(
        transaction_type="BUY", domain_id="metals", asset_id="gold",
        occurred_at=datetime(2026, 8, 1, tzinfo=timezone.utc), quantity="2",
        price_per_unit="3400", account_id="vault", recorded_by="operator",
        transaction_id="txn-original",
    )
    repo.append(original)
    with pytest.raises(ValueError, match="already exists"):
        repo.append(original)
    correction = create_transaction(
        transaction_type="BUY", domain_id="metals", asset_id="gold",
        occurred_at=datetime(2026, 8, 1, tzinfo=timezone.utc), quantity="2",
        price_per_unit="3395", account_id="vault", recorded_by="operator",
        transaction_id="txn-correction", corrects_transaction_id="txn-original",
        correction_reason="Correct purchase price",
    )
    repo.append(correction)
    items = repo.list(limit=10, offset=0)
    assert {item.transaction_id for item in items} == {"txn-original", "txn-correction"}
    assert repo.get("txn-original").price_per_unit == Decimal("3400")
    assert repo.get("txn-correction").corrects_transaction_id == "txn-original"


def test_api_requires_operator_to_write_but_viewer_can_read(tmp_path):
    service, _ = _client(tmp_path)
    assert service.post("/v1/transactions", json=_payload()).status_code == 401
    assert service.post("/v1/transactions", json=_payload(), headers={"X-API-Key": "view-key"}).status_code == 403
    created = service.post("/v1/transactions", json=_payload(), headers={"X-API-Key": "operate-key"})
    assert created.status_code == 201
    document = created.json()["transaction"]
    assert document["domain_id"] == "crypto"
    assert document["price_per_unit"] == "64000"
    listed = service.get("/v1/transactions", headers={"X-API-Key": "view-key"})
    assert listed.status_code == 200
    assert len(listed.json()["items"]) == 1


def test_api_correction_never_overwrites_original(tmp_path):
    service, ledger = _client(tmp_path)
    first = service.post("/v1/transactions", json=_payload(), headers={"X-API-Key": "operate-key"})
    original_id = first.json()["transaction"]["transaction_id"]
    corrected = service.post(
        "/v1/transactions",
        json=_payload(
            price_per_unit="63500",
            corrects_transaction_id=original_id,
            correction_reason="Correct broker confirmation",
        ),
        headers={"X-API-Key": "operate-key"},
    )
    assert corrected.status_code == 201
    correction_id = corrected.json()["transaction"]["transaction_id"]
    assert correction_id != original_id
    assert ledger.get(original_id).price_per_unit == Decimal("64000")
    assert ledger.get(correction_id).price_per_unit == Decimal("63500")


def test_invalid_transaction_is_fail_closed_without_write(tmp_path):
    service, ledger = _client(tmp_path)
    response = service.post(
        "/v1/transactions",
        json=_payload(quantity="0"),
        headers={"X-API-Key": "operate-key"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "TRANSACTION_INVALID"
    assert ledger.list(limit=10, offset=0) == ()
