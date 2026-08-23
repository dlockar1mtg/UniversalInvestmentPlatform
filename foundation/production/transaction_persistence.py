"""Append-only transaction persistence for UIP application state."""

from __future__ import annotations

from contextlib import closing
from datetime import datetime
from decimal import Decimal
import json
import sqlite3
from typing import Callable, Protocol, Sequence

from .transactions import InvestmentTransaction, TransactionType


class TransactionRepository(Protocol):
    def initialize(self) -> None: ...
    def append(self, transaction: InvestmentTransaction) -> InvestmentTransaction: ...
    def get(self, transaction_id: str) -> InvestmentTransaction: ...
    def list(self, *, limit: int = 100, offset: int = 0) -> tuple[InvestmentTransaction, ...]: ...


_COLUMNS = (
    "transaction_id", "transaction_type", "domain_id", "asset_id", "occurred_at",
    "quantity", "price_per_unit", "fees", "currency", "account_id",
    "destination_account_id", "venue", "external_reference", "notes", "recorded_at",
    "recorded_by", "corrects_transaction_id", "correction_reason", "metadata_json",
)


def _metadata_json(value) -> str:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _validate_window(limit: int, offset: int) -> None:
    if not 1 <= limit <= 500:
        raise ValueError("limit must be between 1 and 500")
    if offset < 0:
        raise ValueError("offset must not be negative")


class SQLiteTransactionRepository:
    """SQLite implementation used for deterministic TXN-1 tests."""

    def __init__(self, connection: sqlite3.Connection):
        self._db = connection

    def initialize(self) -> None:
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("""CREATE TABLE IF NOT EXISTS investment_transactions (
            transaction_id TEXT PRIMARY KEY,
            transaction_type TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            quantity TEXT NOT NULL,
            price_per_unit TEXT,
            fees TEXT NOT NULL,
            currency TEXT NOT NULL,
            account_id TEXT NOT NULL,
            destination_account_id TEXT,
            venue TEXT NOT NULL,
            external_reference TEXT NOT NULL,
            notes TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            recorded_by TEXT NOT NULL,
            corrects_transaction_id TEXT REFERENCES investment_transactions(transaction_id) ON DELETE RESTRICT,
            correction_reason TEXT,
            metadata_json TEXT NOT NULL
        )""")
        self._db.execute("CREATE INDEX IF NOT EXISTS investment_transactions_occurred_idx ON investment_transactions(occurred_at DESC, recorded_at DESC)")
        self._db.execute("CREATE INDEX IF NOT EXISTS investment_transactions_asset_idx ON investment_transactions(domain_id, asset_id, occurred_at DESC)")
        self._db.commit()

    def append(self, transaction: InvestmentTransaction) -> InvestmentTransaction:
        existing = self._db.execute(
            "SELECT transaction_id FROM investment_transactions WHERE transaction_id=?",
            (transaction.transaction_id,),
        ).fetchone()
        if existing:
            raise ValueError("transaction_id already exists; the ledger is append-only")
        if transaction.corrects_transaction_id is not None:
            target = self._db.execute(
                "SELECT transaction_id FROM investment_transactions WHERE transaction_id=?",
                (transaction.corrects_transaction_id,),
            ).fetchone()
            if target is None:
                raise ValueError("corrects_transaction_id does not exist")
        with self._db:
            self._db.execute(
                "INSERT INTO investment_transactions VALUES (" + ",".join("?" * len(_COLUMNS)) + ")",
                _sqlite_values(transaction),
            )
        return transaction

    def get(self, transaction_id: str) -> InvestmentTransaction:
        row = self._db.execute(
            "SELECT " + ",".join(_COLUMNS) + " FROM investment_transactions WHERE transaction_id=?",
            (transaction_id,),
        ).fetchone()
        if row is None:
            raise KeyError(transaction_id)
        return _hydrate(row)

    def list(self, *, limit: int = 100, offset: int = 0) -> tuple[InvestmentTransaction, ...]:
        _validate_window(limit, offset)
        rows = self._db.execute(
            "SELECT " + ",".join(_COLUMNS) +
            " FROM investment_transactions ORDER BY occurred_at DESC,recorded_at DESC,transaction_id DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return tuple(_hydrate(row) for row in rows)


class PostgresTransactionRepository:
    """Neon/PostgreSQL append-only transaction ledger."""

    def __init__(self, connection_factory: Callable[[], object]):
        self._connection_factory = connection_factory

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresTransactionRepository":
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def initialize(self) -> None:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("""CREATE TABLE IF NOT EXISTS investment_transactions (
                transaction_id TEXT PRIMARY KEY,
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('BUY','SELL','TRANSFER','GIFT','ADJUSTMENT')),
                domain_id TEXT NOT NULL,
                asset_id TEXT NOT NULL,
                occurred_at TIMESTAMPTZ NOT NULL,
                quantity NUMERIC NOT NULL CHECK(quantity > 0),
                price_per_unit NUMERIC CHECK(price_per_unit IS NULL OR price_per_unit >= 0),
                fees NUMERIC NOT NULL CHECK(fees >= 0),
                currency TEXT NOT NULL,
                account_id TEXT NOT NULL,
                destination_account_id TEXT,
                venue TEXT NOT NULL,
                external_reference TEXT NOT NULL,
                notes TEXT NOT NULL,
                recorded_at TIMESTAMPTZ NOT NULL,
                recorded_by TEXT NOT NULL,
                corrects_transaction_id TEXT REFERENCES investment_transactions(transaction_id) ON DELETE RESTRICT,
                correction_reason TEXT,
                metadata_json JSONB NOT NULL,
                CHECK((transaction_type='TRANSFER' AND destination_account_id IS NOT NULL AND destination_account_id<>account_id) OR (transaction_type<>'TRANSFER' AND destination_account_id IS NULL)),
                CHECK((corrects_transaction_id IS NULL AND correction_reason IS NULL) OR (corrects_transaction_id IS NOT NULL AND correction_reason IS NOT NULL))
            )""")
            cursor.execute("CREATE INDEX IF NOT EXISTS investment_transactions_occurred_idx ON investment_transactions(occurred_at DESC, recorded_at DESC)")
            cursor.execute("CREATE INDEX IF NOT EXISTS investment_transactions_asset_idx ON investment_transactions(domain_id, asset_id, occurred_at DESC)")

    def append(self, transaction: InvestmentTransaction) -> InvestmentTransaction:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("SELECT transaction_id FROM investment_transactions WHERE transaction_id=%s", (transaction.transaction_id,))
            if cursor.fetchone() is not None:
                raise ValueError("transaction_id already exists; the ledger is append-only")
            if transaction.corrects_transaction_id is not None:
                cursor.execute(
                    "SELECT transaction_id FROM investment_transactions WHERE transaction_id=%s",
                    (transaction.corrects_transaction_id,),
                )
                if cursor.fetchone() is None:
                    raise ValueError("corrects_transaction_id does not exist")
            cursor.execute(
                "INSERT INTO investment_transactions VALUES (" + ",".join(["%s"] * len(_COLUMNS[:-1])) + ",%s::jsonb)",
                _postgres_values(transaction),
            )
        return transaction

    def get(self, transaction_id: str) -> InvestmentTransaction:
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT " + ",".join(_COLUMNS) + " FROM investment_transactions WHERE transaction_id=%s",
                (transaction_id,),
            )
            row = cursor.fetchone()
        if row is None:
            raise KeyError(transaction_id)
        return _hydrate(row)

    def list(self, *, limit: int = 100, offset: int = 0) -> tuple[InvestmentTransaction, ...]:
        _validate_window(limit, offset)
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT " + ",".join(_COLUMNS) +
                " FROM investment_transactions ORDER BY occurred_at DESC,recorded_at DESC,transaction_id DESC LIMIT %s OFFSET %s",
                (limit, offset),
            )
            rows = cursor.fetchall()
        return tuple(_hydrate(row) for row in rows)


def _base_values(item: InvestmentTransaction) -> tuple[object, ...]:
    return (
        item.transaction_id, item.transaction_type.value, item.domain_id, item.asset_id,
        item.occurred_at, item.quantity, item.price_per_unit, item.fees, item.currency,
        item.account_id, item.destination_account_id, item.venue, item.external_reference,
        item.notes, item.recorded_at, item.recorded_by, item.corrects_transaction_id,
        item.correction_reason, _metadata_json(item.metadata),
    )


def _postgres_values(item: InvestmentTransaction) -> tuple[object, ...]:
    return _base_values(item)


def _sqlite_values(item: InvestmentTransaction) -> tuple[object, ...]:
    return tuple(
        value.isoformat() if isinstance(value, datetime)
        else str(value) if isinstance(value, Decimal)
        else value
        for value in _base_values(item)
    )


def _hydrate(row: Sequence[object]) -> InvestmentTransaction:
    metadata = row[18] if isinstance(row[18], dict) else json.loads(str(row[18]))
    return InvestmentTransaction(
        transaction_id=str(row[0]),
        transaction_type=TransactionType(str(row[1])),
        domain_id=str(row[2]),
        asset_id=str(row[3]),
        occurred_at=row[4] if isinstance(row[4], datetime) else datetime.fromisoformat(str(row[4])),
        quantity=Decimal(str(row[5])),
        price_per_unit=None if row[6] is None else Decimal(str(row[6])),
        fees=Decimal(str(row[7])),
        currency=str(row[8]),
        account_id=str(row[9]),
        destination_account_id=None if row[10] is None else str(row[10]),
        venue=str(row[11]),
        external_reference=str(row[12]),
        notes=str(row[13]),
        recorded_at=row[14] if isinstance(row[14], datetime) else datetime.fromisoformat(str(row[14])),
        recorded_by=str(row[15]),
        corrects_transaction_id=None if row[16] is None else str(row[16]),
        correction_reason=None if row[17] is None else str(row[17]),
        metadata=metadata,
    )
