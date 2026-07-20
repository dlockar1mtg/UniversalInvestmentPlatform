"""Canonical Metals asset and investment-vehicle registry."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

_DEFAULT_CONFIG_ROOT = Path(__file__).resolve().parents[2] / "config" / "metals"


class MetalsRegistryError(ValueError):
    """Raised when Metals registry configuration violates its contract."""


@dataclass(frozen=True)
class MetalsAsset:
    asset_id: str
    slug: str
    name: str
    symbol: str
    asset_class: str
    unit: str
    providers: Mapping[str, str]
    benchmark_vehicle: str | None


@dataclass(frozen=True)
class MetalsVehicle:
    vehicle_id: str
    ticker: str
    name: str
    underlying_asset_id: str
    vehicle_type: str
    role: str
    enabled: bool
    official_url: str
    expense_ratio_pct: float | None
    expense_ratio_as_of: str | None


@dataclass(frozen=True)
class MetalsRegistry:
    schema_version: str
    assets: tuple[MetalsAsset, ...]
    vehicles: tuple[MetalsVehicle, ...]

    @property
    def assets_by_id(self) -> dict[str, MetalsAsset]:
        return {asset.asset_id: asset for asset in self.assets}

    @property
    def assets_by_slug(self) -> dict[str, MetalsAsset]:
        return {asset.slug: asset for asset in self.assets}

    @property
    def vehicles_by_ticker(self) -> dict[str, MetalsVehicle]:
        return {vehicle.ticker: vehicle for vehicle in self.vehicles}


def _read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MetalsRegistryError(f"cannot load Metals registry file: {path.name}") from exc
    if not isinstance(value, dict):
        raise MetalsRegistryError(f"{path.name} must contain a JSON object")
    return value


def load_metals_registry(config_root: str | Path = _DEFAULT_CONFIG_ROOT) -> MetalsRegistry:
    root = Path(config_root)
    asset_document = _read_json(root / "assets.json")
    vehicle_document = _read_json(root / "vehicles.json")
    if asset_document.get("platform_id") != "metals" or vehicle_document.get("platform_id") != "metals":
        raise MetalsRegistryError("registry platform_id must be metals")
    if asset_document.get("schema_version") != vehicle_document.get("schema_version"):
        raise MetalsRegistryError("asset and vehicle registry schema versions must match")
    try:
        assets = tuple(MetalsAsset(**item) for item in asset_document["assets"])
        vehicles = tuple(MetalsVehicle(**item) for item in vehicle_document["vehicles"])
    except (KeyError, TypeError) as exc:
        raise MetalsRegistryError("registry record does not match the required schema") from exc
    registry = MetalsRegistry(str(asset_document["schema_version"]), assets, vehicles)
    validate_metals_registry(registry)
    return registry


def validate_metals_registry(registry: MetalsRegistry) -> None:
    asset_ids = [asset.asset_id for asset in registry.assets]
    slugs = [asset.slug for asset in registry.assets]
    symbols = [asset.symbol for asset in registry.assets]
    vehicle_ids = [vehicle.vehicle_id for vehicle in registry.vehicles]
    tickers = [vehicle.ticker for vehicle in registry.vehicles]
    for label, values in (
        ("asset_id", asset_ids),
        ("asset slug", slugs),
        ("asset symbol", symbols),
        ("vehicle_id", vehicle_ids),
        ("vehicle ticker", tickers),
    ):
        if len(values) != len(set(values)):
            raise MetalsRegistryError(f"duplicate {label} in Metals registry")
    if not registry.assets or not registry.vehicles:
        raise MetalsRegistryError("Metals registry cannot be empty")
    for asset in registry.assets:
        if asset.asset_id != (
            f"metals:commodity:{asset.slug}" if asset.asset_class == "commodity"
            else f"metals:reserve:usd"
        ):
            raise MetalsRegistryError(f"non-canonical asset_id for {asset.slug}")
        if asset.symbol != asset.symbol.upper():
            raise MetalsRegistryError(f"asset symbol must be uppercase: {asset.symbol}")
        if not isinstance(asset.providers, dict):
            raise MetalsRegistryError(f"providers must be an object for {asset.slug}")
    asset_set = set(asset_ids)
    vehicle_set = set(tickers)
    for vehicle in registry.vehicles:
        if vehicle.vehicle_id != f"metals:vehicle:{vehicle.ticker}":
            raise MetalsRegistryError(f"non-canonical vehicle_id for {vehicle.ticker}")
        if vehicle.ticker != vehicle.ticker.upper():
            raise MetalsRegistryError(f"vehicle ticker must be uppercase: {vehicle.ticker}")
        if vehicle.underlying_asset_id not in asset_set:
            raise MetalsRegistryError(f"unknown underlying asset for {vehicle.ticker}")
        if vehicle.role not in {"strategic", "tactical", "reserve"}:
            raise MetalsRegistryError(f"invalid vehicle role for {vehicle.ticker}")
        if not vehicle.official_url.startswith("https://"):
            raise MetalsRegistryError(f"official URL must use HTTPS for {vehicle.ticker}")
        if (vehicle.expense_ratio_pct is None) != (vehicle.expense_ratio_as_of is None):
            raise MetalsRegistryError(f"expense ratio and as-of date must be supplied together for {vehicle.ticker}")
    for asset in registry.assets:
        if asset.benchmark_vehicle is not None and asset.benchmark_vehicle not in vehicle_set:
            raise MetalsRegistryError(f"unknown benchmark vehicle for {asset.slug}")


def validate_adapter_crosswalk(
    registry: MetalsRegistry,
    adapter_config: str | Path,
) -> None:
    document = _read_json(Path(adapter_config))
    crosswalk = document.get("asset_crosswalk")
    if not isinstance(crosswalk, dict):
        raise MetalsRegistryError("adapter asset_crosswalk must be an object")
    expected = {
        asset.slug: {"asset_id": asset.asset_id, "symbol": asset.symbol}
        for asset in registry.assets
        if asset.asset_class == "commodity"
    }
    if crosswalk != expected:
        raise MetalsRegistryError("adapter asset_crosswalk does not match canonical Metals assets")


def canonical_metals_asset_id(slug: str, registry: MetalsRegistry | None = None) -> str:
    selected = registry or load_metals_registry()
    try:
        asset = selected.assets_by_slug[slug]
    except KeyError as exc:
        raise MetalsRegistryError(f"unknown Metals asset slug: {slug}") from exc
    if asset.asset_class != "commodity":
        raise MetalsRegistryError(f"asset is not a commodity: {slug}")
    return asset.asset_id
