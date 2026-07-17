from datetime import date

import pytest

from foundation.intelligence.scoring import (
    ScoringModelDefinition,
    ScoringModelRegistry,
    ScoringModelService,
    ScoringModelStatus,
)


def model(
    *,
    model_id: str = "crypto_core_v1",
    asset_class: str = "crypto",
    version: str = "1.0.0",
    status: ScoringModelStatus = ScoringModelStatus.ACTIVE,
    effective_from: date = date(2026, 1, 1),
    effective_to: date | None = None,
) -> ScoringModelDefinition:
    return ScoringModelDefinition(
        model_id=model_id,
        asset_class=asset_class,
        version=version,
        scoring_profile_id=f"{asset_class}_profile_v1",
        normalization_profile_id=f"{asset_class}_normalization_v1",
        status=status,
        effective_from=effective_from,
        effective_to=effective_to,
    )


def test_registry_registers_and_gets_exact_version() -> None:
    registry = ScoringModelRegistry([model()])
    selected = registry.get("crypto_core_v1", "1.0.0")
    assert selected.asset_class == "crypto"


def test_registry_rejects_duplicate_key() -> None:
    registry = ScoringModelRegistry([model()])
    with pytest.raises(ValueError):
        registry.register(model())


def test_resolve_selects_latest_effective_active_version() -> None:
    registry = ScoringModelRegistry(
        [
            model(
                version="1.0.0",
                effective_from=date(2026, 1, 1),
                effective_to=date(2026, 6, 30),
            ),
            model(
                version="1.1.0",
                effective_from=date(2026, 7, 1),
            ),
        ]
    )
    selected = registry.resolve(
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
        model_id="crypto_core_v1",
    )
    assert selected.version == "1.1.0"


def test_resolve_ignores_draft_models() -> None:
    registry = ScoringModelRegistry(
        [model(status=ScoringModelStatus.DRAFT)]
    )
    with pytest.raises(LookupError):
        registry.resolve(
            asset_class="crypto",
            as_of_date=date(2026, 7, 17),
        )


def test_registry_validation_detects_overlapping_active_windows() -> None:
    registry = ScoringModelRegistry(
        [
            model(version="1.0.0", effective_from=date(2026, 1, 1)),
            model(version="1.1.0", effective_from=date(2026, 7, 1)),
        ]
    )
    errors = registry.validate()
    assert len(errors) == 1
    assert "Overlapping active model windows" in errors[0]


def test_service_returns_auditable_selection() -> None:
    registry = ScoringModelRegistry([model()])
    selection = ScoringModelService(registry).select_model(
        asset_class="crypto",
        as_of_date=date(2026, 7, 17),
    )
    assert selection.model.model_id == "crypto_core_v1"
    assert "Resolved active model" in selection.selection_reason


def test_effective_window_is_inclusive() -> None:
    definition = model(
        effective_from=date(2026, 1, 1),
        effective_to=date(2026, 12, 31),
    )
    assert definition.is_effective_on(date(2026, 1, 1))
    assert definition.is_effective_on(date(2026, 12, 31))
    assert not definition.is_effective_on(date(2027, 1, 1))
