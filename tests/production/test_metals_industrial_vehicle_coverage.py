from __future__ import annotations

import json
from pathlib import Path

import pytest

from foundation.production.metals_industrial_vehicle_coverage import (
    publish_industrial_vehicle_coverage,
    summarize_industrial_vehicle_coverage,
    validate_industrial_vehicle_coverage,
)


def _document() -> dict[str, object]:
    return {
        "policy": {"fail_closed": True},
        "metals": [
            {
                "metal_id": metal,
                "benchmark_symbol": None,
                "coverage_status": "RESEARCH_ONLY",
                "approved_vehicle_ticker": None,
                "candidate_vehicles": [],
                "candidate_structure": None,
                "candidate_exposure": None,
                "decision_reason": "No approved vehicle.",
                "selection_eligible": False,
                "source_refs": [],
            }
            for metal in ("aluminum", "zinc", "nickel", "tin")
        ],
    }


def test_required_industrial_metals_pass_fail_closed_validation() -> None:
    rows = validate_industrial_vehicle_coverage(_document())
    summary = summarize_industrial_vehicle_coverage(rows)
    assert len(rows) == 4
    assert summary["status"] == "PASS"
    assert summary["eligible_metal_count"] == 0
    assert summary["blocked_metal_count"] == 4


def test_missing_required_metal_fails() -> None:
    document = _document()
    document["metals"] = document["metals"][:-1]
    with pytest.raises(ValueError, match="exactly match"):
        validate_industrial_vehicle_coverage(document)


def test_research_only_cannot_be_selection_eligible() -> None:
    document = _document()
    document["metals"][0]["selection_eligible"] = True
    document["metals"][0]["approved_vehicle_ticker"] = "JJU"
    with pytest.raises(ValueError, match="ineligible coverage state"):
        validate_industrial_vehicle_coverage(document)


def test_approved_vehicle_state_can_be_selection_eligible() -> None:
    document = _document()
    document["metals"][0].update(
        {
            "coverage_status": "FUTURES_ONLY",
            "approved_vehicle_ticker": "TEST",
            "selection_eligible": True,
        }
    )
    rows = validate_industrial_vehicle_coverage(document)
    assert rows[0].selection_eligible is True


def test_outputs_are_published(tmp_path: Path) -> None:
    rows = validate_industrial_vehicle_coverage(_document())
    summary = summarize_industrial_vehicle_coverage(rows)
    publish_industrial_vehicle_coverage(rows, summary, tmp_path)
    assert (tmp_path / "industrial_vehicle_coverage.csv").exists()
    payload = json.loads(
        (tmp_path / "industrial_vehicle_coverage_summary.json").read_text(encoding="utf-8")
    )
    assert payload["metal_count"] == 4
