from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from foundation.production.metals_registry import load_metals_registry
from foundation.production.metals_vehicles import (
    VehicleCandidate,
    VehicleConstraint,
    VehicleSelectionError,
    load_vehicle_selection_policy,
    select_metals_vehicles,
)


def shares(result):
    return {item.ticker: item.share_pct for item in result.allocations}


def test_copper_forces_direct_vehicle_and_enforces_structural_limits() -> None:
    result = select_metals_vehicles(
        "copper",
        [VehicleCandidate("COPX", 95), VehicleCandidate("CPER", 30)],
    )
    allocation = shares(result)
    assert allocation == {"COPX": Decimal("60"), "CPER": Decimal("40")}
    assert result.direct_share_pct == Decimal("40")
    assert result.miner_share_pct == Decimal("60")
    assert result.total_share_pct == Decimal("100")


def test_gold_single_vehicle_cap_admits_additional_candidates() -> None:
    result = select_metals_vehicles(
        "gold",
        [
            VehicleCandidate("GLD", 95),
            VehicleCandidate("IAU", 35),
            VehicleCandidate("SGOL", 30),
        ],
    )
    allocation = shares(result)
    assert set(allocation) == {"GLD", "IAU"}
    assert allocation["GLD"] == Decimal("60")
    assert allocation["IAU"] == Decimal("40")


def test_uranium_concentration_cap_prevents_single_fund_dominance() -> None:
    result = select_metals_vehicles(
        "uranium",
        [VehicleCandidate("URA", 90), VehicleCandidate("URNM", 50)],
    )
    allocation = shares(result)
    assert allocation["URA"] == Decimal("60")
    assert allocation["URNM"] == Decimal("40")
    assert result.miner_share_pct == Decimal("100")


def test_platinum_and_reserve_allow_single_registered_vehicle() -> None:
    platinum = select_metals_vehicles("platinum", [VehicleCandidate("PPLT", 70)])
    reserve = select_metals_vehicles("tactical_reserve", [VehicleCandidate("BIL", 80)])
    assert shares(platinum) == {"PPLT": Decimal("100")}
    assert shares(reserve) == {"BIL": Decimal("100")}


def test_ranking_and_allocation_are_deterministic() -> None:
    candidates = [
        VehicleCandidate("SGOL", 80),
        VehicleCandidate("GLD", 80),
        VehicleCandidate("IAU", 70),
    ]
    first = select_metals_vehicles("gold", candidates)
    second = select_metals_vehicles("gold", reversed(candidates))
    assert first == second
    assert [item.ticker for item in first.allocations] == ["GLD", "SGOL", "IAU"]


def test_selection_rejects_duplicate_wrong_asset_and_invalid_scores() -> None:
    with pytest.raises(VehicleSelectionError, match="duplicate"):
        select_metals_vehicles(
            "gold",
            [VehicleCandidate("GLD", 70), VehicleCandidate("GLD", 60)],
        )
    with pytest.raises(VehicleSelectionError, match="does not belong"):
        select_metals_vehicles("gold", [VehicleCandidate("SLV", 70)])
    with pytest.raises(VehicleSelectionError, match="outside"):
        select_metals_vehicles("gold", [VehicleCandidate("GLD", 101)])


def test_infeasible_direct_constraint_fails_closed() -> None:
    registry = load_metals_registry()
    policy = load_vehicle_selection_policy(registry=registry)
    uranium_constraint = VehicleConstraint(Decimal("10"), Decimal("100"), Decimal("60"))
    policy = replace(
        policy,
        by_asset={**policy.by_asset, "uranium": uranium_constraint},
    )
    with pytest.raises(VehicleSelectionError, match="no eligible direct"):
        select_metals_vehicles(
            "uranium",
            [VehicleCandidate("URA", 80), VehicleCandidate("URNM", 70)],
            registry=registry,
            policy=policy,
        )


def test_unknown_or_disabled_vehicle_fails_safely() -> None:
    with pytest.raises(VehicleSelectionError, match="unknown vehicle"):
        select_metals_vehicles("gold", [VehicleCandidate("FAKE", 70)])
    with pytest.raises(VehicleSelectionError, match="unknown asset"):
        select_metals_vehicles("missing", [VehicleCandidate("GLD", 70)])
