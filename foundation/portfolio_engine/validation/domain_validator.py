"""Validation helpers for Phase 2.1 portfolio configuration."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

from foundation.portfolio_engine.models import AssetCategory


@dataclass(slots=True)
class ValidationResult:
    errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return payload


def validate_portfolio_configuration(config_dir: Path) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    portfolio = _load_yaml(config_dir / "default_portfolio.yaml")
    targets = _load_yaml(config_dir / "allocation_targets.yaml")
    policy = _load_yaml(config_dir / "rebalance_policy.yaml")

    portfolio_node = portfolio.get("portfolio", {})
    if not str(portfolio_node.get("name", "")).strip():
        errors.append("default_portfolio.yaml: portfolio.name is required.")

    monthly = Decimal(str(portfolio_node.get("monthly_contribution", 0)))
    if monthly < 0:
        errors.append("default_portfolio.yaml: monthly_contribution cannot be negative.")

    target_rows = targets.get("allocation_targets")
    if not isinstance(target_rows, list) or not target_rows:
        errors.append("allocation_targets.yaml: allocation_targets must be a non-empty list.")
        target_rows = []

    valid_categories = {member.value for member in AssetCategory}
    total = Decimal("0")
    observed: set[str] = set()

    for index, row in enumerate(target_rows, start=1):
        category = str(row.get("category", "")).strip()
        if category not in valid_categories:
            errors.append(f"allocation_targets.yaml row {index}: invalid category '{category}'.")
        if category in observed:
            errors.append(f"allocation_targets.yaml row {index}: duplicate category '{category}'.")
        observed.add(category)

        minimum = Decimal(str(row.get("minimum_weight", 0)))
        target = Decimal(str(row.get("target_weight", 0)))
        maximum = Decimal(str(row.get("maximum_weight", 0)))
        total += target

        if not Decimal("0") <= minimum <= target <= maximum <= Decimal("1"):
            errors.append(
                f"allocation_targets.yaml row {index}: expected "
                "0 <= minimum_weight <= target_weight <= maximum_weight <= 1."
            )

    if abs(total - Decimal("1")) > Decimal("0.000001"):
        errors.append(f"Allocation target weights total {total}; expected 1.0.")

    method = str(policy.get("rebalance_policy", {}).get("method", ""))
    if method != "contribution_only":
        warnings.append(
            "Initial Phase 2 policy is expected to use contribution_only rebalancing."
        )

    return ValidationResult(errors=errors, warnings=warnings)
