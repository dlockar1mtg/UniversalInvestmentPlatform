from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json


@dataclass(frozen=True)
class AdapterConfig:
    platform_id: str
    source_interface: str
    contract_version: str
    adapter_version: str
    currency: str
    portfolio_id: str
    account_id: str
    stale_after_days: int
    asset_crosswalk: dict[str, dict[str, str]]


def load_config(path: Path) -> AdapterConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return AdapterConfig(
        platform_id=payload.get("platform_id", "metals"),
        source_interface=payload.get("source_interface", "metals-native-v8"),
        contract_version=payload.get("contract_version", "v1"),
        adapter_version=payload.get("adapter_version", "2.0.0"),
        currency=payload.get("currency", "USD"),
        portfolio_id=payload.get("portfolio_id", "metals-primary"),
        account_id=payload.get("account_id", "metals-all-accounts"),
        stale_after_days=int(payload.get("stale_after_days", 45)),
        asset_crosswalk=payload.get("asset_crosswalk", {}),
    )
