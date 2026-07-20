from datetime import datetime, timedelta, timezone
from decimal import Decimal

from foundation.intelligence.monitoring import (
    DriftCategory, DriftDetectionStatus, DriftDirection, DriftThreshold,
    MonitoringBaseline, MonitoringObservation, MonitoringPolicyBundle,
    MonitoringRunRequest, MonitoringWindow, TriggerSeverity, detect_drift,
)


NOW = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)


def make_request(observations, thresholds, *, metrics=None, minimum=1):
    baseline = MonitoringBaseline(
        "baseline-1", "run-1", "a" * 64, NOW,
        metrics or {"score": "80", "price": "100", "liquidity": "90"},
    )
    window = MonitoringWindow(
        "window-1", NOW, NOW + timedelta(hours=4), tuple(observations),
    )
    policy = MonitoringPolicyBundle(
        "policy-1", tuple(thresholds), minimum_observations=minimum,
    )
    return MonitoringRunRequest(
        "monitor-1", NOW + timedelta(hours=4), baseline, window, policy,
    )


def observation(identifier, hour, values, opportunity="opp-1"):
    return MonitoringObservation(
        identifier, NOW + timedelta(hours=hour), values,
        opportunity_id=opportunity,
    )


def test_latest_observation_and_inclusive_boundaries_classify_severity():
    request = make_request(
        (
            observation("older", 1, {"score": "83"}),
            observation("latest", 2, {"score": "90"}),
        ),
        (DriftThreshold(DriftCategory.SCORE, "score", 2, 5, 10),),
    )
    result = detect_drift(request)
    assert result.status is DriftDetectionStatus.DRIFT_DETECTED
    assert result.signals[0].observed_value == Decimal("90")
    assert result.signals[0].delta == Decimal("10")
    assert result.signals[0].severity is TriggerSeverity.CRITICAL


def test_directional_threshold_ignores_opposite_movement():
    request = make_request(
        (observation("obs", 1, {"liquidity": "95", "price": "92"}),),
        (
            DriftThreshold(
                DriftCategory.LIQUIDITY, "liquidity", 2, 5, 10,
                DriftDirection.DECREASE,
            ),
            DriftThreshold(
                DriftCategory.MARKET, "price", 2, 5, 10,
                DriftDirection.DECREASE,
            ),
        ),
    )
    result = detect_drift(request)
    assert tuple(item.metric_name for item in result.signals) == ("price",)
    assert result.signals[0].severity is TriggerSeverity.MATERIAL
    assert result.evaluated_comparisons == 2


def test_relative_drift_and_zero_baseline_are_deterministic():
    request = make_request(
        (observation("obs", 1, {"score": "75", "new_metric": "5"}),),
        (
            DriftThreshold(DriftCategory.SCORE, "score", ".05", ".10", ".20", relative=True),
            DriftThreshold(DriftCategory.MARKET, "new_metric", ".25", ".50", "1", relative=True),
        ),
        metrics={"score": "100", "new_metric": "0"},
    )
    result = detect_drift(request)
    by_metric = {item.metric_name: item for item in result.signals}
    assert by_metric["score"].severity is TriggerSeverity.CRITICAL
    assert by_metric["new_metric"].severity is TriggerSeverity.CRITICAL
    assert by_metric["new_metric"].delta == Decimal("5")


def test_missing_baseline_and_observed_metrics_are_preserved_as_evidence():
    request = make_request(
        (observation("obs", 1, {"price": "101"}),),
        (
            DriftThreshold(DriftCategory.SCORE, "score", 2, 5, 10),
            DriftThreshold(DriftCategory.CONFIDENCE, "confidence", 2, 5, 10),
        ),
    )
    result = detect_drift(request)
    assert result.status is DriftDetectionStatus.NO_DRIFT
    assert {item.reason_code for item in result.missing_metrics} == {
        "BASELINE_METRIC_MISSING", "OBSERVED_METRIC_MISSING",
    }
    assert result.evaluated_comparisons == 0


def test_minimum_observation_policy_returns_insufficient_data_without_signals():
    request = make_request(
        (observation("obs", 1, {"score": "60"}),),
        (DriftThreshold(DriftCategory.SCORE, "score", 2, 5, 10),),
        minimum=2,
    )
    result = detect_drift(request)
    assert result.status is DriftDetectionStatus.INSUFFICIENT_DATA
    assert result.signals == () and result.evaluated_comparisons == 0


def test_detection_is_input_order_invariant_with_stable_fingerprint():
    observations = (
        observation("b", 2, {"score": "88", "price": "104"}),
        observation("a", 1, {"score": "84", "price": "102"}),
    )
    thresholds = (
        DriftThreshold(DriftCategory.SCORE, "score", 2, 5, 10),
        DriftThreshold(DriftCategory.MARKET, "price", 2, 5, 10),
    )
    first = detect_drift(make_request(observations, thresholds))
    second = detect_drift(make_request(reversed(observations), reversed(thresholds)))
    assert first == second
    assert len(first.detection_fingerprint) == 64
