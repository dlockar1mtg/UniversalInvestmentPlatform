from __future__ import annotations

import json
from dataclasses import asdict
from itertools import product
from pathlib import Path
from typing import Any, Iterable

from .contracts import (
    ALLOCATION_POLICY_VERSION,
    DOMAIN_SCHEMA_VERSION,
    AllocationPolicy,
    DomainOpportunity,
    DomainPackage,
)

DEPLOYABLE_SIGNALS = {"STRONG_BUY", "BUY", "ACCUMULATE"}
OPTIMIZER_STRATEGY = "hybrid-risk-adjusted-v2"
UTILITY_WEIGHTS = {
    "allocation_score": 0.45,
    "evidence_confidence": 0.20,
    "expected_return_strength": 0.25,
    "risk_safety": 0.10,
}


def _number(value: object, default: float = 0.0) -> float:
    try:
        text = str(value or "").replace("$", "").replace(",", "").strip()
        return float(text) if text else default
    except ValueError:
        return default


def _optional_number(value: object) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).replace("$", "").replace(",", "").strip())
    except ValueError:
        return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def load_domain_package(path: Path) -> DomainPackage:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != DOMAIN_SCHEMA_VERSION:
        raise ValueError(f"Unsupported domain schema: {payload.get('schema_version')}")
    if payload.get("allocation_authority") != "UIP":
        raise ValueError("Domain package does not assign allocation authority to UIP")
    if payload.get("scheduling_authority") != "UIP":
        raise ValueError("Domain package does not assign scheduling authority to UIP")
    opportunities: list[DomainOpportunity] = []
    for raw in payload.get("opportunities", []):
        opportunities.append(DomainOpportunity(
            opportunity_id=str(raw.get("opportunity_id") or ""),
            domain=str(raw.get("domain") or payload.get("domain") or "").lower(),
            asset_class=str(raw.get("asset_class") or "unknown"),
            asset_id=str(raw.get("asset_id") or ""),
            name=str(raw.get("name") or raw.get("asset_id") or ""),
            signal=str(raw.get("signal") or "").upper(),
            eligible_for_new_capital=bool(raw.get("eligible_for_new_capital")),
            allocation_score=_number(raw.get("allocation_score")),
            confidence_score=_number(raw.get("confidence_score")),
            minimum_allocation=_number(raw.get("minimum_allocation")),
            allocation_increment=_number(raw.get("allocation_increment")),
            maximum_allocation=_number(raw.get("maximum_allocation")),
            whole_units_required=bool(raw.get("whole_units_required")),
            metadata={key: value for key, value in raw.items() if key not in {
                "opportunity_id", "domain", "asset_class", "asset_id", "name", "signal",
                "eligible_for_new_capital", "allocation_score", "confidence_score",
                "minimum_allocation", "allocation_increment", "maximum_allocation",
                "whole_units_required",
            }},
        ))
    return DomainPackage(
        domain=str(payload.get("domain") or "").lower(),
        status=str(payload.get("domain_status") or "INCOMPLETE"),
        generated_at_utc=str(payload.get("generated_at_utc") or ""),
        opportunities=tuple(opportunities),
        assigned_carry_forward=_number(payload.get("assigned_carry_forward")),
    )


def _is_deployable(opportunity: DomainOpportunity, policy: AllocationPolicy) -> bool:
    return bool(
        opportunity.eligible_for_new_capital
        and opportunity.signal in DEPLOYABLE_SIGNALS
        and opportunity.allocation_score >= policy.minimum_deployment_score
        and opportunity.maximum_allocation > 0
        and (opportunity.allocation_increment or opportunity.minimum_allocation) > 0
    )


def _candidate_levels(opportunity: DomainOpportunity, policy: AllocationPolicy) -> list[float]:
    if not _is_deployable(opportunity, policy):
        return [0.0]
    increment = opportunity.allocation_increment or opportunity.minimum_allocation
    minimum = opportunity.minimum_allocation or increment
    maximum = min(opportunity.maximum_allocation, policy.deployable_budget)
    if minimum <= 0 or increment <= 0 or maximum + 1e-9 < minimum:
        return [0.0]
    levels = [0.0]
    value = minimum
    while value <= maximum + 1e-9:
        levels.append(round(value, 2))
        value += increment
    return sorted(set(levels))


def _utility_components(opportunity: DomainOpportunity) -> dict[str, float]:
    allocation_score = _clamp(opportunity.allocation_score)
    base_confidence = _clamp(opportunity.confidence_score)

    forecast_confidence = _optional_number(opportunity.metadata.get("forecast_confidence"))
    evidence_confidence = (
        (base_confidence + _clamp(forecast_confidence)) / 2.0
        if forecast_confidence is not None
        else base_confidence
    )

    expected_upside_pct = _optional_number(opportunity.metadata.get("expected_upside_pct"))
    expected_return = _optional_number(opportunity.metadata.get("expected_return"))
    if expected_upside_pct is not None:
        return_pct = expected_upside_pct
    elif expected_return is not None:
        return_pct = expected_return * 100.0 if abs(expected_return) <= 2.0 else expected_return
    else:
        return_pct = 0.0
    expected_return_strength = _clamp(50.0 + return_pct)

    probability_of_loss = _optional_number(opportunity.metadata.get("probability_of_loss"))
    risk_score = _optional_number(opportunity.metadata.get("risk_score"))
    if probability_of_loss is not None:
        risk_pct = probability_of_loss * 100.0 if abs(probability_of_loss) <= 1.0 else probability_of_loss
    elif risk_score is not None:
        risk_pct = risk_score
    else:
        risk_pct = 50.0
    risk_safety = _clamp(100.0 - risk_pct)

    cross_domain_score = (
        allocation_score * UTILITY_WEIGHTS["allocation_score"]
        + evidence_confidence * UTILITY_WEIGHTS["evidence_confidence"]
        + expected_return_strength * UTILITY_WEIGHTS["expected_return_strength"]
        + risk_safety * UTILITY_WEIGHTS["risk_safety"]
    )
    return {
        "allocation_score_component": round(allocation_score, 4),
        "evidence_confidence_component": round(evidence_confidence, 4),
        "expected_return_strength_component": round(expected_return_strength, 4),
        "risk_safety_component": round(risk_safety, 4),
        "cross_domain_score": round(_clamp(cross_domain_score), 4),
    }


def _utility_density(opportunity: DomainOpportunity) -> float:
    return _utility_components(opportunity)["cross_domain_score"] / 100.0


def _largest_feasible_amount(opportunity: DomainOpportunity, available: float) -> float:
    increment = opportunity.allocation_increment or opportunity.minimum_allocation
    minimum = opportunity.minimum_allocation or increment
    maximum = min(opportunity.maximum_allocation, available)
    if increment <= 0 or minimum <= 0 or maximum + 1e-9 < minimum:
        return 0.0
    steps = int((maximum - minimum + 1e-9) // increment)
    return round(minimum + steps * increment, 2)


def _fill_liquid_opportunities(
    liquid: list[DomainOpportunity],
    policy: AllocationPolicy,
    base_amounts: dict[str, float],
    base_domain_spend: dict[str, float],
    base_total: float,
) -> tuple[dict[str, float], dict[str, float], float]:
    amounts = dict(base_amounts)
    domain_spend = dict(base_domain_spend)
    total = round(base_total, 2)
    domain_limit = policy.deployable_budget * policy.maximum_domain_weight_pct / 100.0
    ordered = sorted(
        liquid,
        key=lambda opportunity: (
            -_utility_density(opportunity),
            -opportunity.allocation_score,
            -opportunity.confidence_score,
            opportunity.domain,
            opportunity.opportunity_id,
        ),
    )
    for opportunity in ordered:
        remaining_budget = round(policy.deployable_budget - total, 2)
        remaining_domain = round(domain_limit - domain_spend.get(opportunity.domain, 0.0), 2)
        available = min(remaining_budget, remaining_domain)
        amount = _largest_feasible_amount(opportunity, available)
        if amount <= 0:
            continue
        amounts[opportunity.opportunity_id] = amount
        total = round(total + amount, 2)
        domain_spend[opportunity.domain] = round(domain_spend.get(opportunity.domain, 0.0) + amount, 2)
    return amounts, domain_spend, total


def allocate_capital(packages: Iterable[DomainPackage], policy: AllocationPolicy) -> dict[str, Any]:
    package_list = list(packages)
    invalid_domains = sorted(pkg.domain for pkg in package_list if pkg.status != "PASS")
    opportunities = [
        opportunity
        for package in package_list
        if package.status == "PASS"
        for opportunity in package.opportunities
        if _is_deployable(opportunity, policy)
    ]
    discrete = [opportunity for opportunity in opportunities if opportunity.whole_units_required]
    liquid = [opportunity for opportunity in opportunities if not opportunity.whole_units_required]
    discrete_levels = [_candidate_levels(opportunity, policy) for opportunity in discrete]
    domain_limit = policy.deployable_budget * policy.maximum_domain_weight_pct / 100.0

    best: tuple[float, float, tuple[float, ...], dict[str, float]] | None = None
    combinations = product(*discrete_levels) if discrete_levels else [tuple()]
    for combination in combinations:
        total = round(sum(combination), 2)
        if total > policy.deployable_budget + 1e-9:
            continue
        domain_spend: dict[str, float] = {}
        amounts: dict[str, float] = {}
        valid = True
        for opportunity, amount in zip(discrete, combination):
            if amount <= 0:
                continue
            amounts[opportunity.opportunity_id] = amount
            domain_spend[opportunity.domain] = round(domain_spend.get(opportunity.domain, 0.0) + amount, 2)
            if domain_spend[opportunity.domain] > domain_limit + 1e-9:
                valid = False
                break
        if not valid:
            continue
        amounts, domain_spend, total = _fill_liquid_opportunities(liquid, policy, amounts, domain_spend, total)
        utility = sum(
            amount * _utility_density(opportunity)
            for opportunity in opportunities
            for amount in [amounts.get(opportunity.opportunity_id, 0.0)]
        )
        ordered_amounts = tuple(amounts.get(opportunity.opportunity_id, 0.0) for opportunity in opportunities)
        candidate = (round(utility, 8), total, ordered_amounts, amounts)
        if best is None or candidate[:3] > best[:3]:
            best = candidate

    selected_amounts = best[3] if best else {}
    allocations: list[dict[str, Any]] = []
    for opportunity in opportunities:
        amount = selected_amounts.get(opportunity.opportunity_id, 0.0)
        if amount <= 0:
            continue
        units = amount / opportunity.allocation_increment if opportunity.allocation_increment else 0.0
        components = _utility_components(opportunity)
        allocations.append({
            "opportunity_id": opportunity.opportunity_id,
            "domain": opportunity.domain,
            "asset_class": opportunity.asset_class,
            "asset_id": opportunity.asset_id,
            "name": opportunity.name,
            "signal": opportunity.signal,
            "allocation_score": opportunity.allocation_score,
            "confidence_score": opportunity.confidence_score,
            **components,
            "allocated_amount": round(amount, 2),
            "planned_units": round(units, 4) if opportunity.whole_units_required else "",
            "whole_units_required": opportunity.whole_units_required,
            "reason_codes": ["RISK_ADJUSTED_CROSS_DOMAIN_ALLOCATION_SELECTED"],
        })

    invested = round(sum(row["allocated_amount"] for row in allocations), 2)
    cash = round(policy.monthly_budget - invested, 2)
    by_domain: dict[str, float] = {}
    for row in allocations:
        by_domain[row["domain"]] = round(by_domain.get(row["domain"], 0.0) + row["allocated_amount"], 2)
    reason_codes = ["RISK_ADJUSTED_CROSS_DOMAIN_CAPITAL_ALLOCATION_COMPLETED"]
    if invested == 0:
        reason_codes.append("NO_OPPORTUNITY_CLEARED_DEPLOYMENT_POLICY")
    if invalid_domains:
        reason_codes.append("ONE_OR_MORE_DOMAIN_PACKAGES_EXCLUDED")

    return {
        "status": "PASS",
        "policy_version": ALLOCATION_POLICY_VERSION,
        "optimizer_strategy": OPTIMIZER_STRATEGY,
        "utility_weights": UTILITY_WEIGHTS,
        "monthly_budget": round(policy.monthly_budget, 2),
        "deployable_budget": policy.deployable_budget,
        "invested_amount": invested,
        "cash_allocation": cash,
        "cash_weight_pct": round(cash / policy.monthly_budget * 100.0, 2) if policy.monthly_budget else 0.0,
        "allocation_count": len(allocations),
        "domain_allocations": by_domain,
        "allocations": allocations,
        "invalid_or_incomplete_domains": invalid_domains,
        "reason_codes": reason_codes,
        "policy": asdict(policy),
    }


def write_allocation_plan(output_path: Path, packages: Iterable[DomainPackage], policy: AllocationPolicy) -> dict[str, Any]:
    payload = allocate_capital(packages, policy)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
