"""Benchmark definition registry."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping

from .validation import validate_non_empty_text


@dataclass(frozen=True, slots=True)
class BenchmarkDefinition:
    """Benchmark identity and asset-class mapping."""

    benchmark_id: str
    asset_class: str
    description: str
    source: str = "configured"

    def __post_init__(self) -> None:
        for field_name in ("benchmark_id", "asset_class", "description", "source"):
            object.__setattr__(
                self,
                field_name,
                validate_non_empty_text(getattr(self, field_name), field_name),
            )


class BenchmarkRegistry:
    """Resolve benchmark definitions by asset class or ID."""

    def __init__(self, definitions: Iterable[BenchmarkDefinition] = ()) -> None:
        self._by_id: dict[str, BenchmarkDefinition] = {}
        self._by_asset_class: dict[str, BenchmarkDefinition] = {}
        for definition in definitions:
            self.register(definition)

    @property
    def definitions(self) -> Mapping[str, BenchmarkDefinition]:
        return MappingProxyType(self._by_id)

    def register(
        self,
        definition: BenchmarkDefinition,
        *,
        replace: bool = False,
    ) -> None:
        if definition.benchmark_id in self._by_id and not replace:
            raise ValueError(
                f"Benchmark already registered: {definition.benchmark_id}."
            )
        if definition.asset_class in self._by_asset_class and not replace:
            raise ValueError(
                f"Asset class already has a benchmark: {definition.asset_class}."
            )
        self._by_id[definition.benchmark_id] = definition
        self._by_asset_class[definition.asset_class] = definition

    def get(self, benchmark_id: str) -> BenchmarkDefinition:
        try:
            return self._by_id[benchmark_id]
        except KeyError as exc:
            raise KeyError(f"Unknown benchmark: {benchmark_id}.") from exc

    def resolve_for_asset_class(self, asset_class: str) -> BenchmarkDefinition:
        try:
            return self._by_asset_class[asset_class]
        except KeyError as exc:
            raise KeyError(
                f"No benchmark configured for asset class: {asset_class}."
            ) from exc
