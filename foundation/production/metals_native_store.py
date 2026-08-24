"""UIP-native Metals persistence independent of the standalone Metals runtime."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Iterable, Protocol, Sequence


class CursorLike(Protocol):
    def execute(self, sql: str, parameters: Sequence[object] = ...) -> object: ...
    def executemany(self, sql: str, parameters: Iterable[Sequence[object]]) -> object: ...
    def fetchone(self) -> Sequence[object] | None: ...


class ConnectionLike(Protocol):
    def cursor(self) -> CursorLike: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


@dataclass(frozen=True)
class MetalsObservation:
    series_id: str
    observation_date: str
    value: float
    source: str
    unit: str
    collected_at_utc: str
    run_id: str
    metadata_json: str = "{}"


@dataclass(frozen=True)
class MetalsVehicleObservation:
    ticker: str
    observation_date: str
    close: float
    adjusted_close: float | None
    volume: float | None
    source: str
    collected_at_utc: str
    run_id: str


@dataclass(frozen=True)
class MetalsMarketBenchmarkObservation:
    benchmark_symbol: str
    observation_date: str
    close: float
    source: str
    collected_at_utc: str
    run_id: str


@dataclass(frozen=True)
class MetalsStoreSummary:
    benchmark_observation_count: int
    vehicle_observation_count: int
    latest_benchmark_date: str | None
    latest_vehicle_date: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_SCHEMA_STATEMENTS = (
    """CREATE TABLE IF NOT EXISTS metals_observations (
        series_id TEXT NOT NULL, observation_date TEXT NOT NULL,
        value DOUBLE PRECISION NOT NULL, source TEXT NOT NULL, unit TEXT NOT NULL,
        collected_at_utc TEXT NOT NULL, run_id TEXT NOT NULL, metadata_json TEXT NOT NULL,
        PRIMARY KEY (series_id, observation_date, source))""",
    """CREATE TABLE IF NOT EXISTS metals_vehicle_observations (
        ticker TEXT NOT NULL, observation_date TEXT NOT NULL,
        close DOUBLE PRECISION NOT NULL, adjusted_close DOUBLE PRECISION, volume DOUBLE PRECISION,
        source TEXT NOT NULL, collected_at_utc TEXT NOT NULL, run_id TEXT NOT NULL,
        PRIMARY KEY (ticker, observation_date, source))""",
    """CREATE TABLE IF NOT EXISTS metals_market_benchmark_observations (
        benchmark_symbol TEXT NOT NULL, observation_date TEXT NOT NULL,
        close DOUBLE PRECISION NOT NULL, source TEXT NOT NULL,
        collected_at_utc TEXT NOT NULL, run_id TEXT NOT NULL,
        PRIMARY KEY (benchmark_symbol, observation_date, source))""",
    """CREATE TABLE IF NOT EXISTS metals_native_runs (
        run_id TEXT PRIMARY KEY, started_at_utc TEXT NOT NULL, completed_at_utc TEXT,
        status TEXT NOT NULL, benchmark_rows INTEGER NOT NULL DEFAULT 0,
        vehicle_rows INTEGER NOT NULL DEFAULT 0, error_message TEXT)""",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MetalsNativeStore:
    def __init__(self, connection: ConnectionLike, *, parameter_style: str = "qmark") -> None:
        if parameter_style not in {"qmark", "format"}:
            raise ValueError("parameter_style must be 'qmark' or 'format'")
        self.connection = connection
        self.parameter_style = parameter_style

    def _sql(self, statement: str) -> str:
        return statement if self.parameter_style == "qmark" else statement.replace("?", "%s")

    def initialize(self) -> None:
        cursor = self.connection.cursor()
        try:
            for statement in _SCHEMA_STATEMENTS:
                cursor.execute(statement)
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def begin_run(self, run_id: str, started_at_utc: str | None = None) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                self._sql("INSERT INTO metals_native_runs (run_id, started_at_utc, status, benchmark_rows, vehicle_rows) VALUES (?, ?, ?, ?, ?)"),
                (run_id, started_at_utc or utc_now_iso(), "RUNNING", 0, 0),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def upsert_benchmark_observations(self, rows: Iterable[MetalsObservation]) -> int:
        values = [(r.series_id, r.observation_date, r.value, r.source, r.unit, r.collected_at_utc, r.run_id, r.metadata_json) for r in rows]
        if not values:
            return 0
        sql = self._sql(
            "INSERT INTO metals_observations (series_id, observation_date, value, source, unit, collected_at_utc, run_id, metadata_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(series_id, observation_date, source) DO UPDATE SET "
            "value=excluded.value, unit=excluded.unit, collected_at_utc=excluded.collected_at_utc, run_id=excluded.run_id, metadata_json=excluded.metadata_json"
        )
        cursor = self.connection.cursor()
        try:
            cursor.executemany(sql, values)
            self.connection.commit()
            return len(values)
        except Exception:
            self.connection.rollback()
            raise

    def upsert_vehicle_observations(self, rows: Iterable[MetalsVehicleObservation]) -> int:
        values = [(r.ticker, r.observation_date, r.close, r.adjusted_close, r.volume, r.source, r.collected_at_utc, r.run_id) for r in rows]
        if not values:
            return 0
        sql = self._sql(
            "INSERT INTO metals_vehicle_observations (ticker, observation_date, close, adjusted_close, volume, source, collected_at_utc, run_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(ticker, observation_date, source) DO UPDATE SET "
            "close=excluded.close, adjusted_close=excluded.adjusted_close, volume=excluded.volume, collected_at_utc=excluded.collected_at_utc, run_id=excluded.run_id"
        )
        cursor = self.connection.cursor()
        try:
            cursor.executemany(sql, values)
            self.connection.commit()
            return len(values)
        except Exception:
            self.connection.rollback()
            raise

    def upsert_market_benchmark_observations(self, rows: Iterable[MetalsMarketBenchmarkObservation]) -> int:
        values = [(r.benchmark_symbol, r.observation_date, r.close, r.source, r.collected_at_utc, r.run_id) for r in rows]
        if not values:
            return 0
        sql = self._sql(
            "INSERT INTO metals_market_benchmark_observations (benchmark_symbol, observation_date, close, source, collected_at_utc, run_id) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(benchmark_symbol, observation_date, source) DO UPDATE SET "
            "close=excluded.close, collected_at_utc=excluded.collected_at_utc, run_id=excluded.run_id"
        )
        cursor = self.connection.cursor()
        try:
            cursor.executemany(sql, values)
            self.connection.commit()
            return len(values)
        except Exception:
            self.connection.rollback()
            raise

    def complete_run(self, run_id: str, *, benchmark_rows: int, vehicle_rows: int, completed_at_utc: str | None = None) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                self._sql("UPDATE metals_native_runs SET completed_at_utc=?, status=?, benchmark_rows=?, vehicle_rows=?, error_message=NULL WHERE run_id=?"),
                (completed_at_utc or utc_now_iso(), "PASS", benchmark_rows, vehicle_rows, run_id),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def fail_run(self, run_id: str, error_message: str, completed_at_utc: str | None = None) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                self._sql("UPDATE metals_native_runs SET completed_at_utc=?, status=?, error_message=? WHERE run_id=?"),
                (completed_at_utc or utc_now_iso(), "FAILED", error_message[:4000], run_id),
            )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def summary(self) -> MetalsStoreSummary:
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*), MAX(observation_date) FROM metals_observations")
        benchmark = cursor.fetchone() or (0, None)
        cursor.execute("SELECT COUNT(*), MAX(observation_date) FROM metals_vehicle_observations")
        vehicle = cursor.fetchone() or (0, None)
        return MetalsStoreSummary(int(benchmark[0]), int(vehicle[0]), benchmark[1], vehicle[1])
