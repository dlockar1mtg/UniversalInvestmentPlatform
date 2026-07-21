"""Validate the canonical Metals registry and its certified adapter bridge."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from foundation.production.metals_registry import (  # noqa: E402
    load_metals_registry,
    validate_adapter_crosswalk,
)


def main() -> int:
    registry = load_metals_registry(PROJECT_ROOT / "config" / "metals")
    validate_adapter_crosswalk(
        registry,
        PROJECT_ROOT / "exchange" / "metals" / "config" / "adapter_config.json",
    )
    commodity_assets = tuple(
        sorted(asset.asset_id for asset in registry.assets if asset.asset_class == "commodity")
    )
    enabled_vehicles = tuple(
        sorted(vehicle.ticker for vehicle in registry.vehicles if vehicle.enabled)
    )
    print(
        json.dumps(
            {
                "status": "PASS",
                "schema_version": registry.schema_version,
                "asset_count": len(registry.assets),
                "commodity_count": len(commodity_assets),
                "vehicle_count": len(registry.vehicles),
                "enabled_vehicle_count": len(enabled_vehicles),
                "commodity_asset_ids": commodity_assets,
                "enabled_vehicles": enabled_vehicles,
                "adapter_crosswalk": "MATCH",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
