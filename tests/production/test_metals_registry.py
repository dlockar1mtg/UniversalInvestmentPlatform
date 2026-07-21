from __future__ import annotations

import json
from pathlib import Path

import pytest

from foundation.production.metals_registry import (
    MetalsRegistryError,
    canonical_metals_asset_id,
    load_metals_registry,
    validate_adapter_crosswalk,
)


CONFIG_ROOT = Path("config/metals")
ADAPTER_CONFIG = Path("exchange/metals/config/adapter_config.json")


def test_registry_loads_complete_canonical_universe() -> None:
    registry = load_metals_registry()
    assert len(registry.assets) == 10
    assert len(registry.vehicles) == 11
    assert len(registry.assets_by_id) == 10
    assert len(registry.vehicles_by_ticker) == 11
    assert {"GLD", "IAU", "SGOL", "SLV", "CPER", "URA", "BIL"} <= set(
        registry.vehicles_by_ticker
    )


def test_adapter_crosswalk_exactly_matches_canonical_commodities() -> None:
    registry = load_metals_registry()
    validate_adapter_crosswalk(registry, ADAPTER_CONFIG)
    commodity_ids = {
        asset.asset_id for asset in registry.assets if asset.asset_class == "commodity"
    }
    assert commodity_ids == {
        f"metals:commodity:{slug}"
        for slug in {
            "gold", "silver", "copper", "uranium", "platinum",
            "aluminum", "zinc", "nickel", "tin",
        }
    }


def test_vehicle_underlyings_and_benchmarks_resolve() -> None:
    registry = load_metals_registry()
    for vehicle in registry.vehicles:
        assert vehicle.underlying_asset_id in registry.assets_by_id
    for asset in registry.assets:
        if asset.benchmark_vehicle:
            assert asset.benchmark_vehicle in registry.vehicles_by_ticker


def test_legacy_vehicle_universe_is_preserved() -> None:
    registry = load_metals_registry()
    assert set(registry.vehicles_by_ticker) == {
        "GLD", "IAU", "SGOL", "SLV", "SIVR", "PPLT",
        "CPER", "COPX", "URA", "URNM", "BIL",
    }
    assert registry.vehicles_by_ticker["BIL"].role == "reserve"
    assert registry.vehicles_by_ticker["COPX"].vehicle_type == "miners_etf"


def test_mutable_expense_data_is_optional_but_paired() -> None:
    registry = load_metals_registry()
    assert all(vehicle.expense_ratio_pct is None for vehicle in registry.vehicles)


def test_canonical_asset_lookup_rejects_unknown_or_noncommodity() -> None:
    registry = load_metals_registry()
    assert canonical_metals_asset_id("gold", registry) == "metals:commodity:gold"
    with pytest.raises(MetalsRegistryError):
        canonical_metals_asset_id("missing", registry)
    with pytest.raises(MetalsRegistryError):
        canonical_metals_asset_id("tactical_reserve", registry)


def test_registry_rejects_unknown_underlying(tmp_path: Path) -> None:
    assets = json.loads((CONFIG_ROOT / "assets.json").read_text(encoding="utf-8"))
    vehicles = json.loads((CONFIG_ROOT / "vehicles.json").read_text(encoding="utf-8"))
    vehicles["vehicles"][0]["underlying_asset_id"] = "metals:commodity:missing"
    (tmp_path / "assets.json").write_text(json.dumps(assets), encoding="utf-8")
    (tmp_path / "vehicles.json").write_text(json.dumps(vehicles), encoding="utf-8")
    with pytest.raises(MetalsRegistryError, match="unknown underlying"):
        load_metals_registry(tmp_path)


def test_registry_rejects_adapter_identity_drift(tmp_path: Path) -> None:
    registry = load_metals_registry()
    adapter = json.loads(ADAPTER_CONFIG.read_text(encoding="utf-8"))
    adapter["asset_crosswalk"]["gold"]["asset_id"] = "metals:gold"
    path = tmp_path / "adapter.json"
    path.write_text(json.dumps(adapter), encoding="utf-8")
    with pytest.raises(MetalsRegistryError, match="does not match"):
        validate_adapter_crosswalk(registry, path)
