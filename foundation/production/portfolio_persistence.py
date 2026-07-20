"""Immutable, content-addressed portfolio snapshot persistence."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import sqlite3
from types import MappingProxyType
from typing import Callable, Mapping, Protocol, Sequence

from .portfolio import PortfolioPosition


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class PortfolioSnapshot:
    snapshot_id: str
    fingerprint: str
    imported_at: datetime
    as_of: datetime
    positions: tuple[PortfolioPosition, ...]
    total_cost_basis: Decimal
    total_market_value: Decimal
    currency: str
    metadata: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.snapshot_id.strip() or len(self.fingerprint) != 64:
            raise ValueError("snapshot identity and SHA-256 fingerprint are required")
        if self.imported_at.tzinfo is None or self.as_of.tzinfo is None:
            raise ValueError("snapshot timestamps must be timezone-aware")
        if not self.positions:
            raise ValueError("snapshot must contain at least one position")
        if tuple(sorted(self.positions, key=lambda item: item.position_id)) != self.positions:
            raise ValueError("snapshot positions must be ordered by position_id")
        if len({item.position_id for item in self.positions}) != len(self.positions):
            raise ValueError("snapshot position identities must be unique")
        if any(item.currency != self.currency for item in self.positions):
            raise ValueError("snapshot positions must use one currency")
        if self.total_cost_basis != sum((item.cost_basis for item in self.positions), Decimal(0)):
            raise ValueError("snapshot cost basis must reconcile")
        if self.total_market_value != sum((item.market_value for item in self.positions), Decimal(0)):
            raise ValueError("snapshot market value must reconcile")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def summary(self) -> Mapping[str, object]:
        return MappingProxyType({
            "as_of": self.as_of.isoformat(),
            "currency": self.currency,
            "fingerprint": self.fingerprint,
            "imported_at": self.imported_at.isoformat(),
            "position_count": len(self.positions),
            "snapshot_id": self.snapshot_id,
            "total_cost_basis": str(self.total_cost_basis),
            "total_market_value": str(self.total_market_value),
        })


def create_portfolio_snapshot(
    positions: Sequence[PortfolioPosition],
    *,
    imported_at: datetime | None = None,
    metadata: Mapping[str, object] | None = None,
) -> PortfolioSnapshot:
    ordered = tuple(sorted(positions, key=lambda item: item.position_id))
    if not ordered:
        raise ValueError("at least one portfolio position is required")
    currencies = {item.currency for item in ordered}
    if len(currencies) != 1:
        raise ValueError("a snapshot must use exactly one currency")
    canonical_positions = [dict(item.canonical()) for item in ordered]
    fingerprint = hashlib.sha256(_canonical_json(canonical_positions).encode("utf-8")).hexdigest()
    now = imported_at or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("imported_at must be timezone-aware")
    return PortfolioSnapshot(
        snapshot_id=f"portfolio-{fingerprint[:24]}",
        fingerprint=fingerprint,
        imported_at=now,
        as_of=max(item.as_of for item in ordered),
        positions=ordered,
        total_cost_basis=sum((item.cost_basis for item in ordered), Decimal(0)),
        total_market_value=sum((item.market_value for item in ordered), Decimal(0)),
        currency=next(iter(currencies)),
        metadata=metadata or {},
    )


class PortfolioSnapshotRepository(Protocol):
    def initialize(self) -> None: ...
    def save(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot: ...
    def get(self, snapshot_id: str) -> PortfolioSnapshot: ...
    def latest(self) -> PortfolioSnapshot | None: ...
    def history(self, limit: int = 20) -> tuple[PortfolioSnapshot, ...]: ...


_POSITION_COLUMNS = (
    "position_id", "account_id", "portfolio_group", "asset_type", "asset_id",
    "quantity", "cost_basis", "market_value", "currency", "as_of", "symbol",
    "name", "provider_symbol", "target_weight", "liquidity_class", "notes",
)


class SQLitePortfolioSnapshotRepository:
    """SQLite implementation used for deterministic tests and local evaluation."""

    def __init__(self, connection: sqlite3.Connection):
        self._db = connection

    def initialize(self) -> None:
        self._db.execute("PRAGMA foreign_keys=ON")
        self._db.execute("""CREATE TABLE IF NOT EXISTS portfolio_snapshots (
            snapshot_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL UNIQUE,
            imported_at TEXT NOT NULL, as_of TEXT NOT NULL, position_count INTEGER NOT NULL,
            total_cost_basis TEXT NOT NULL, total_market_value TEXT NOT NULL,
            currency TEXT NOT NULL, metadata_json TEXT NOT NULL
        )""")
        self._db.execute("""CREATE TABLE IF NOT EXISTS portfolio_snapshot_positions (
            snapshot_id TEXT NOT NULL REFERENCES portfolio_snapshots(snapshot_id) ON DELETE RESTRICT,
            position_id TEXT NOT NULL, account_id TEXT NOT NULL, portfolio_group TEXT NOT NULL,
            asset_type TEXT NOT NULL, asset_id TEXT NOT NULL, quantity TEXT NOT NULL,
            cost_basis TEXT NOT NULL, market_value TEXT NOT NULL, currency TEXT NOT NULL,
            as_of TEXT NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL,
            provider_symbol TEXT NOT NULL, target_weight TEXT, liquidity_class TEXT NOT NULL,
            notes TEXT NOT NULL, PRIMARY KEY(snapshot_id, position_id)
        )""")
        self._db.commit()

    def save(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        existing = self._db.execute(
            "SELECT snapshot_id FROM portfolio_snapshots WHERE fingerprint=?", (snapshot.fingerprint,)
        ).fetchone()
        if existing:
            return self.get(existing[0])
        collision = self._db.execute(
            "SELECT fingerprint FROM portfolio_snapshots WHERE snapshot_id=?", (snapshot.snapshot_id,)
        ).fetchone()
        if collision:
            raise ValueError("snapshot_id already contains different content")
        with self._db:
            self._db.execute(
                "INSERT INTO portfolio_snapshots VALUES (?,?,?,?,?,?,?,?,?)",
                (snapshot.snapshot_id, snapshot.fingerprint, snapshot.imported_at.isoformat(),
                 snapshot.as_of.isoformat(), len(snapshot.positions), str(snapshot.total_cost_basis),
                 str(snapshot.total_market_value), snapshot.currency, _canonical_json(dict(snapshot.metadata))),
            )
            self._db.executemany(
                "INSERT INTO portfolio_snapshot_positions VALUES (" + ",".join("?" * 17) + ")",
                [_sqlite_position_values(snapshot.snapshot_id, item) for item in snapshot.positions],
            )
        return snapshot

    def get(self, snapshot_id: str) -> PortfolioSnapshot:
        row = self._db.execute("SELECT * FROM portfolio_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
        if row is None:
            raise KeyError(snapshot_id)
        positions = self._db.execute(
            "SELECT " + ",".join(_POSITION_COLUMNS) +
            " FROM portfolio_snapshot_positions WHERE snapshot_id=? ORDER BY position_id", (snapshot_id,)
        ).fetchall()
        return _hydrate_snapshot(row, positions)

    def latest(self) -> PortfolioSnapshot | None:
        row = self._db.execute(
            "SELECT snapshot_id FROM portfolio_snapshots ORDER BY imported_at DESC,snapshot_id DESC LIMIT 1"
        ).fetchone()
        return None if row is None else self.get(row[0])

    def history(self, limit: int = 20) -> tuple[PortfolioSnapshot, ...]:
        if not 1 <= limit <= 100:
            raise ValueError("history limit must be between 1 and 100")
        rows = self._db.execute(
            "SELECT snapshot_id FROM portfolio_snapshots ORDER BY imported_at DESC,snapshot_id DESC LIMIT ?", (limit,)
        ).fetchall()
        return tuple(self.get(row[0]) for row in rows)


class PostgresPortfolioSnapshotRepository:
    """Neon/PostgreSQL implementation with transactional snapshot writes."""

    def __init__(self, connection_factory: Callable[[], object]):
        self._connection_factory = connection_factory

    @classmethod
    def from_dsn(cls, dsn: str) -> "PostgresPortfolioSnapshotRepository":
        if not dsn.strip():
            raise ValueError("PostgreSQL DSN must not be blank")
        import psycopg
        return cls(lambda: psycopg.connect(dsn))

    def initialize(self) -> None:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("""CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                snapshot_id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL UNIQUE,
                imported_at TIMESTAMPTZ NOT NULL, as_of TIMESTAMPTZ NOT NULL,
                position_count INTEGER NOT NULL CHECK(position_count > 0),
                total_cost_basis NUMERIC NOT NULL CHECK(total_cost_basis >= 0),
                total_market_value NUMERIC NOT NULL CHECK(total_market_value >= 0),
                currency TEXT NOT NULL, metadata_json JSONB NOT NULL
            )""")
            cursor.execute("""CREATE TABLE IF NOT EXISTS portfolio_snapshot_positions (
                snapshot_id TEXT NOT NULL REFERENCES portfolio_snapshots(snapshot_id) ON DELETE RESTRICT,
                position_id TEXT NOT NULL, account_id TEXT NOT NULL, portfolio_group TEXT NOT NULL,
                asset_type TEXT NOT NULL, asset_id TEXT NOT NULL, quantity NUMERIC NOT NULL,
                cost_basis NUMERIC NOT NULL, market_value NUMERIC NOT NULL, currency TEXT NOT NULL,
                as_of TIMESTAMPTZ NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL,
                provider_symbol TEXT NOT NULL, target_weight NUMERIC, liquidity_class TEXT NOT NULL,
                notes TEXT NOT NULL, PRIMARY KEY(snapshot_id, position_id)
            )""")
            cursor.execute("CREATE INDEX IF NOT EXISTS portfolio_snapshots_imported_at_idx ON portfolio_snapshots(imported_at DESC)")

    def save(self, snapshot: PortfolioSnapshot) -> PortfolioSnapshot:
        with closing(self._connection_factory()) as db, db, db.cursor() as cursor:
            cursor.execute("SELECT snapshot_id FROM portfolio_snapshots WHERE fingerprint=%s", (snapshot.fingerprint,))
            existing = cursor.fetchone()
            if existing:
                return self.get(existing[0])
            cursor.execute("SELECT fingerprint FROM portfolio_snapshots WHERE snapshot_id=%s", (snapshot.snapshot_id,))
            if cursor.fetchone():
                raise ValueError("snapshot_id already contains different content")
            cursor.execute(
                "INSERT INTO portfolio_snapshots VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)",
                (snapshot.snapshot_id, snapshot.fingerprint, snapshot.imported_at, snapshot.as_of,
                 len(snapshot.positions), snapshot.total_cost_basis, snapshot.total_market_value,
                 snapshot.currency, _canonical_json(dict(snapshot.metadata))),
            )
            cursor.executemany(
                "INSERT INTO portfolio_snapshot_positions VALUES (" + ",".join(["%s"] * 17) + ")",
                [_position_values(snapshot.snapshot_id, item) for item in snapshot.positions],
            )
        return snapshot

    def get(self, snapshot_id: str) -> PortfolioSnapshot:
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute("SELECT * FROM portfolio_snapshots WHERE snapshot_id=%s", (snapshot_id,))
            row = cursor.fetchone()
            if row is None:
                raise KeyError(snapshot_id)
            cursor.execute(
                "SELECT " + ",".join(_POSITION_COLUMNS) +
                " FROM portfolio_snapshot_positions WHERE snapshot_id=%s ORDER BY position_id", (snapshot_id,)
            )
            positions = cursor.fetchall()
        return _hydrate_snapshot(row, positions)

    def latest(self) -> PortfolioSnapshot | None:
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute("SELECT snapshot_id FROM portfolio_snapshots ORDER BY imported_at DESC,snapshot_id DESC LIMIT 1")
            row = cursor.fetchone()
        return None if row is None else self.get(row[0])

    def history(self, limit: int = 20) -> tuple[PortfolioSnapshot, ...]:
        if not 1 <= limit <= 100:
            raise ValueError("history limit must be between 1 and 100")
        with closing(self._connection_factory()) as db, db.cursor() as cursor:
            cursor.execute(
                "SELECT snapshot_id FROM portfolio_snapshots ORDER BY imported_at DESC,snapshot_id DESC LIMIT %s", (limit,)
            )
            rows = cursor.fetchall()
        return tuple(self.get(row[0]) for row in rows)


def _position_values(snapshot_id: str, item: PortfolioPosition) -> tuple[object, ...]:
    return (
        snapshot_id, item.position_id, item.account_id, item.portfolio_group, item.asset_type,
        item.asset_id, item.quantity, item.cost_basis, item.market_value, item.currency, item.as_of,
        item.symbol, item.name, item.provider_symbol, item.target_weight, item.liquidity_class, item.notes,
    )


def _sqlite_position_values(snapshot_id: str, item: PortfolioPosition) -> tuple[object, ...]:
    values = _position_values(snapshot_id, item)
    return tuple(
        value.isoformat() if isinstance(value, datetime)
        else str(value) if isinstance(value, Decimal)
        else value
        for value in values
    )


def _hydrate_snapshot(row: Sequence[object], positions: Sequence[Sequence[object]]) -> PortfolioSnapshot:
    hydrated = tuple(
        PortfolioPosition(
            str(item[0]), str(item[1]), str(item[2]), str(item[3]), str(item[4]), Decimal(str(item[5])),
            Decimal(str(item[6])), Decimal(str(item[7])), str(item[8]),
            item[9] if isinstance(item[9], datetime) else datetime.fromisoformat(str(item[9])),
            str(item[10]), str(item[11]), str(item[12]),
            None if item[13] is None else Decimal(str(item[13])), str(item[14]), str(item[15]),
        ) for item in positions
    )
    metadata = row[8] if isinstance(row[8], dict) else json.loads(str(row[8]))
    return PortfolioSnapshot(
        str(row[0]), str(row[1]),
        row[2] if isinstance(row[2], datetime) else datetime.fromisoformat(str(row[2])),
        row[3] if isinstance(row[3], datetime) else datetime.fromisoformat(str(row[3])),
        hydrated, Decimal(str(row[5])), Decimal(str(row[6])), str(row[7]), metadata,
    )
