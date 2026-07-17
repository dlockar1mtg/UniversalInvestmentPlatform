from pathlib import Path

import pytest

from foundation.intelligence.validation import (
    BenchmarkDefinition,
    BenchmarkRegistry,
    load_benchmark_registry,
)


def test_registry_resolves_by_asset_class() -> None:
    registry = BenchmarkRegistry(
        [
            BenchmarkDefinition(
                benchmark_id="VOO",
                asset_class="etf",
                description="S&P 500 benchmark",
            )
        ]
    )
    assert registry.resolve_for_asset_class("etf").benchmark_id == "VOO"


def test_registry_rejects_duplicate_asset_class() -> None:
    registry = BenchmarkRegistry(
        [
            BenchmarkDefinition(
                benchmark_id="VOO",
                asset_class="etf",
                description="S&P 500 benchmark",
            )
        ]
    )
    with pytest.raises(ValueError):
        registry.register(
            BenchmarkDefinition(
                benchmark_id="ACWI",
                asset_class="etf",
                description="Global benchmark",
            )
        )


def test_configured_benchmarks_load() -> None:
    registry = load_benchmark_registry(
        Path("config/intelligence/validation/benchmark_definitions.yaml")
    )
    assert registry.resolve_for_asset_class("crypto").benchmark_id == "bitcoin"
    assert registry.resolve_for_asset_class("cash").benchmark_id == "BIL"
