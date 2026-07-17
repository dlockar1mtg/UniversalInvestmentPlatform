"""Tests for Phase 4.4.5 forecast certification."""

from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest

from foundation.intelligence.forecasting.validation import (
    CertificationGate,
    CertificationStatus,
    ForecastCertificationEngine,
    ForecastCertificationProfile,
    certification_report_from_dict,
    certification_report_to_dict,
    certification_report_to_json,
    load_certification_report,
    save_certification_report,
)
from foundation.intelligence.forecasting.validation.drift_contracts import (
    DriftMetric,
    DriftRecommendation,
    DriftSeverity,
    DriftType,
    ForecastDriftSignal,
)
from foundation.intelligence.forecasting.validation.learning_contracts import (
    ModelLearningSignal,
    ModelLearningStatus,
)
from foundation.intelligence.forecasting.validation.performance_contracts import (
    ForecastPerformanceMetrics,
    PerformanceGrade,
    PerformanceGrouping,
)


MODEL_KEY = "model:1.0.0"


def performance(
    *,
    score: float = 0.85,
    sample_size: int = 20,
    directional_accuracy: float | None = 0.70,
    coverage_gap: float | None = 0.05,
    eligible: bool = True,
) -> ForecastPerformanceMetrics:
    return ForecastPerformanceMetrics(
        group_key=MODEL_KEY,
        grouping=PerformanceGrouping.MODEL,
        sample_size=sample_size,
        evaluation_start=date(2026, 1, 1),
        evaluation_end=date(2027, 1, 1),
        mae=5.0,
        mse=30.0,
        rmse=30.0**0.5,
        mape=0.05,
        smape=0.05,
        mean_bias=1.0,
        mean_relative_bias=0.01,
        directional_accuracy=directional_accuracy,
        interval_coverage=(
            None if coverage_gap is None else 0.95 + coverage_gap
        ),
        interval_coverage_gap=coverage_gap,
        scenario_hit_rate=0.80,
        score=score,
        grade=PerformanceGrade.GOOD,
        eligible=eligible,
    )


def learning(
    *,
    reputation: float = 0.75,
) -> ModelLearningSignal:
    return ModelLearningSignal(
        model_key=MODEL_KEY,
        as_of_date=date(2027, 1, 1),
        sample_size=20,
        performance_score=0.85,
        prior_reputation=0.70,
        recency_score=1.0,
        stability_score=0.90,
        new_reputation=reputation,
        reputation_change=reputation - 0.70,
        status=ModelLearningStatus.STABLE,
        current_weight=0.50,
        recommended_weight=0.55,
        weight_change=0.05,
    )


def drift(
    *,
    score: float = 0.15,
) -> ForecastDriftSignal:
    return ForecastDriftSignal(
        model_key=MODEL_KEY,
        as_of_date=date(2027, 1, 1),
        baseline_sample_size=20,
        current_sample_size=20,
        baseline_regime="expansion",
        current_regime="expansion",
        metrics=(
            DriftMetric(
                drift_type=DriftType.PERFORMANCE,
                raw_change=score,
                normalized_score=score,
                explanation="Performance drift.",
            ),
        ),
        drift_score=score,
        severity=(
            DriftSeverity.NONE
            if score < 0.15
            else DriftSeverity.LOW
            if score < 0.30
            else DriftSeverity.MODERATE
        ),
        recommendation=(
            DriftRecommendation.NONE
            if score < 0.15
            else DriftRecommendation.MONITOR
        ),
        regime_changed=False,
    )


def profile() -> ForecastCertificationProfile:
    return ForecastCertificationProfile(
        minimum_sample_size=10,
        minimum_performance_score=0.70,
        minimum_directional_accuracy=0.55,
        maximum_interval_coverage_gap=0.15,
        minimum_reputation=0.60,
        maximum_drift_score=0.40,
    )


def certify(
    perf=None,
    learn=None,
    drift_signal=None,
):
    return ForecastCertificationEngine().certify(
        (perf or performance(),),
        (learn or learning(),),
        (drift_signal or drift(),),
        profile=profile(),
        effective_date=date(2027, 1, 1),
    )


def test_profile_requires_positive_sample_size() -> None:
    with pytest.raises(ValueError, match="positive"):
        ForecastCertificationProfile(minimum_sample_size=0)


def test_profile_requires_positive_validity() -> None:
    with pytest.raises(ValueError, match="positive"):
        ForecastCertificationProfile(validity_days=0)


def test_empty_inputs_are_rejected() -> None:
    with pytest.raises(ValueError, match="At least one"):
        ForecastCertificationEngine().certify((), (), ())


def test_model_keys_must_match() -> None:
    bad_learning = replace(learning(), model_key="other:1.0.0")

    with pytest.raises(ValueError, match="must match"):
        ForecastCertificationEngine().certify(
            (performance(),),
            (bad_learning,),
            (drift(),),
        )


def test_healthy_model_is_certified() -> None:
    record = certify().records[0]

    assert record.status is CertificationStatus.CERTIFIED
    assert record.score == pytest.approx(1.0)


def test_high_drift_rejects_model() -> None:
    record = certify(
        drift_signal=drift(score=0.80)
    ).records[0]

    assert record.status is CertificationStatus.REJECTED
    assert record.restrictions


def test_low_sample_size_rejects_model() -> None:
    record = certify(
        perf=performance(sample_size=5)
    ).records[0]

    assert record.status is CertificationStatus.REJECTED


def test_near_threshold_model_is_conditional() -> None:
    record = certify(
        learn=learning(reputation=0.55)
    ).records[0]

    assert record.status is CertificationStatus.CONDITIONAL
    assert any(
        gate.gate is CertificationGate.REPUTATION
        and gate.conditional
        for gate in record.gates
    )


def test_certification_expiration_is_calculated() -> None:
    record = certify().records[0]

    assert record.expires_on == date(2027, 4, 1)


def test_certification_id_is_deterministic() -> None:
    first = certify().records[0]
    second = certify().records[0]

    assert first.certification_id == second.certification_id


def test_all_expected_gates_are_present() -> None:
    record = certify().records[0]

    assert {item.gate for item in record.gates} == set(
        CertificationGate
    )


def test_optional_direction_gate_can_be_disabled() -> None:
    custom = replace(
        profile(),
        require_directional_accuracy=False,
    )
    report = ForecastCertificationEngine().certify(
        (performance(directional_accuracy=None),),
        (learning(),),
        (drift(),),
        profile=custom,
    )

    gate = next(
        item
        for item in report.records[0].gates
        if item.gate is CertificationGate.DIRECTION
    )
    assert gate.passed is True


def test_optional_coverage_gate_can_be_disabled() -> None:
    custom = replace(
        profile(),
        require_interval_coverage=False,
    )
    report = ForecastCertificationEngine().certify(
        (performance(coverage_gap=None),),
        (learning(),),
        (drift(),),
        profile=custom,
    )

    gate = next(
        item
        for item in report.records[0].gates
        if item.gate is CertificationGate.CALIBRATION
    )
    assert gate.passed is True


def test_ineligible_scorecard_rejects_model() -> None:
    record = certify(
        perf=performance(eligible=False)
    ).records[0]

    assert record.status is CertificationStatus.REJECTED


def test_report_is_json_safe() -> None:
    payload = certification_report_to_dict(certify())

    assert len(payload["records"]) == 1


def test_report_json_is_deterministic() -> None:
    report = certify()

    assert certification_report_to_json(
        report
    ) == certification_report_to_json(report)


def test_report_round_trip() -> None:
    report = certify()
    restored = certification_report_from_dict(
        certification_report_to_dict(report)
    )

    assert restored == report


def test_report_save_and_load(tmp_path) -> None:
    report = certify()
    path = tmp_path / "certification.json"

    save_certification_report(report, path)
    restored = load_certification_report(path)

    assert restored == report
