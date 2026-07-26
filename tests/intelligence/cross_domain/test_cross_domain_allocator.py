from __future__ import annotations

from foundation.intelligence.cross_domain import AllocationPolicy, DomainOpportunity, DomainPackage, allocate_capital


def _package(domain: str, opportunities: list[DomainOpportunity], status: str = "PASS") -> DomainPackage:
    return DomainPackage(domain=domain, status=status, generated_at_utc="2026-07-26T00:00:00+00:00", opportunities=tuple(opportunities))


def _opportunity(
    domain: str,
    asset_id: str,
    score: float,
    minimum: float,
    maximum: float,
    signal: str = "STRONG_BUY",
    confidence: float = 90.0,
    *,
    increment: float | None = None,
    whole_units_required: bool = True,
) -> DomainOpportunity:
    return DomainOpportunity(
        opportunity_id=f"{domain}:{asset_id}",
        domain=domain,
        asset_class=domain,
        asset_id=asset_id,
        name=asset_id,
        signal=signal,
        eligible_for_new_capital=True,
        allocation_score=score,
        confidence_score=confidence,
        minimum_allocation=minimum,
        allocation_increment=increment if increment is not None else minimum,
        maximum_allocation=maximum,
        whole_units_required=whole_units_required,
    )


def test_all_budget_can_go_to_mtg_when_other_domains_are_not_buyable() -> None:
    mtg = _package("mtg", [_opportunity("mtg", "double-masters", 82, 500, 3000)])
    metals = _package("metals", [_opportunity("metals", "gold", 40, 100, 3000, signal="WATCH")])
    crypto = _package("crypto", [], status="INCOMPLETE")
    result = allocate_capital([mtg, metals, crypto], AllocationPolicy(monthly_budget=3000))
    assert result["invested_amount"] == 3000
    assert result["domain_allocations"] == {"mtg": 3000.0}
    assert result["cash_allocation"] == 0
    assert result["invalid_or_incomplete_domains"] == ["crypto"]


def test_cash_receives_full_budget_when_nothing_clears_policy() -> None:
    metals = _package("metals", [_opportunity("metals", "gold", 40, 100, 3000, signal="BUY")])
    result = allocate_capital([metals], AllocationPolicy(monthly_budget=3000, minimum_deployment_score=55))
    assert result["invested_amount"] == 0
    assert result["cash_allocation"] == 3000
    assert "NO_OPPORTUNITY_CLEARED_DEPLOYMENT_POLICY" in result["reason_codes"]


def test_allocator_can_split_budget_across_domains() -> None:
    mtg = _package("mtg", [_opportunity("mtg", "box", 80, 500, 1000)])
    stocks = _package("stocks", [_opportunity("stocks", "etf", 75, 500, 2000)])
    result = allocate_capital([mtg, stocks], AllocationPolicy(monthly_budget=3000))
    assert result["invested_amount"] == 3000
    assert result["domain_allocations"]["mtg"] == 1000
    assert result["domain_allocations"]["stocks"] == 2000


def test_domain_cap_is_enforced() -> None:
    mtg = _package("mtg", [_opportunity("mtg", "box", 90, 500, 3000)])
    result = allocate_capital([mtg], AllocationPolicy(monthly_budget=3000, maximum_domain_weight_pct=50))
    assert result["domain_allocations"]["mtg"] == 1500
    assert result["cash_allocation"] == 1500


def test_minimum_cash_reserve_is_preserved() -> None:
    mtg = _package("mtg", [_opportunity("mtg", "box", 90, 300, 3000)])
    result = allocate_capital([mtg], AllocationPolicy(monthly_budget=3000, minimum_cash_reserve_pct=10))
    assert result["invested_amount"] == 2700
    assert result["cash_allocation"] == 300


def test_precise_liquid_increments_do_not_create_cartesian_explosion() -> None:
    metals = _package("metals", [
        _opportunity(
            "metals",
            f"asset-{index}",
            90 - index,
            1,
            3000,
            confidence=90 - index,
            increment=1,
            whole_units_required=False,
        )
        for index in range(6)
    ])
    result = allocate_capital([metals], AllocationPolicy(monthly_budget=3000))
    assert result["optimizer_strategy"] == "hybrid-discrete-liquid-v1"
    assert result["invested_amount"] == 3000
    assert result["allocation_count"] == 1
    assert result["allocations"][0]["allocated_amount"] == 3000


def test_mixed_whole_unit_and_liquid_opportunities_are_supported() -> None:
    mtg = _package("mtg", [
        _opportunity(
            "mtg",
            "collector-box",
            95,
            434.07,
            868.14,
            confidence=95,
            increment=434.07,
            whole_units_required=True,
        )
    ])
    metals = _package("metals", [
        _opportunity(
            "metals",
            "gold-etf",
            80,
            1,
            3000,
            confidence=80,
            increment=1,
            whole_units_required=False,
        )
    ])
    result = allocate_capital([mtg, metals], AllocationPolicy(monthly_budget=3000))
    assert result["optimizer_strategy"] == "hybrid-discrete-liquid-v1"
    assert result["invested_amount"] <= 3000
    assert any(row["domain"] == "mtg" for row in result["allocations"])
    assert any(row["domain"] == "metals" for row in result["allocations"])
