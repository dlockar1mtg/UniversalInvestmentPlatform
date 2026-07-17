"""Registry for discovering and resolving forecast engines."""

from __future__ import annotations

from collections.abc import Iterator

from ..models import ForecastHorizon
from .base_engine import BaseForecastEngine
from .engine_contracts import ForecastEngineError


class DuplicateForecastEngineError(ForecastEngineError):
    """Raised when an engine key is already registered."""


class ForecastEngineNotFoundError(ForecastEngineError):
    """Raised when no compatible forecast engine can be resolved."""


class ForecastEngineRegistry:
    """In-memory registry keyed by engine name and version."""

    def __init__(self) -> None:
        self._engines: dict[tuple[str, str], BaseForecastEngine] = {}

    def register(
        self,
        engine: BaseForecastEngine,
        *,
        replace: bool = False,
    ) -> None:
        """Register an engine instance."""

        key = (
            engine.metadata.engine_name,
            engine.metadata.engine_version,
        )
        if key in self._engines and not replace:
            raise DuplicateForecastEngineError(
                f"Forecast engine already registered: {key[0]} {key[1]}"
            )
        self._engines[key] = engine

    def unregister(self, engine_name: str, engine_version: str) -> None:
        """Remove one exact engine version."""

        key = (engine_name, engine_version)
        try:
            del self._engines[key]
        except KeyError as exc:
            raise ForecastEngineNotFoundError(
                f"Forecast engine not registered: {engine_name} {engine_version}"
            ) from exc

    def get(
        self,
        engine_name: str,
        engine_version: str | None = None,
    ) -> BaseForecastEngine:
        """Get an exact version or the latest registered version by name."""

        if engine_version is not None:
            key = (engine_name, engine_version)
            try:
                return self._engines[key]
            except KeyError as exc:
                raise ForecastEngineNotFoundError(
                    f"Forecast engine not registered: "
                    f"{engine_name} {engine_version}"
                ) from exc

        candidates = [
            engine
            for (name, _), engine in self._engines.items()
            if name == engine_name
        ]
        if not candidates:
            raise ForecastEngineNotFoundError(
                f"No forecast engine registered with name {engine_name!r}."
            )
        return max(
            candidates,
            key=lambda engine: self._version_key(
                engine.metadata.engine_version
            ),
        )

    def resolve(
        self,
        *,
        asset_class: str,
        horizon: ForecastHorizon,
        engine_name: str | None = None,
    ) -> BaseForecastEngine:
        """Resolve the latest compatible engine."""

        candidates = list(self._engines.values())

        if engine_name is not None:
            candidates = [
                engine
                for engine in candidates
                if engine.metadata.engine_name == engine_name
            ]

        candidates = [
            engine
            for engine in candidates
            if asset_class in engine.metadata.asset_classes
            and horizon in engine.metadata.supported_horizons
        ]

        if not candidates:
            details = (
                f"asset_class={asset_class!r}, horizon={horizon.value!r}"
            )
            if engine_name is not None:
                details += f", engine_name={engine_name!r}"
            raise ForecastEngineNotFoundError(
                f"No compatible forecast engine found for {details}."
            )

        return max(
            candidates,
            key=lambda engine: self._version_key(
                engine.metadata.engine_version
            ),
        )

    def list_engines(self) -> tuple[ForecastEngineMetadataView, ...]:
        """Return stable metadata views sorted by name and version."""

        views = [
            ForecastEngineMetadataView(
                engine_name=engine.metadata.engine_name,
                engine_version=engine.metadata.engine_version,
                asset_classes=engine.metadata.asset_classes,
                supported_horizons=tuple(
                    horizon.value
                    for horizon in engine.metadata.supported_horizons
                ),
            )
            for engine in self._engines.values()
        ]
        return tuple(
            sorted(
                views,
                key=lambda item: (
                    item.engine_name,
                    self._version_key(item.engine_version),
                ),
            )
        )

    def __len__(self) -> int:
        return len(self._engines)

    def __iter__(self) -> Iterator[BaseForecastEngine]:
        return iter(self._engines.values())

    @staticmethod
    def _version_key(version: str) -> tuple[tuple[int, object], ...]:
        """Create a tolerant ordering key for dotted version strings."""

        parts: list[tuple[int, object]] = []
        for part in version.replace("-", ".").split("."):
            if part.isdigit():
                parts.append((1, int(part)))
            else:
                parts.append((0, part))
        return tuple(parts)


from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ForecastEngineMetadataView:
    """Serializable registry listing entry."""

    engine_name: str
    engine_version: str
    asset_classes: tuple[str, ...]
    supported_horizons: tuple[str, ...]
