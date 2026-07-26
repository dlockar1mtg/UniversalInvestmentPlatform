from __future__ import annotations

import csv
from pathlib import Path

from foundation.intelligence.cross_domain.adapters.metals import build_metals_domain_package
from foundation.intelligence.cross_domain.allocator import load_domain_package, allocate_capital
from foundation.intelligence.cross_domain.contracts import AllocationPolicy


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["placeholder"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _package(root: Path, *, status: str = "READY", score: float = 82, confidence: float = 88) -> Path:
    _write(root / "asset_master.csv", [{
        "asset_id": "metals:metal:gold", "universal_asset_id": "metals:metal:gold",
        "asset_name": "Gold", "symbol": "GOLD",
    }])
    _write(root / "forecasts.csv", [{
        "asset_id": "metals:metal:gold", "universal_asset_id": "metals:metal:gold",
        "expected_return": "0.18", "forecast_horizon_months": "12",
    }])
    _write(root / "recommendations.csv", [{
        "recommendation_id": "metals:r1:gold", "asset_id": "metals:metal:gold",
        "universal_asset_id": "metals:metal:gold", "action": "RANKED_OPPORTUNITY",
        "normalized_score": str(score), "confidence_score": str(confidence),
        "target_weight_pct": "100", "rationale": "Certified opportunity", "source_run_id": "r1",
    }])
    _write(root / "risk_metrics.csv", [{
        "asset_id": "metals:metal:gold", "universal_asset_id": "metals:metal:gold", "risk_score": "22",
    }])
    _write(root / "portfolio_positions.csv", [{
        "asset_id": "metals:metal:gold", "universal_asset_id": "metals:metal:gold", "position_value": "250",
    }])
    _write(root / "platform_status.csv", [{
        "status": status, "run_status": "SUCCESS", "error_count": "0",
        "run_completed_at_utc": "2026-07-26T12:00:00+00:00",
    }])
    return root


def test_certified_metals_package_maps_to_uip_contract(tmp_path: Path) -> None:
    payload = build_metals_domain_package(_package(tmp_path), allocation_ceiling=3000)
    assert payload["domain_status"] == "PASS"
    assert payload["allocation_authority"] == "UIP"
    assert payload["scheduling_authority"] == "UIP"
    assert payload["deployable_opportunity_count"] == 1
    opportunity = payload["opportunities"][0]
    assert opportunity["signal"] == "STRONG_BUY"
    assert opportunity["eligible_for_new_capital"] is True
    assert opportunity["maximum_allocation"] == 3000
    assert opportunity["whole_units_required"] is False


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
    import json
    metals = build_metals_domain_package(_package(tmp_path / "metals", score=70, confidence=80), allocation_ceiling=3000)
    metals_path = tmp_path / "metals.json"
    metals_path.write_text(json.dumps(metals), encoding="utf-8")
    mtg = {
        "schema_version": "uip-domain-opportunity-v1", "domain": "mtg", "domain_status": "PASS",
        "allocation_authority": "UIP", "scheduling_authority": "UIP", "generated_at_utc": "2026-07-26T12:00:00Z",
        "opportunities": [{
            "opportunity_id": "mtg:box", "domain": "mtg", "asset_class": "collectibles", "asset_id": "box",
            "name": "Collector Box", "signal": "STRONG_BUY", "eligible_for_new_capital": True,
            "allocation_score": 90, "confidence_score": 90, "minimum_allocation": 500,
            "allocation_increment": 500, "maximum_allocation": 3000, "whole_units_required": True,
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
