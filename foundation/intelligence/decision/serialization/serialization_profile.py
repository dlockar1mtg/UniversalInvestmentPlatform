"""Configuration for decision serialization and audit exports."""

from __future__ import annotations

from dataclasses import dataclass

from .serialization_errors import SerializationConfigurationError


@dataclass(frozen=True, slots=True)
class DecisionSerializationProfile:
    """Schema and formatting settings for serialized decisions."""

    profile_id: str = "universal-decision-serialization"
    schema_version: str = "1.0"
    serialization_version: str = "5.1.9"

    include_intermediate_artifacts: bool = True
    include_explanation: bool = True
    include_audit_facts: bool = True
    include_source_metadata: bool = True
    sort_keys: bool = True
    json_indent: int | None = 2

    def __post_init__(self) -> None:
        if not self.profile_id.strip():
            raise SerializationConfigurationError(
                "profile_id cannot be empty."
            )

        if not self.schema_version.strip():
            raise SerializationConfigurationError(
                "schema_version cannot be empty."
            )

        if not self.serialization_version.strip():
            raise SerializationConfigurationError(
                "serialization_version cannot be empty."
            )

        if self.json_indent is not None and self.json_indent < 0:
            raise SerializationConfigurationError(
                "json_indent cannot be negative."
            )
