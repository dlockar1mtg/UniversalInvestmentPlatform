"""Configuration for the Universal Import Engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImportEngineConfig:
    """Resolved filesystem configuration for an import-engine run."""

    repository_root: Path
    database_path: Path
    schema_root: Path
    integration_root: Path
    validation_root: Path

    @classmethod
    def from_repository_root(cls, repository_root: Path) -> "ImportEngineConfig":
        root = repository_root.resolve()

        return cls(
            repository_root=root,
            database_path=root
            / "data"
            / "universal"
            / "universal_investment.duckdb",
            schema_root=root / "schemas" / "v1" / "csv",
            integration_root=root / "data" / "integration",
            validation_root=root / "data" / "validation" / "imports",
        )

    def ensure_directories(self) -> None:
        """Create writable runtime directories if they do not exist."""

        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.validation_root.mkdir(parents=True, exist_ok=True)