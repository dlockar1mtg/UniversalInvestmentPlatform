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
    metadata: dict[str, object] | None = None,
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
        metadata=metadata or {},
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
    assert result["optimizer_strategy"] == "hybrid-risk-adjusted-v2"
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
            metadata={"expected_upside_pct": 35, "probability_of_loss": 0.10},
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
            metadata={"expected_return": 0.10, "forecast_confidence": 60, "risk_score": 15},
        )
    ])
    result = allocate_capital([mtg, metals], AllocationPolicy(monthly_budget=3000))
    assert result["optimizer_strategy"] == "hybrid-risk-adjusted-v2"
    assert result["invested_amount"] <= 3000
    assert any(row["domain"] == "mtg" for row in result["allocations"])
    assert any(row["domain"] == "metals" for row in result["allocations"])


def test_expected_return_and_risk_change_cross_domain_priority() -> None:
    mtg = _package("mtg", [
        _opportunity(
            "mtg",
            "box",
            72,
            434.07,
            868.14,
            confidence=76,
            metadata={"expected_upside_pct": 37.23, "probability_of_loss": 0.107},
        )
    ])
    metals = _package("metals", [
        _opportunity(
            "metals",
            "silver-etf",
            86,
            1,
            3000,
            confidence=86,
            increment=1,
            whole_units_required=False,
            metadata={"expected_return": 0.2556, "forecast_confidence": 0, "risk_score": 10.66},
        )
    ])
    result = allocate_capital([mtg, metals], AllocationPolicy(monthly_budget=1000))
    mtg_row = next(row for row in result["allocations"] if row["domain"] == "mtg")
    metals_row = next(row for row in result["allocations"] if row["domain"] == "metals")
    assert mtg_row["cross_domain_score"] > metals_row["cross_domain_score"]
    assert mtg_row["allocated_amount"] == 868.14


def test_allocation_output_explains_utility_components() -> None:
    metals = _package("metals", [
        _opportunity(
            "metals",
            "gold-etf",
            90,
            1,
            100,
            confidence=80,
            increment=1,
            whole_units_required=False,
            metadata={"expected_return": 0.12, "forecast_confidence": 60, "risk_score": 20},
        )
    ])
    result = allocate_capital([metals], AllocationPolicy(monthly_budget=100))
    row = result["allocations"][0]
    assert result["utility_weights"]["expected_return_strength"] == 0.25
    assert row["evidence_confidence_component"] == 70
    assert row["expected_return_strength_component"] == 62
    assert row["risk_safety_component"] == 80
    assert row["cross_domain_score"] > 0
