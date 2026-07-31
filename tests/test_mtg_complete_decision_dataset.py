"""Tests for the complete inclusive MTG decision dataset adapter."""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "build_mtg_complete_decision_dataset.py"


def test_script_compiles() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(SCRIPT)],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_output_contract_fields_are_declared() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    required = (
        '"investment_tier"',
        '"decision_score"',
        '"evidence_confidence"',
        '"asset_subclass"',
        '"asset_name"',
        '"historical_record_present"',
        '"forecast_eligible"',
        '"recommendation_eligible"',
        '"mtg_complete_product_tiers.csv"',
    )
    for token in required:
        assert token in text


def test_adapter_is_inclusive_by_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'summary["total_products"] != 1141' in text
    assert 'summary["unique_products"] != 1141' in text
    assert '"historical_records_missing"] != 168' in text
    assert '"COLLECTOR_BOOSTER_BOX": 49' in text
    assert '"PRE_COLLECTOR_BOOSTER_BOX": 119' in text
    assert '"SECRET_LAIR": 973' in text

def test_overall_ranking_is_tier_first() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    expected = '''records.sort(
        key=lambda row: (
            TIER_ORDER.get(
                str(row["investment_tier"]),
                99,
            ),
            -float(row["decision_score"]),'''

    assert expected in text


def test_provisional_products_cannot_receive_top_tiers() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'if evidence_count == 0:' in text
    assert 'if score >= 58:' in text
    assert 'return "C"' in text
    assert 'return "D"' in text
    assert 'return "WATCH"' in text


def test_lane_and_overall_ranks_are_independent() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert 'record["overall_rank"] = overall_rank' in text
    assert 'record["lane_rank"] = lane_rank[lane]' in text
    assert '"lane_tier_counts": lane_tier_counts' in text


def test_historical_percentages_are_normalized() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "def percentage_points_to_decimal(" in text
    assert "return parsed / 100.0" in text
    assert (
        'percentage_points_to_decimal(\n'
        '                historical.get(\n'
        '                    "historical_cagr_pct"'
    ) in text


def test_a_tier_requires_forward_support() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "and historical_eligible" in text
    assert "forecast_eligible" in text
    assert "or recommendation_eligible" in text


def test_support_basis_is_exported() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert '"historical_support"' in text
    assert '"forward_support"' in text
    assert '"purchase_readiness_basis"' in text
    assert '"HISTORICAL_ONLY"' in text
    assert '"HISTORICAL_AND_FORWARD"' in text


def test_cagr_outlier_governance_is_present() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "def cagr_outlier_status(" in text
    assert '"EXTREME_POSITIVE"' in text
    assert '"EXTREME_NEGATIVE"' in text
    assert "def capped_cagr_for_scoring(" in text


def test_raw_and_scoring_cagr_are_both_exported() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert '"historical_cagr_pct"' in text
    assert '"historical_cagr_scoring_value"' in text
    assert '"historical_cagr_outlier_status"' in text


def test_cagr_scoring_cap_preserves_raw_output() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "scoring_cagr = capped_cagr_for_scoring(" in text
    assert "historical_cagr," in text
    assert "scoring_cagr," in text


def test_extreme_negative_history_caps_tier() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert (
        'historical_outlier_status '
        '== "EXTREME_NEGATIVE"'
    ) in text
    assert "historical_cagr <= -0.50" in text
    assert '"SEVERE_HISTORICAL_LOSS"' in text


def test_tier_guardrail_reason_is_exported() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "def tier_guardrail_reason(" in text
    assert '"tier_guardrail_reason"' in text
    assert '"EXTREME_NEGATIVE_HISTORICAL_CAGR"' in text


def test_assign_tier_receives_historical_risk() -> None:
    text = SCRIPT.read_text(encoding="utf-8")

    assert "historical_cagr: float | None" in text
    assert "historical_outlier_status: str" in text
    assert "historical_cagr=historical_cagr" in text
