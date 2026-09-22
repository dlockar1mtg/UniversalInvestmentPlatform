"""Immutable manual snapshots for externally held stocks and ETFs."""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import sqlite3
from typing import Callable, Protocol, Sequence


@dataclass(frozen=True)
class ManualHoldingSnapshot:
    snapshot_id: str
    fingerprint: str
    symbol: str
    asset_name: str
    asset_type: str
    account_id: str
    as_of: datetime
    shares: Decimal
    cost_basis: Decimal
    current_value: Decimal
    recorded_at: datetime
    recorded_by: str
    notes: str = ""
    authority_state: str = "MANUAL_USER_ENTERED_EXTERNAL_HOLDING"

    def __post_init__(self):
        if not self.symbol.strip():
            raise ValueError("symbol is required")
        if self.asset_type not in {"ETF", "STOCK"}:
            raise ValueError("asset_type must be ETF or STOCK")
        if not self.account_id.strip():
            raise ValueError("account_id is required")
        if self.as_of.tzinfo is None or self.recorded_at.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")
        if self.shares < 0 or self.cost_basis < 0 or self.current_value < 0:
            raise ValueError("shares, cost_basis, and current_value must be non-negative")

    @property
    def gain_loss(self) -> Decimal:
        return self.current_value - self.cost_basis

    @property
    def return_pct(self):
        return None if self.cost_basis == 0 else self.gain_loss / self.cost_basis * Decimal(100)

    @property
    def average_cost(self):
        return None if self.shares == 0 else self.cost_basis / self.shares

    @property
    def current_price(self):
        return None if self.shares == 0 else self.current_value / self.shares

    def document(self):
        return {
            "snapshot_id": self.snapshot_id,
            "fingerprint": self.fingerprint,
            "symbol": self.symbol,
            "asset_name": self.asset_name,
            "asset_type": self.asset_type,
            "account_id": self.account_id,
            "as_of": self.as_of.isoformat(),
            "shares": str(self.shares),
            "cost_basis": str(self.cost_basis),
            "current_value": str(self.current_value),
            "gain_loss": str(self.gain_loss),
            "return_pct": None if self.return_pct is None else str(self.return_pct),
            "average_cost": None if self.average_cost is None else str(self.average_cost),
            "current_price": None if self.current_price is None else str(self.current_price),
            "recorded_at": self.recorded_at.isoformat(),
            "recorded_by": self.recorded_by,
            "notes": self.notes,
            "authority_state": self.authority_state,
        }


class ManualHoldingRepository(Protocol):
    def initialize(self) -> None: ...
    def save(self, item: ManualHoldingSnapshot) -> ManualHoldingSnapshot: ...
    def current(self) -> tuple[ManualHoldingSnapshot, ...]: ...
    def history(self, symbol: str, account_id: str, limit: int = 20) -> tuple[ManualHoldingSnapshot, ...]: ...


def create_manual_holding_snapshot(
    *,
    symbol: str,
    asset_name: str,
    asset_type: str,
    account_id: str,
    as_of: datetime,
    shares: Decimal,
    cost_basis: Decimal,
    current_value: Decimal,
    recorded_by: str,
    notes: str = "",
    recorded_at: datetime | None = None,
) -> ManualHoldingSnapshot:
    if as_of.tzinfo is None:
        raise ValueError("as_of must include timezone")
    normalized_symbol = symbol.strip().upper()
    normalized_type = asset_type.strip().upper()
    normalized_account = account_id.strip()
    payload = {
        "symbol": normalized_symbol,
        "asset_name": asset_name.strip(),
        "asset_type": normalized_type,
        "account_id": normalized_account,
        "as_of": as_of.isoformat(),
        "shares": str(shares),
        "cost_basis": str(cost_basis),
        "current_value": str(current_value),
        "notes": notes.strip(),
    }
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()
    return ManualHoldingSnapshot(
        snapshot_id=f"manual-holding-{fingerprint[:24]}",
        fingerprint=fingerprint,
        symbol=normalized_symbol,
        asset_name=asset_name.strip(),
        asset_type=normalized_type,
        account_id=normalized_account,
        as_of=as_of,
        shares=shares,
        cost_basis=cost_basis,
        current_value=current_value,
        recorded_at=recorded_at or datetime.now(timezone.utc),
        recorded_by=recorded_by,
        notes=notes.strip(),
    )


_COLS = (
    "snapshot_id", "fingerprint", "symbol", "asset_name", "asset_type", "account_id",
    "as_of", "shares", "cost_basis", "current_value", "recorded_at", "recorded_by",
    "notes", "authority_state",
)


def _hydrate(row: Sequence[object]) -> ManualHoldingSnapshot:
    return ManualHoldingSnapshot(
        snapshot_id=str(row[0]),
        fingerprint=str(row[1]),
        symbol=str(row[2]),
        asset_name=str(row[3]),
        asset_type=str(row[4]),
        account_id=str(row[5]),
        as_of=row[6] if isinstance(row[6], datetime) else datetime.fromisoformat(str(row[6])),
        shares=Decimal(str(row[7])),
        cost_basis=Decimal(str(row[8])),
        current_value=Decimal(str(row[9])),
        recorded_at=row[10] if isinstance(row[10], datetime) else datetime.fromisoformat(str(row[10])),
        recorded_by=str(row[11]),
        notes=str(row[12]),
        authority_state=str(row[13]),
    )


class SQLiteManualHoldingRepository:
    def __init__(self, connection: sqlite3.Connection):
        self._db = connection

    def initialize(self):
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS manual_holding_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            fingerprint TEXT NOT NULL UNIQUE,
            symbol TEXT NOT NULL,
            asset_name TEXT NOT NULL,
            asset_type TEXT NOT NULL,
            account_id TEXT NOT NULL,
            as_of TEXT NOT NULL,
            shares TEXT NOT NULL,
            cost_basis TEXT NOT NULL,
            current_value TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            recorded_by TEXT NOT NULL,
            notes TEXT NOT NULL,
            authority_state TEXT NOT NULL)"""
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS manual_holding_current_idx "
            "ON manual_holding_snapshots(symbol, account_id, as_of DESC, recorded_at DESC)"
        )
        self._db.commit()

    def save(self, item):
        row = self._db.execute(
            "SELECT " + ",".join(_COLS) + " FROM manual_holding_snapshots WHERE fingerprint=?",
            (item.fingerprint,),
        ).fetchone()
        if row:
            return _hydrate(row)
        with self._db:
            self._db.execute(
                "INSERT INTO manual_holding_snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                tuple(
                    value.isoformat() if isinstance(value, datetime)
                    else str(value) if isinstance(value, Decimal)
                    else value
                    for value in (
                        item.snapshot_id, item.fingerprint, item.symbol, item.asset_name,
                        item.asset_type, item.account_id, item.as_of, item.shares,
                        item.cost_basis, item.current_value, item.recorded_at,
                        item.recorded_by, item.notes, item.authority_state,
                    )
                ),
            )
        return item

    def current(self):
        rows = self._db.execute(
            "SELECT " + ",".join(_COLS) + " FROM manual_holding_snapshots s "
            "WHERE snapshot_id=(SELECT s2.snapshot_id FROM manual_holding_snapshots s2 "
            "WHERE s2.symbol=s.symbol AND s2.account_id=s.account_id "
            "ORDER BY s2.as_of DESC,s2.recorded_at DESC,s2.snapshot_id DESC LIMIT 1) "
            "ORDER BY asset_type,symbol,account_id"
        ).fetchall()
        return tuple(_hydrate(row) for row in rows)

    def history(self, symbol, account_id, limit=20):
        if not 1 <= limit <= 100:
            raise ValueError("history limit must be between 1 and 100")
        rows = self._db.execute(
            "SELECT " + ",".join(_COLS) + " FROM manual_holding_snapshots "
            "WHERE symbol=? AND account_id=? "
            "ORDER BY as_of DESC,recorded_at DESC,snapshot_id DESC LIMIT ?",
            (symbol.strip().upper(), account_id.strip(), limit),
        ).fetchall()
        return tuple(_hydrate(row) for row in rows)


class PostgresManualHoldingRepository:
    def __init__(self, connection_factory: Callable[[], object]):
        self._connection_factory = connection_factory

    @classmethod
    def from_dsn(cls, dsn: str):
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def initialize(self):
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS manual_holding_snapshots (
                snapshot_id TEXT PRIMARY KEY,
                fingerprint TEXT NOT NULL UNIQUE,
                symbol TEXT NOT NULL,
                asset_name TEXT NOT NULL,
                asset_type TEXT NOT NULL CHECK(asset_type IN ('ETF','STOCK')),
                account_id TEXT NOT NULL,
                as_of TIMESTAMPTZ NOT NULL,
                shares NUMERIC NOT NULL CHECK(shares>=0),
                cost_basis NUMERIC NOT NULL CHECK(cost_basis>=0),
                current_value NUMERIC NOT NULL CHECK(current_value>=0),
                recorded_at TIMESTAMPTZ NOT NULL,
                recorded_by TEXT NOT NULL,
                notes TEXT NOT NULL,
                authority_state TEXT NOT NULL)"""
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS manual_holding_current_idx "
                "ON manual_holding_snapshots(symbol, account_id, as_of DESC, recorded_at DESC)"
            )

    def save(self, item):
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute(
                "SELECT " + ",".join(_COLS) + " FROM manual_holding_snapshots WHERE fingerprint=%s",
                (item.fingerprint,),
            )
            row = cursor.fetchone()
            if row:
                return _hydrate(row)
            cursor.execute(
                "INSERT INTO manual_holding_snapshots VALUES "
                "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    item.snapshot_id, item.fingerprint, item.symbol, item.asset_name,
                    item.asset_type, item.account_id, item.as_of, item.shares,
                    item.cost_basis, item.current_value, item.recorded_at,
                    item.recorded_by, item.notes, item.authority_state,
                ),
            )
        return item

    def current(self):
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT ON (symbol,account_id) " + ",".join(_COLS) +
                " FROM manual_holding_snapshots "
                "ORDER BY symbol,account_id,as_of DESC,recorded_at DESC,snapshot_id DESC"
            )
            rows = cursor.fetchall()
        return tuple(sorted((_hydrate(row) for row in rows), key=lambda item:(item.asset_type,item.symbol,item.account_id)))

    def history(self, symbol, account_id, limit=20):
        if not 1 <= limit <= 100:
            raise ValueError("history limit must be between 1 and 100")
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT " + ",".join(_COLS) + " FROM manual_holding_snapshots "
                "WHERE symbol=%s AND account_id=%s "
                "ORDER BY as_of DESC,recorded_at DESC,snapshot_id DESC LIMIT %s",
                (symbol.strip().upper(), account_id.strip(), limit),
            )
            rows = cursor.fetchall()
        return tuple(_hydrate(row) for row in rows)
