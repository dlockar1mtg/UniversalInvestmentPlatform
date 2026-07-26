"""Readiness checks for the isolated MTG production foundation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class MTGReadinessReport:
    status: str
    source_root: str
    source_available: bool
    config_available: bool
    live_execution_enabled: bool
    reason_codes: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {"reason_codes": list(self.reason_codes)}


def evaluate_mtg_readiness(
    source_root: Path,
    config_path: Path,
    environment: Mapping[str, str],
) -> MTGReadinessReport:
    reasons: list[str] = []
    source_available = source_root.is_dir()
    config_available = config_path.is_file()
    live_execution_enabled = environment.get("UIP_MTG_LIVE_EXECUTION", "false").lower() == "true"

    if not source_available:
        reasons.append("MTG_SOURCE_ROOT_NOT_AVAILABLE")
    if not config_available:
        reasons.append("MTG_PRODUCTION_CONFIG_NOT_AVAILABLE")
    if not live_execution_enabled:
        reasons.append("MTG_LIVE_EXECUTION_DISABLED")

    status = "READY" if source_available and config_available and live_execution_enabled else "SAFE_HOLD"
    return MTGReadinessReport(
        status=status,
        source_root=str(source_root),
        source_available=source_available,
        config_available=config_available,
        live_execution_enabled=live_execution_enabled,
        reason_codes=tuple(reasons),
    )
