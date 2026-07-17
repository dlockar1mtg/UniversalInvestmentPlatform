"""Configuration for the Universal Decision Orchestrator."""

from __future__ import annotations

from dataclasses import dataclass

from .orchestration_errors import OrchestrationConfigurationError


@dataclass(frozen=True, slots=True)
class OrchestrationProfile:
    """Lifecycle and output settings for orchestrated decisions."""

    profile_id: str = "universal-decision-orchestration"
    engine_version: str = "5.1.8"

    expiration_hours: int = 24
    include_intermediate_artifacts: bool = True
    include_explanation_metadata: bool = True
    include_component_versions: bool = True

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise OrchestrationConfigurationError(
                "profile_id cannot be empty."
            )

        if not self.engine_version.strip():
            raise OrchestrationConfigurationError(
                "engine_version cannot be empty."
            )

        if self.expiration_hours <= 0:
            raise OrchestrationConfigurationError(
                "expiration_hours must be positive."
            )
