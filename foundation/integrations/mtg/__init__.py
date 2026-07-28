"""MTG integration adapters for the Universal Investment Platform."""

from foundation.integrations.mtg.manual_production import (
    MTGProductionResult,
    build_universal_package,
    run_mtg_manual_production_cycle,
    validate_handoff,
)
from foundation.integrations.mtg.universal_adapter import (
    MISSING,
    MTGAdapterResult,
    build_universal_mtg_package,
)

__all__ = [
    "MISSING",
    "MTGAdapterResult",
    "MTGProductionResult",
    "build_universal_mtg_package",
    "build_universal_package",
    "run_mtg_manual_production_cycle",
    "validate_handoff",
]
