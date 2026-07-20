"""Validated production runtime configuration."""

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class ProductionRuntimeConfig:
    environment: str
    database_path: Path
    artifact_directory: Path
    service_name: str = "uiip"
    strict_mode: bool = True

    def __post_init__(self) -> None:
        if self.environment not in {"development", "test", "staging", "production"}:
            raise ValueError("environment must be development, test, staging, or production")
        if not self.service_name.strip():
            raise ValueError("service_name must not be blank")
        if self.environment == "production" and not self.strict_mode:
            raise ValueError("production requires strict_mode")

    @classmethod
    def from_mapping(cls, values: Mapping[str, str]) -> "ProductionRuntimeConfig":
        required = ("UIIP_ENVIRONMENT", "UIIP_DATABASE_PATH", "UIIP_ARTIFACT_DIRECTORY")
        missing = [key for key in required if not values.get(key, "").strip()]
        if missing:
            raise ValueError(f"missing runtime configuration: {', '.join(missing)}")
        strict = values.get("UIIP_STRICT_MODE", "true").strip().lower()
        if strict not in {"true", "false"}:
            raise ValueError("UIIP_STRICT_MODE must be true or false")
        return cls(
            values["UIIP_ENVIRONMENT"].strip().lower(), Path(values["UIIP_DATABASE_PATH"]),
            Path(values["UIIP_ARTIFACT_DIRECTORY"]), values.get("UIIP_SERVICE_NAME", "uiip"),
            strict == "true",
        )
