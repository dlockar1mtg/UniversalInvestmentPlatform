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


def _number(value: object, default: float = 0.0) -> float:
    try:
        text = str(value or "").replace("$", "").replace(",", "").strip()
        return float(text) if text else default
    except ValueError:
        return default


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


def _candidate_levels(opportunity: DomainOpportunity, policy: AllocationPolicy) -> list[float]:
    if (
        not opportunity.eligible_for_new_capital
        or opportunity.signal not in DEPLOYABLE_SIGNALS
        or opportunity.allocation_score < policy.minimum_deployment_score
        or opportunity.maximum_allocation <= 0
    ):
        return [0.0]
    increment = opportunity.allocation_increment or opportunity.minimum_allocation
    if increment <= 0:
        return [0.0]
    maximum = min(opportunity.maximum_allocation, policy.deployable_budget)
    levels = [0.0]
    value = opportunity.minimum_allocation
    while value <= maximum + 1e-9:
        levels.append(round(value, 2))
        value += increment
    return sorted(set(levels))


def allocate_capital(
    packages: Iterable[DomainPackage],
    policy: AllocationPolicy,
) -> dict[str, Any]:
    package_list = list(packages)
    invalid_domains = sorted(pkg.domain for pkg in package_list if pkg.status != "PASS")
    opportunities = [
        opportunity
        for package in package_list
        if package.status == "PASS"
        for opportunity in package.opportunities
    ]
    levels = [_candidate_levels(opportunity, policy) for opportunity in opportunities]
    best: tuple[float, float, tuple[float, ...]] | None = None
    domain_limit = policy.deployable_budget * policy.maximum_domain_weight_pct / 100.0

    for combination in product(*levels) if levels else [tuple()]:
        total = round(sum(combination), 2)
        if total > policy.deployable_budget + 1e-9:
            continue
        by_domain: dict[str, float] = {}
        for opportunity, amount in zip(opportunities, combination):
            by_domain[opportunity.domain] = by_domain.get(opportunity.domain, 0.0) + amount
        if any(amount > domain_limit + 1e-9 for amount in by_domain.values()):
            continue
        utility = sum(
            amount
            * (opportunity.allocation_score / 100.0)
            * (0.5 + opportunity.confidence_score / 200.0)
            for opportunity, amount in zip(opportunities, combination)
        )
        candidate = (round(utility, 8), total, tuple(combination))
        if best is None or candidate > best:
            best = candidate

    selected = best[2] if best else tuple(0.0 for _ in opportunities)
    allocations: list[dict[str, Any]] = []
    for opportunity, amount in zip(opportunities, selected):
        if amount <= 0:
            continue
        units = amount / opportunity.allocation_increment if opportunity.allocation_increment else 0.0
        allocations.append({
            "opportunity_id": opportunity.opportunity_id,
            "domain": opportunity.domain,
            "asset_class": opportunity.asset_class,
            "asset_id": opportunity.asset_id,
            "name": opportunity.name,
            "signal": opportunity.signal,
            "allocation_score": opportunity.allocation_score,
            "confidence_score": opportunity.confidence_score,
            "allocated_amount": round(amount, 2),
            "planned_units": round(units, 4) if opportunity.whole_units_required else "",
            "whole_units_required": opportunity.whole_units_required,
            "reason_codes": ["CROSS_DOMAIN_ALLOCATION_SELECTED"],
        })

    invested = round(sum(row["allocated_amount"] for row in allocations), 2)
    cash = round(policy.monthly_budget - invested, 2)
    by_domain: dict[str, float] = {}
    for row in allocations:
        by_domain[row["domain"]] = round(by_domain.get(row["domain"], 0.0) + row["allocated_amount"], 2)
    status = "PASS"
    reason_codes = ["CROSS_DOMAIN_CAPITAL_ALLOCATION_COMPLETED"]
    if invested == 0:
        reason_codes.append("NO_OPPORTUNITY_CLEARED_DEPLOYMENT_POLICY")
    if invalid_domains:
        reason_codes.append("ONE_OR_MORE_DOMAIN_PACKAGES_EXCLUDED")

    return {
        "status": status,
        "policy_version": ALLOCATION_POLICY_VERSION,
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
