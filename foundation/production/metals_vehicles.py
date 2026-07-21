"""Deterministic Metals vehicle selection and concentration constraints."""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable

from .metals_registry import MetalsRegistry, MetalsRegistryError, load_metals_registry

_DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[2] / "config" / "metals" / "vehicle_constraints.json"
DIRECT_TYPES = frozenset({"physical_backed_etf", "futures_fund", "cash_proxy"})
MINER_TYPES = frozenset({"miners_etf", "thematic_equity_etf"})
_HUNDRED = Decimal("100")


class VehicleSelectionError(ValueError):
    """Raised when vehicle inputs or constraints cannot produce a valid allocation."""


@dataclass(frozen=True)
class VehicleCandidate:
    ticker: str
    score: Decimal

    def __init__(self, ticker: str, score: Decimal | int | float | str):
        object.__setattr__(self, "ticker", ticker)
        object.__setattr__(self, "score", Decimal(str(score)))


@dataclass(frozen=True)
class VehicleConstraint:
    minimum_direct_exposure_share_pct: Decimal
    maximum_miner_share_pct: Decimal
    maximum_single_vehicle_share_pct: Decimal


@dataclass(frozen=True)
class VehicleSelectionPolicy:
    minimum_score: Decimal
    top_per_asset: int
    defaults: VehicleConstraint
    by_asset: dict[str, VehicleConstraint]


@dataclass(frozen=True)
class VehicleAllocation:
    ticker: str
    vehicle_id: str
    underlying_asset_id: str
    vehicle_type: str
    score: Decimal
    share_pct: Decimal


@dataclass(frozen=True)
class VehicleSelectionResult:
    asset_slug: str
    allocations: tuple[VehicleAllocation, ...]

    @property
    def total_share_pct(self) -> Decimal:
        return sum((item.share_pct for item in self.allocations), Decimal("0"))

    @property
    def direct_share_pct(self) -> Decimal:
        return sum(
            (item.share_pct for item in self.allocations if item.vehicle_type in DIRECT_TYPES),
            Decimal("0"),
        )

    @property
    def miner_share_pct(self) -> Decimal:
        return sum(
            (item.share_pct for item in self.allocations if item.vehicle_type in MINER_TYPES),
            Decimal("0"),
        )


def _constraint(document: dict) -> VehicleConstraint:
    try:
        value = VehicleConstraint(
            Decimal(str(document["minimum_direct_exposure_share_pct"])),
            Decimal(str(document["maximum_miner_share_pct"])),
            Decimal(str(document["maximum_single_vehicle_share_pct"])),
        )
    except (KeyError, TypeError) as exc:
        raise VehicleSelectionError("vehicle constraint is missing required values") from exc
    if any(
        item < 0 or item > _HUNDRED
        for item in (
            value.minimum_direct_exposure_share_pct,
            value.maximum_miner_share_pct,
            value.maximum_single_vehicle_share_pct,
        )
    ):
        raise VehicleSelectionError("vehicle constraint percentages must be between 0 and 100")
    if value.maximum_single_vehicle_share_pct <= 0:
        raise VehicleSelectionError("maximum single-vehicle share must be positive")
    return value


def load_vehicle_selection_policy(
    path: str | Path = _DEFAULT_POLICY_PATH,
    registry: MetalsRegistry | None = None,
) -> VehicleSelectionPolicy:
    try:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise VehicleSelectionError("cannot load Metals vehicle constraints") from exc
    try:
        minimum_score = Decimal(str(document["minimum_score"]))
        top_per_asset = int(document["top_per_asset"])
        default_document = document["default_constraints"]
        override_documents = document["asset_constraints"]
    except (KeyError, TypeError, ValueError) as exc:
        raise VehicleSelectionError("vehicle policy does not match the required schema") from exc
    if minimum_score < 0 or minimum_score > _HUNDRED or top_per_asset < 1:
        raise VehicleSelectionError("vehicle selection thresholds are outside permitted bounds")
    defaults = _constraint(default_document)
    selected_registry = registry or load_metals_registry()
    known_slugs = set(selected_registry.assets_by_slug)
    unknown = set(override_documents) - known_slugs
    if unknown:
        raise VehicleSelectionError(f"constraints reference unknown assets: {sorted(unknown)}")
    by_asset: dict[str, VehicleConstraint] = {}
    for slug in known_slugs:
        merged = dict(default_document)
        merged.update(override_documents.get(slug, {}))
        by_asset[slug] = _constraint(merged)
    return VehicleSelectionPolicy(minimum_score, top_per_asset, defaults, by_asset)


def _allocate_group(
    tickers: list[str],
    weights: dict[str, Decimal],
    total: Decimal,
    cap: Decimal,
) -> dict[str, Decimal]:
    if total == 0:
        return {ticker: Decimal("0") for ticker in tickers}
    if not tickers or Decimal(len(tickers)) * cap < total:
        raise VehicleSelectionError("single-vehicle cap makes the requested group allocation infeasible")
    remaining = total
    active = set(tickers)
    result: dict[str, Decimal] = {}
    while active:
        weight_total = sum((weights[ticker] for ticker in active), Decimal("0"))
        proposed = {
            ticker: remaining * weights[ticker] / weight_total
            for ticker in active
        }
        capped = sorted(ticker for ticker, share in proposed.items() if share > cap)
        if not capped:
            ordered = sorted(active, key=lambda ticker: (-weights[ticker], ticker))
            allocated = Decimal("0")
            for ticker in ordered[:-1]:
                result[ticker] = proposed[ticker]
                allocated += proposed[ticker]
            result[ordered[-1]] = remaining - allocated
            break
        for ticker in capped:
            result[ticker] = cap
            remaining -= cap
            active.remove(ticker)
    return result


def select_metals_vehicles(
    asset_slug: str,
    candidates: Iterable[VehicleCandidate],
    *,
    registry: MetalsRegistry | None = None,
    policy: VehicleSelectionPolicy | None = None,
) -> VehicleSelectionResult:
    selected_registry = registry or load_metals_registry()
    selected_policy = policy or load_vehicle_selection_policy(registry=selected_registry)
    try:
        asset = selected_registry.assets_by_slug[asset_slug]
        constraint = selected_policy.by_asset[asset_slug]
    except KeyError as exc:
        raise VehicleSelectionError(f"unknown asset for vehicle selection: {asset_slug}") from exc

    values = tuple(candidates)
    tickers = [item.ticker for item in values]
    if len(tickers) != len(set(tickers)):
        raise VehicleSelectionError("vehicle candidates contain duplicate tickers")
    valid: list[VehicleCandidate] = []
    for candidate in values:
        vehicle = selected_registry.vehicles_by_ticker.get(candidate.ticker)
        if vehicle is None:
            raise VehicleSelectionError(f"unknown vehicle candidate: {candidate.ticker}")
        if not candidate.score.is_finite() or candidate.score < 0 or candidate.score > _HUNDRED:
            raise VehicleSelectionError(f"vehicle score is outside permitted bounds: {candidate.ticker}")
        if vehicle.underlying_asset_id != asset.asset_id:
            raise VehicleSelectionError(f"vehicle candidate does not belong to {asset_slug}: {candidate.ticker}")
        if vehicle.enabled:
            valid.append(candidate)
    if not valid:
        raise VehicleSelectionError(f"no enabled vehicle candidates for {asset_slug}")

    ranked = sorted(valid, key=lambda item: (-item.score, item.ticker))
    eligible = [item for item in ranked if item.score >= selected_policy.minimum_score]
    selected = eligible[: selected_policy.top_per_asset] or ranked[:1]

    effective_direct_minimum = max(
        constraint.minimum_direct_exposure_share_pct,
        _HUNDRED - constraint.maximum_miner_share_pct,
    )
    vehicle_map = selected_registry.vehicles_by_ticker
    cap = constraint.maximum_single_vehicle_share_pct
    while Decimal(len(selected)) * cap < _HUNDRED:
        additional = next((item for item in ranked if item not in selected), None)
        if additional is None or len(selected) >= selected_policy.top_per_asset:
            break
        selected.append(additional)
        selected.sort(key=lambda item: (-item.score, item.ticker))
    if effective_direct_minimum > 0 and not any(
        vehicle_map[item.ticker].vehicle_type in DIRECT_TYPES for item in selected
    ):
        direct = next(
            (
                item for item in ranked
                if vehicle_map[item.ticker].vehicle_type in DIRECT_TYPES
            ),
            None,
        )
        if direct is None:
            raise VehicleSelectionError("direct-exposure minimum has no eligible direct vehicle")
        selected = selected[:-1] + [direct] if len(selected) >= selected_policy.top_per_asset else selected + [direct]
        selected = sorted({item.ticker: item for item in selected}.values(), key=lambda item: (-item.score, item.ticker))

    classifications = {
        item.ticker: vehicle_map[item.ticker].vehicle_type for item in selected
    }
    unsupported = {
        ticker for ticker, vehicle_type in classifications.items()
        if vehicle_type not in DIRECT_TYPES | MINER_TYPES
    }
    if unsupported:
        raise VehicleSelectionError(f"unsupported vehicle types for allocation: {sorted(unsupported)}")

    direct = [item.ticker for item in selected if classifications[item.ticker] in DIRECT_TYPES]
    miners = [item.ticker for item in selected if classifications[item.ticker] in MINER_TYPES]
    weights = {item.ticker: max(item.score - Decimal("20"), Decimal("1")) for item in selected}

    if not direct:
        if effective_direct_minimum > 0:
            raise VehicleSelectionError("direct-exposure constraint is infeasible")
        direct_target = Decimal("0")
    elif not miners:
        direct_target = _HUNDRED
    else:
        base_direct = _HUNDRED * sum(weights[ticker] for ticker in direct) / sum(weights.values())
        lower = max(effective_direct_minimum, _HUNDRED - Decimal(len(miners)) * cap)
        upper = min(_HUNDRED, Decimal(len(direct)) * cap)
        if lower > upper:
            raise VehicleSelectionError("combined vehicle constraints are infeasible")
        direct_target = min(max(base_direct, lower), upper)
    miner_target = _HUNDRED - direct_target
    if miner_target > constraint.maximum_miner_share_pct:
        raise VehicleSelectionError("miner concentration constraint is infeasible")

    shares = _allocate_group(direct, weights, direct_target, cap)
    shares.update(_allocate_group(miners, weights, miner_target, cap))
    allocations = tuple(
        VehicleAllocation(
            ticker=item.ticker,
            vehicle_id=vehicle_map[item.ticker].vehicle_id,
            underlying_asset_id=asset.asset_id,
            vehicle_type=vehicle_map[item.ticker].vehicle_type,
            score=item.score,
            share_pct=shares[item.ticker],
        )
        for item in selected
    )
    result = VehicleSelectionResult(asset_slug, allocations)
    if result.total_share_pct != _HUNDRED:
        raise VehicleSelectionError("vehicle allocation does not sum to 100")
    if result.direct_share_pct < constraint.minimum_direct_exposure_share_pct:
        raise VehicleSelectionError("vehicle allocation violates direct-exposure minimum")
    if result.miner_share_pct > constraint.maximum_miner_share_pct:
        raise VehicleSelectionError("vehicle allocation violates miner concentration maximum")
    if any(item.share_pct > cap for item in result.allocations):
        raise VehicleSelectionError("vehicle allocation violates single-vehicle maximum")
    return result
