from pathlib import Path

import pytest

from foundation.production.metals_risk_aware_constraints import (
    MetalsVehicleRiskInput,
    evaluate_vehicle_constraint,
    evaluate_vehicle_constraints,
    publish_vehicle_constraints,
    summarize_vehicle_constraints,
)


POLICY = {
    "base_allocation_cap_pct": 10.0,
    "minimum_average_daily_volume": 100000,
    "maximum_spread_pct": 0.75,
    "maximum_expense_ratio_pct": 1.0,
    "maximum_roll_drag_pct": 2.0,
    "maximum_miner_beta": 1.75,
    "maximum_single_company_concentration_pct": 20.0,
    "maximum_single_country_concentration_pct": 45.0,
    "maximum_currency_exposure_pct": 50.0,
    "maximum_overlap_pct": 35.0,
    "maximum_factor_exposure_score": 70.0,
    "allowed_tax_structures": ["grantor_trust", "regulated_investment_company"],
    "blocked_tax_structures": ["unknown", "unverified"],
    "hard_block_if_unapproved": True,
    "hard_block_if_metadata_stale": True,
}


def vehicle(**changes):
    data = dict(
        asset_id="gold", vehicle_ticker="IAU", approved=True, metadata_current=True,
        average_daily_volume=5000000, spread_pct=0.03, expense_ratio_pct=0.25,
        roll_drag_pct=0.0, miner_beta=0.0, single_company_concentration_pct=0.0,
        single_country_concentration_pct=0.0, currency_exposure_pct=0.0,
        tax_structure="grantor_trust", overlap_pct=10.0, factor_exposure_score=20.0,
    )
    data.update(changes)
    return MetalsVehicleRiskInput(**data)


def test_clean_vehicle_is_eligible():
    row = evaluate_vehicle_constraint(vehicle(), POLICY)
    assert row.eligibility_status == "ELIGIBLE"
    assert row.maximum_allocation_pct == 10.0
    assert row.reason_codes == "WITHIN_POLICY"


def test_overlap_caps_allocation():
    row = evaluate_vehicle_constraint(vehicle(overlap_pct=50.0), POLICY)
    assert row.eligibility_status == "CAPPED"
    assert row.maximum_allocation_pct == 2.0
    assert "PORTFOLIO_OVERLAP" in row.reason_codes


def test_unapproved_vehicle_is_blocked():
    row = evaluate_vehicle_constraint(vehicle(approved=False), POLICY)
    assert row.eligibility_status == "BLOCKED"
    assert row.maximum_allocation_pct == 0.0
    assert row.hard_blocked is True


def test_multiple_risks_use_lowest_cap():
    row = evaluate_vehicle_constraint(
        vehicle(spread_pct=1.0, miner_beta=2.0, factor_exposure_score=80.0), POLICY
    )
    assert row.maximum_allocation_pct == 1.0
    assert row.eligibility_status == "CAPPED"


def test_duplicate_ticker_rejected():
    with pytest.raises(ValueError):
        evaluate_vehicle_constraints((vehicle(), vehicle(asset_id="silver")), POLICY)


def test_summary_and_publication(tmp_path: Path):
    rows = evaluate_vehicle_constraints((vehicle(), vehicle(vehicle_ticker="SLV", overlap_pct=50.0)), POLICY)
    summary = summarize_vehicle_constraints(rows)
    publish_vehicle_constraints(rows, summary, tmp_path)
    assert summary == {
        "status": "PASS", "vehicle_count": 2, "eligible_count": 1,
        "capped_count": 1, "blocked_count": 0, "fail_closed": True,
    }
    assert (tmp_path / "metals_vehicle_constraints.csv").exists()
    assert (tmp_path / "metals_vehicle_constraint_summary.json").exists()
