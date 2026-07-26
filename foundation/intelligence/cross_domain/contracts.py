from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DOMAIN_SCHEMA_VERSION = "uip-domain-opportunity-v1"
ALLOCATION_POLICY_VERSION = "6.0.0"


@dataclass(frozen=True)
class DomainOpportunity:
    opportunity_id: str
    domain: str
    asset_class: str
    asset_id: str
    name: str
    signal: str
    eligible_for_new_capital: bool
    allocation_score: float
    confidence_score: float
    minimum_allocation: float
    allocation_increment: float
    maximum_allocation: float
    whole_units_required: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DomainPackage:
    domain: str
    status: str
    generated_at_utc: str
    opportunities: tuple[DomainOpportunity, ...]
    assigned_carry_forward: float = 0.0


@dataclass(frozen=True)
class AllocationPolicy:
    monthly_budget: float
    minimum_deployment_score: float = 55.0
    maximum_domain_weight_pct: float = 100.0
    minimum_cash_reserve_pct: float = 0.0
    policy_version: str = ALLOCATION_POLICY_VERSION

    @property
    def deployable_budget(self) -> float:
        return round(self.monthly_budget * (1.0 - self.minimum_cash_reserve_pct / 100.0), 2)
