"""Application service for scoring model selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .scoring_model import ScoringModelDefinition
from .scoring_model_registry import ScoringModelRegistry


@dataclass(frozen=True, slots=True)
class ScoringModelSelection:
    """Auditable result of a scoring model resolution request."""

    asset_class: str
    as_of_date: date
    model: ScoringModelDefinition
    selection_reason: str


class ScoringModelService:
    """Resolve registered models for downstream scoring orchestration."""

    def __init__(self, registry: ScoringModelRegistry) -> None:
        self._registry = registry

    def select_model(
        self,
        *,
        asset_class: str,
        as_of_date: date,
        model_id: str | None = None,
    ) -> ScoringModelSelection:
        model = self._registry.resolve(
            asset_class=asset_class,
            as_of_date=as_of_date,
            model_id=model_id,
        )
        reason = (
            f"Resolved active model {model.model_id} version {model.version} "
            f"for {asset_class} effective on {as_of_date.isoformat()}."
        )
        return ScoringModelSelection(
            asset_class=asset_class,
            as_of_date=as_of_date,
            model=model,
            selection_reason=reason,
        )
