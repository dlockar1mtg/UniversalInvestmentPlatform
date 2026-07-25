from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True, slots=True)
class MetalsVehicleRiskInput:
    asset_id: str
    vehicle_ticker: str
    approved: bool
    metadata_current: bool
    average_daily_volume: float
    spread_pct: float
    expense_ratio_pct: float
    roll_drag_pct: float
    miner_beta: float
    single_company_concentration_pct: float
    single_country_concentration_pct: float
    currency_exposure_pct: float
    tax_structure: str
    overlap_pct: float
    factor_exposure_score: float


@dataclass(frozen=True, slots=True)
class MetalsVehicleConstraintResult:
    asset_id: str
    vehicle_ticker: str
    eligibility_status: str
    maximum_allocation_pct: float
    hard_blocked: bool
    reason_codes: str
    validation_status: str


def _cap(current: float, candidate: float) -> float:
    return round(min(current, candidate), 6)


def evaluate_vehicle_constraint(
    item: MetalsVehicleRiskInput,
    policy: dict,
) -> MetalsVehicleConstraintResult:
    reasons: list[str] = []
    cap = float(policy["base_allocation_cap_pct"])
    blocked = False

    if policy.get("hard_block_if_unapproved", True) and not item.approved:
        blocked = True
        reasons.append("VEHICLE_NOT_APPROVED")
    if policy.get("hard_block_if_metadata_stale", True) and not item.metadata_current:
        blocked = True
        reasons.append("METADATA_STALE")
    if item.tax_structure in set(policy.get("blocked_tax_structures", [])):
        blocked = True
        reasons.append("TAX_STRUCTURE_BLOCKED")
    if item.tax_structure not in set(policy.get("allowed_tax_structures", [])):
        blocked = True
        reasons.append("TAX_STRUCTURE_NOT_ALLOWED")

    if item.average_daily_volume < float(policy["minimum_average_daily_volume"]):
        cap = _cap(cap, 2.0)
        reasons.append("LOW_LIQUIDITY")
    if item.spread_pct > float(policy["maximum_spread_pct"]):
        cap = _cap(cap, 1.0)
        reasons.append("WIDE_SPREAD")
    if item.expense_ratio_pct > float(policy["maximum_expense_ratio_pct"]):
        cap = _cap(cap, 3.0)
        reasons.append("HIGH_EXPENSE_RATIO")
    if item.roll_drag_pct > float(policy["maximum_roll_drag_pct"]):
        cap = _cap(cap, 2.0)
        reasons.append("HIGH_ROLL_DRAG")
    if item.miner_beta > float(policy["maximum_miner_beta"]):
        cap = _cap(cap, 3.0)
        reasons.append("HIGH_MINER_BETA")
    if item.single_company_concentration_pct > float(policy["maximum_single_company_concentration_pct"]):
        cap = _cap(cap, 2.5)
        reasons.append("COMPANY_CONCENTRATION")
    if item.single_country_concentration_pct > float(policy["maximum_single_country_concentration_pct"]):
        cap = _cap(cap, 3.0)
        reasons.append("COUNTRY_CONCENTRATION")
    if item.currency_exposure_pct > float(policy["maximum_currency_exposure_pct"]):
        cap = _cap(cap, 3.0)
        reasons.append("CURRENCY_EXPOSURE")
    if item.overlap_pct > float(policy["maximum_overlap_pct"]):
        cap = _cap(cap, 2.0)
        reasons.append("PORTFOLIO_OVERLAP")
    if item.factor_exposure_score > float(policy["maximum_factor_exposure_score"]):
        cap = _cap(cap, 2.5)
        reasons.append("FACTOR_EXPOSURE")

    if blocked:
        status = "BLOCKED"
        cap = 0.0
    elif reasons:
        status = "CAPPED"
    else:
        status = "ELIGIBLE"
        reasons.append("WITHIN_POLICY")

    return MetalsVehicleConstraintResult(
        asset_id=item.asset_id,
        vehicle_ticker=item.vehicle_ticker,
        eligibility_status=status,
        maximum_allocation_pct=cap,
        hard_blocked=blocked,
        reason_codes="|".join(reasons),
        validation_status="PASS",
    )


def evaluate_vehicle_constraints(
    items: Iterable[MetalsVehicleRiskInput],
    policy: dict,
) -> tuple[MetalsVehicleConstraintResult, ...]:
    rows = tuple(evaluate_vehicle_constraint(item, policy) for item in items)
    tickers = [row.vehicle_ticker for row in rows]
    if len(tickers) != len(set(tickers)):
        raise ValueError("Duplicate vehicle_ticker values are not allowed.")
    return rows


def summarize_vehicle_constraints(rows: Iterable[MetalsVehicleConstraintResult]) -> dict:
    values = tuple(rows)
    return {
        "status": "PASS" if values else "NO_VEHICLES",
        "vehicle_count": len(values),
        "eligible_count": sum(row.eligibility_status == "ELIGIBLE" for row in values),
        "capped_count": sum(row.eligibility_status == "CAPPED" for row in values),
        "blocked_count": sum(row.eligibility_status == "BLOCKED" for row in values),
        "fail_closed": True,
    }


def publish_vehicle_constraints(rows: Iterable[MetalsVehicleConstraintResult], summary: dict, output_root: Path) -> None:
    values = tuple(rows)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "metals_vehicle_constraint_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_root / "metals_vehicle_constraints.json").write_text(
        json.dumps([asdict(row) for row in values], indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fieldnames = list(asdict(values[0]).keys()) if values else [
        "asset_id", "vehicle_ticker", "eligibility_status", "maximum_allocation_pct",
        "hard_blocked", "reason_codes", "validation_status"
    ]
    with (output_root / "metals_vehicle_constraints.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(row) for row in values)
