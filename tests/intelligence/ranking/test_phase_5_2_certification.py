import json

from foundation.intelligence.ranking.certification import (
    CertificationStatus,
    certify_phase_5_2,
)
from foundation.intelligence.ranking.competition import CompetitionPolicy
from foundation.intelligence.ranking.orchestrator import PortfolioRankingItem


def cross_asset_items():
    return [
        PortfolioRankingItem("BTC", 92, "P1", {"confidence": 85}, group_key="crypto"),
        PortfolioRankingItem("VOO", 88, "P1", {"confidence": 90}, group_key="etf"),
        PortfolioRankingItem("GLD", 81, "P2", {"confidence": 80}, group_key="metals"),
        PortfolioRankingItem("MTG-BOX", 74, "P3", {"confidence": 70}, group_key="mtg"),
    ]


def test_full_cross_asset_certification_passes():
    report = certify_phase_5_2(
        cross_asset_items(), CompetitionPolicy(max_selected=3, max_selected_per_group=1)
    )
    assert report.passed
    assert report.status is CertificationStatus.PASSED
    assert len(report.checks) == 9
    assert all(check.status is CertificationStatus.PASSED for check in report.checks)


def test_certification_is_repeatable():
    policy = CompetitionPolicy(max_selected=2)
    first = certify_phase_5_2(cross_asset_items(), policy)
    second = certify_phase_5_2(cross_asset_items(), policy)
    assert first == second


def test_report_is_machine_readable():
    report = certify_phase_5_2(cross_asset_items(), CompetitionPolicy(2))
    payload = json.loads(report.to_json())
    assert payload["phase"] == "5.2"
    assert payload["status"] == "PASSED"
    assert payload["batch_fingerprint"] == report.batch_fingerprint


def test_insufficient_cross_asset_coverage_fails_without_hiding_other_checks():
    report = certify_phase_5_2(
        [
            PortfolioRankingItem("BTC", 90, "P1", {"confidence": 90}, group_key="crypto"),
            PortfolioRankingItem("ETH", 80, "P2", {"confidence": 80}, group_key="crypto"),
        ],
        CompetitionPolicy(1),
    )
    assert not report.passed
    assert report.checks[0].check_id == "CROSS_ASSET_COVERAGE"
    assert report.checks[0].status is CertificationStatus.FAILED
    assert len(report.checks) == 9


def test_batch_validation_failure_becomes_failed_certification_report():
    duplicate = PortfolioRankingItem("BTC", 90, "P1", {"confidence": 90}, group_key="crypto")
    report = certify_phase_5_2([duplicate, duplicate], CompetitionPolicy(1))
    assert report.status is CertificationStatus.FAILED
    assert report.batch_fingerprint is None
    assert report.checks[-1].check_id == "BATCH_EXECUTION"


def test_capacity_check_certifies_zero_selection_boundary():
    report = certify_phase_5_2(cross_asset_items(), CompetitionPolicy(max_selected=0))
    assert report.passed
