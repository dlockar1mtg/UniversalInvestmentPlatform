"""Deterministic diagnostics and graceful shutdown coordination."""

from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sqlite3
from types import MappingProxyType
from typing import Mapping

from .config import ProductionRuntimeConfig


class ShutdownController:
    def __init__(self):
        self._requested = False
        self._reason: str | None = None

    def request(self, reason: str) -> None:
        if not reason.strip():
            raise ValueError("shutdown reason must not be blank")
        if not self._requested:
            self._requested, self._reason = True, reason

    @property
    def requested(self) -> bool:
        return self._requested

    @property
    def reason(self) -> str | None:
        return self._reason


@dataclass(frozen=True)
class OperationalStatus:
    environment: str
    database_available: bool
    artifact_directory_available: bool
    run_counts: Mapping[str, int]
    job_counts: Mapping[str, int]


def collect_operational_status(config: ProductionRuntimeConfig) -> OperationalStatus:
    runs, jobs = {}, {}
    database_available = config.database_path.is_file()
    if database_available:
        try:
            with closing(sqlite3.connect(config.database_path)) as db:
                runs = dict(db.execute("SELECT status,COUNT(*) FROM production_runs GROUP BY status ORDER BY status").fetchall())
                jobs = dict(db.execute("SELECT status,COUNT(*) FROM production_jobs GROUP BY status ORDER BY status").fetchall())
        except sqlite3.DatabaseError:
            database_available = False
    return OperationalStatus(
        config.environment, database_available, config.artifact_directory.is_dir(),
        MappingProxyType(runs), MappingProxyType(jobs),
    )
