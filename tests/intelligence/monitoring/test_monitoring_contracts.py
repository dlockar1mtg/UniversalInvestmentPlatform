from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.monitoring import (
    DriftCategory, DriftDirection, DriftSignal, DriftThreshold,
    MonitoringBaseline, MonitoringLifecycleStatus, MonitoringObservation,
    MonitoringPolicyBundle, MonitoringRunRequest, MonitoringRunResult,
    MonitoringWindow, ReoptimizationDisposition, ReoptimizationTrigger,
    TriggerSeverity,
)


NOW = datetime(2026, 7, 18, 12, tzinfo=timezone.utc)


def threshold(metric="priority_score", category=DriftCategory.SCORE, watch="2"):
    return DriftThreshold(category, metric, watch, "5", "10")


def baseline():
    return MonitoringBaseline(
        "baseline-1", "run-1", "a" * 64, NOW,
        {"priority_score": "85", "market_price": "100"},
        metadata={"source": {"certified": True}},
    )


def observation(identifier="obs-1", at=None):
    return MonitoringObservation(
        identifier, at or NOW + timedelta(hours=1),
        {"priority_score": "82", "market_price": "103"},
        opportunity_id="opp-1",
    )


def policy(*thresholds):
    return MonitoringPolicyBundle(
        "policy-1", tuple(thresholds or (threshold(),)),
        cooldown=timedelta(hours=12), stale_after=timedelta(days=2),
        hysteresis_rate="0.10", trigger_policy={"critical": {"action": "ESCALATE"}},
    )


def test_baseline_and_observation_normalize_metrics_and_freeze_nested_evidence():
    base = baseline()
    item = observation()
    assert base.metrics["priority_score"] == Decimal("85")
    assert item.metrics["market_price"] == Decimal("103")
    with pytest.raises(TypeError):
        base.metrics["priority_score"] = Decimal("1")
    with pytest.raises(TypeError):
        base.metadata["source"]["certified"] = False


def test_monitoring_window_calculates_duration_and_enforces_bounds_and_uniqueness():
    item = observation()
    window = MonitoringWindow(
        "window-1", NOW, NOW + timedelta(hours=2), (item,)
    )
    assert window.duration == timedelta(hours=2)
    with pytest.raises(ValueError, match="unique"):
        MonitoringWindow("duplicate", NOW, NOW + timedelta(hours=2), (item, item))
    with pytest.raises(ValueError, match="within"):
        MonitoringWindow("outside", NOW, NOW + timedelta(minutes=30), (item,))


def test_thresholds_enforce_order_and_preserve_direction():
    value = DriftThreshold(
        DriftCategory.LIQUIDITY, "liquidity_score", 2, 5, 8,
        DriftDirection.DECREASE, relative=True,
    )
    assert value.key == ("LIQUIDITY", "liquidity_score")
    assert value.direction is DriftDirection.DECREASE and value.relative
    with pytest.raises(ValueError, match="watch <= material <= critical"):
        DriftThreshold(DriftCategory.SCORE, "score", 6, 5, 10)


def test_policy_fingerprint_is_threshold_order_invariant_and_change_sensitive():
    score = threshold()
    market = threshold("market_price", DriftCategory.MARKET, "3")
    first = policy(score, market)
    reversed_policy = policy(market, score)
    changed = policy(threshold(watch="3"), market)
    assert first.fingerprint == reversed_policy.fingerprint
    assert first.fingerprint != changed.fingerprint
    assert len(first.fingerprint) == 64


def test_request_preserves_certified_source_lineage_and_temporal_boundary():
    base = baseline()
    window = MonitoringWindow(
        "window-1", NOW, NOW + timedelta(hours=2), (observation(),)
    )
    request = MonitoringRunRequest("monitor-1", NOW + timedelta(hours=2), base, window, policy())
    assert request.baseline.source_run_id == "run-1"
    assert request.policy.fingerprint == policy().fingerprint
    earlier = MonitoringWindow(
        "earlier", NOW - timedelta(hours=1), NOW + timedelta(hours=1),
        (observation(at=NOW),),
    )
    with pytest.raises(ValueError, match="before the baseline"):
        MonitoringRunRequest("invalid", NOW, base, earlier, policy())


def test_signal_trigger_and_completed_result_require_auditable_identity():
    signal = DriftSignal(
        DriftCategory.SCORE, "priority_score", 85, 74, -11,
        TriggerSeverity.CRITICAL, "opp-1", "SCORE_CRITICAL",
    )
    trigger = ReoptimizationTrigger(
        ReoptimizationDisposition.REOPTIMIZE, TriggerSeverity.CRITICAL,
        ("SCORE_CRITICAL",), NOW + timedelta(hours=12), "run-1",
    )
    result = MonitoringRunResult(
        "monitor-1", MonitoringLifecycleStatus.COMPLETED_WITH_ALERTS,
        policy().fingerprint, (signal,), trigger, "b" * 64,
    )
    assert result.signals[0].delta == Decimal("-11")
    assert result.trigger.source_run_id == "run-1"
    with pytest.raises(ValueError, match="output_fingerprint"):
        MonitoringRunResult(
            "monitor-1", MonitoringLifecycleStatus.COMPLETED,
            policy().fingerprint, (), trigger,
        )
