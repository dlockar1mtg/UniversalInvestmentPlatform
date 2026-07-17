"""In-memory scoring model registry with version and lifecycle controls."""

from __future__ import annotations

from datetime import date
from types import MappingProxyType
from typing import Iterable, Mapping

from .scoring_model import ScoringModelDefinition, ScoringModelStatus


class ScoringModelRegistry:
    """Register, discover, and resolve versioned scoring models."""

    def __init__(
        self,
        models: Iterable[ScoringModelDefinition] = (),
    ) -> None:
        self._models: dict[tuple[str, str], ScoringModelDefinition] = {}
        for model in models:
            self.register(model)

    @property
    def models(self) -> Mapping[tuple[str, str], ScoringModelDefinition]:
        return MappingProxyType(self._models)

    def register(
        self,
        model: ScoringModelDefinition,
        *,
        replace: bool = False,
    ) -> None:
        if not isinstance(model, ScoringModelDefinition):
            raise TypeError("model must be a ScoringModelDefinition.")
        key = model.registry_key
        if key in self._models and not replace:
            raise ValueError(
                f"Scoring model already registered: {model.model_id} {model.version}."
            )
        self._models[key] = model

    def get(self, model_id: str, version: str) -> ScoringModelDefinition:
        key = (model_id, version)
        try:
            return self._models[key]
        except KeyError as exc:
            raise KeyError(
                f"Unknown scoring model: {model_id} version {version}."
            ) from exc

    def list_models(
        self,
        *,
        asset_class: str | None = None,
        status: ScoringModelStatus | None = None,
    ) -> tuple[ScoringModelDefinition, ...]:
        results = tuple(
            model
            for model in self._models.values()
            if (asset_class is None or model.asset_class == asset_class)
            and (status is None or model.status is status)
        )
        return tuple(
            sorted(
                results,
                key=lambda model: (
                    model.asset_class,
                    model.model_id,
                    model.effective_from,
                    model.version,
                ),
            )
        )

    def resolve(
        self,
        *,
        asset_class: str,
        as_of_date: date,
        model_id: str | None = None,
        status: ScoringModelStatus = ScoringModelStatus.ACTIVE,
    ) -> ScoringModelDefinition:
        """Resolve the single most recent effective model for an asset class."""
        candidates = [
            model
            for model in self._models.values()
            if model.asset_class == asset_class
            and model.status is status
            and model.is_effective_on(as_of_date)
            and (model_id is None or model.model_id == model_id)
        ]
        if not candidates:
            descriptor = model_id or asset_class
            raise LookupError(
                f"No {status.value} scoring model is effective for {descriptor} "
                f"on {as_of_date.isoformat()}."
            )

        candidates.sort(
            key=lambda model: (model.effective_from, model.version),
            reverse=True,
        )
        winner = candidates[0]

        same_date = [
            model
            for model in candidates
            if model.effective_from == winner.effective_from
            and model.model_id != winner.model_id
        ]
        if model_id is None and same_date:
            ids = ", ".join(sorted({winner.model_id, *(item.model_id for item in same_date)}))
            raise LookupError(
                "Multiple active scoring models are equally eligible for "
                f"{asset_class}: {ids}. Specify model_id explicitly."
            )
        return winner

    def validate(self) -> tuple[str, ...]:
        """Return registry consistency errors without mutating the registry."""
        errors: list[str] = []
        grouped: dict[tuple[str, str], list[ScoringModelDefinition]] = {}

        for model in self._models.values():
            grouped.setdefault((model.asset_class, model.model_id), []).append(model)

        for (asset_class, model_id), versions in grouped.items():
            ordered = sorted(versions, key=lambda item: item.effective_from)
            active_versions = [
                item for item in ordered if item.status is ScoringModelStatus.ACTIVE
            ]
            for previous, current in zip(active_versions, active_versions[1:]):
                previous_end = previous.effective_to
                if previous_end is None or previous_end >= current.effective_from:
                    errors.append(
                        "Overlapping active model windows for "
                        f"{asset_class}/{model_id}: "
                        f"{previous.version} and {current.version}."
                    )

        return tuple(errors)


DEFAULT_SCORING_MODEL_REGISTRY = ScoringModelRegistry()
