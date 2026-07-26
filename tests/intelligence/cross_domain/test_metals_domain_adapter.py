from __future__ import annotations

import csv
import json
from pathlib import Path

from foundation.intelligence.cross_domain.adapters.metals import build_metals_domain_package
from foundation.intelligence.cross_domain.allocator import allocate_capital, load_domain_package
from foundation.intelligence.cross_domain.contracts import AllocationPolicy


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["placeholder"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _package(
    root: Path,
    *,
    status: str = "READY",
    run_status: str = "SUCCESS",
    warnings: int = 0,
    score: float = 82,
    confidence: float = 88,
    expected_return: float = 0.18,
) -> Path:
    _write(root / "asset_master.csv", [
        {
            "universal_asset_id": "metals:commodity:gold",
            "asset_name": "Gold",
            "asset_symbol": "GOLD",
        },
        {
            "universal_asset_id": "metals:vehicle:GLD",
            "asset_name": "GLD",
            "asset_symbol": "GLD",
        },
    ])
    _write(root / "forecasts.csv", [{
        "universal_asset_id": "metals:commodity:gold",
        "expected_total_return": str(expected_return),
        "forecast_confidence": "72",
        "forecast_horizon_months": "12",
    }])
    _write(root / "recommendations.csv", [{
        "universal_asset_id": "metals:vehicle:GLD",
        "recommendation": "BUY",
        "normalized_score": str(score),
        "confidence_score": str(confidence),
        "target_weight": "100",
        "rationale_summary": "Certified opportunity",
        "run_id": "r1",
    }])
    _write(root / "risk_metrics.csv", [{
        "universal_asset_id": "metals:vehicle:GLD",
        "risk_score": "22",
    }])
    _write(root / "portfolio_positions.csv", [{
        "universal_asset_id": "metals:vehicle:GLD",
        "position_value": "250",
    }])
    _write(root / "platform_status.csv", [{
        "status": status,
        "run_status": run_status,
        "warning_count": str(warnings),
        "error_count": "0",
        "run_completed_at_utc": "2026-07-26T12:00:00+00:00",
    }])
    return root


def test_certified_metals_vehicle_maps_underlying_forecast_to_uip_contract(tmp_path: Path) -> None:
    payload = build_metals_domain_package(_package(tmp_path), allocation_ceiling=3000)
    assert payload["domain_status"] == "PASS"
    assert payload["allocation_authority"] == "UIP"
    assert payload["scheduling_authority"] == "UIP"
    assert payload["forecast_horizon_months"] == 12
    assert payload["deployable_opportunity_count"] == 1
    opportunity = payload["opportunities"][0]
    assert opportunity["signal"] == "BUY"
    assert opportunity["eligible_for_new_capital"] is True
    assert opportunity["expected_return"] == 0.18
    assert opportunity["forecast_asset_id"] == "metals:commodity:gold"
    assert opportunity["forecast_horizon_months"] == 12
    assert opportunity["current_position_value"] == 250
    assert opportunity["maximum_allocation"] == 3000
    assert "UNDERLYING_COMMODITY_FORECAST_LINKED" in opportunity["evidence_reason_codes"]


def test_blank_legacy_status_accepts_success_with_no_warnings_or_errors(tmp_path: Path) -> None:
    payload = build_metals_domain_package(_package(tmp_path, status=""), allocation_ceiling=3000)
    assert payload["domain_status"] == "PASS"
    assert payload["deployable_opportunity_count"] == 1


def test_legacy_success_with_warning_fails_closed(tmp_path: Path) -> None:
    payload = build_metals_domain_package(
        _package(tmp_path, status="", warnings=1),
        allocation_ceiling=3000,
    )
    assert payload["domain_status"] == "INCOMPLETE"
    assert payload["deployable_opportunity_count"] == 0


def test_buy_without_positive_forecast_is_capped_at_watch(tmp_path: Path) -> None:
    payload = build_metals_domain_package(
        _package(tmp_path, expected_return=-0.02),
        allocation_ceiling=3000,
    )
    opportunity = payload["opportunities"][0]
    assert opportunity["signal"] == "WATCH"
    assert opportunity["eligible_for_new_capital"] is False
    assert opportunity["expected_return"] == -0.02


def test_missing_forecast_is_not_manufactured_as_zero(tmp_path: Path) -> None:
    root = _package(tmp_path)
    _write(root / "forecasts.csv", [{
        "universal_asset_id": "metals:commodity:silver",
        "expected_total_return": "0.20",
        "forecast_horizon_months": "12",
    }])
    payload = build_metals_domain_package(root, allocation_ceiling=3000)
    opportunity = payload["opportunities"][0]
    assert opportunity["expected_return"] is None
    assert opportunity["signal"] == "WATCH"
    assert opportunity["eligible_for_new_capital"] is False
    assert "FORECAST_EVIDENCE_MISSING" in opportunity["evidence_reason_codes"]


def test_not_ready_metals_package_fails_closed(tmp_path: Path) -> None:
    payload = build_metals_domain_package(_package(tmp_path, status="DEGRADED"), allocation_ceiling=3000)
    assert payload["domain_status"] == "INCOMPLETE"
    assert payload["deployable_opportunity_count"] == 0
    assert payload["opportunities"][0]["eligible_for_new_capital"] is False


def test_missing_contract_file_is_reported(tmp_path: Path) -> None:
    payload = build_metals_domain_package(tmp_path, allocation_ceiling=3000)
    assert payload["domain_status"] == "INCOMPLETE"
    assert "recommendations.csv" in payload["missing_files"]


def test_metals_and_mtg_can_compete_in_allocator(tmp_path: Path) -> None:
    metals = build_metals_domain_package(
        _package(tmp_path / "metals", score=70, confidence=80),
        allocation_ceiling=3000,
    )
    metals_path = tmp_path / "metals.json"
    metals_path.write_text(json.dumps(metals), encoding="utf-8")
    mtg = {
        "schema_version": "uip-domain-opportunity-v1",
        "domain": "mtg",
        "domain_status": "PASS",
        "allocation_authority": "UIP",
        "scheduling_authority": "UIP",
        "generated_at_utc": "2026-07-26T12:00:00Z",
        "opportunities": [{
            "opportunity_id": "mtg:box",
            "domain": "mtg",
            "asset_class": "collectibles",
            "asset_id": "box",
            "name": "Collector Box",
            "signal": "STRONG_BUY",
            "eligible_for_new_capital": True,
            "allocation_score": 90,
            "confidence_score": 90,
            "minimum_allocation": 500,
            "allocation_increment": 500,
            "maximum_allocation": 3000,
            "whole_units_required": True,
        }],
    }
    mtg_path = tmp_path / "mtg.json"
    mtg_path.write_text(json.dumps(mtg), encoding="utf-8")
    result = allocate_capital(
        [load_domain_package(metals_path), load_domain_package(mtg_path)],
        AllocationPolicy(monthly_budget=3000, minimum_deployment_score=55),
    )
    assert result["status"] == "PASS"
    assert result["invested_amount"] == 3000
    assert set(result["domain_allocations"]).issubset({"metals", "mtg"})
