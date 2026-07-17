"""Load benchmark definitions from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .benchmark_registry import BenchmarkDefinition, BenchmarkRegistry


def load_benchmark_registry(path: str | Path) -> BenchmarkRegistry:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("PyYAML is required to load benchmark definitions.") from exc

    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(config_path)

    parsed = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(parsed, Mapping):
        raise ValueError("Benchmark YAML root must be a mapping.")

    rows = parsed.get("benchmarks")
    if not isinstance(rows, Mapping):
        raise ValueError("Benchmark YAML must contain a benchmarks mapping.")

    definitions = []
    for asset_class, row in rows.items():
        if not isinstance(row, Mapping):
            raise TypeError("Each benchmark definition must be a mapping.")
        definitions.append(
            BenchmarkDefinition(
                benchmark_id=row["benchmark_id"],
                asset_class=asset_class,
                description=row["description"],
                source=row.get("source", "configured"),
            )
        )
    return BenchmarkRegistry(definitions)
