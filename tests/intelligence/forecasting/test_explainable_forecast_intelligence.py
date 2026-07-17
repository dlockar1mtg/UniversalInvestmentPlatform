"""Tests for Phase 4.2.5 explainable forecast intelligence."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json

import pytest

from foundation.intelligence.forecasting.intelligence import (
    CalibrationStrength,
    ConfidenceCalibrationResult,
    ConsensusStrength,
    DriverPolarity,
    EnsembleWeightEntry,
    EnsembleWeightResult,
    ExplainableForecastIntelligenceService,
    ForecastDriverAttributionEngine,
    ForecastEvidenceGraphBuilder,
    ForecastModelEvidence,
    ForecastNarrativeEngine,
    ForecastQualityEngine,
    ForecastRiskFactor,
    HistoricalSimilarityEngine,
    MarketRegime,
    WeightOptimizationStatus,
    explanation_to_dict,
    explanation_to_json,
)
from foundation.intelligence.forecasting.intelligence.consensus_contracts import (
    ForecastConsensusResult,
)
from foundation.intelligence.forecasting.models import (
    ForecastDirection,
    ForecastHorizon,
    ForecastMethod,
    ForecastProvenance,
    UniversalForecast,
)


def forecast() -> UniversalForecast:
    return UniversalForecast(
        forecast_id="forecast-001",
        asset_id="BTC-USD",
        as_of_date=date(2026, 7, 17),
        target_date=date(2027, 7, 17),
        horizon=ForecastHorizon.ONE_YEAR,
        reference_value=100_000.0,
        point_forecast=118_000.0,
        currency="USD",
        provenance=ForecastProvenance(
            model_name="model-a",
            model_version="1.0.0",
            method=ForecastMethod.ENSEMBLE,
            generated_at=datetime(
                2026, 7, 17, 18, 0, tzinfo=timezone.utc
            ),
        ),
        direction=ForecastDirection.UP,
        confidence_score=0.82,
        expected_return=0.18,
    )


def quality_score():
    evidence = ForecastModelEvidence(
        engine_name="model-a",
        engine_version="1.0.0",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        evaluation_date=date(2026, 7, 17),
        sample_size=250,
        accuracy_score=0.88,
        calibration_score=0.86,
        directional_accuracy=0.90,
        stability_score=0.84,
        coverage_score=0.85,
    )
    return ForecastQualityEngine().score(evidence)


def consensus_result() -> ForecastConsensusResult:
    return ForecastConsensusResult(
        asset_id="BTC-USD",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        model_count=3,
        consensus_value=116_500.0,
        consensus_direction=ForecastDirection.UP,
        value_agreement_score=0.91,
        direction_agreement_score=1.0,
        quality_agreement_score=0.88,
        consensus_score=0.93,
        strength=ConsensusStrength.VERY_STRONG,
        dispersion_ratio=0.03,
        confidence_adjustment=0.10,
    )


def calibration_result() -> ConfidenceCalibrationResult:
    return ConfidenceCalibrationResult(
        raw_confidence=0.82,
        calibrated_confidence=0.87,
        adjustment=0.05,
        reliability_score=0.90,
        sample_factor=1.0,
        freshness_factor=1.0,
        regime_match_score=1.0,
        evidence_count=1,
        strength=CalibrationStrength.VERY_STRONG,
        selected_evidence=None,
    )


def weight_result() -> EnsembleWeightResult:
    return EnsembleWeightResult(
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        regime=MarketRegime.BULL,
        status=WeightOptimizationStatus.OPTIMIZED,
        weights=(
            EnsembleWeightEntry(
                engine_name="model-a",
                engine_version="1.0.0",
                raw_score=0.90,
                normalized_weight=0.60,
                constrained_weight=0.60,
                eligible=True,
            ),
            EnsembleWeightEntry(
                engine_name="model-b",
                engine_version="1.0.0",
                raw_score=0.70,
                normalized_weight=0.40,
                constrained_weight=0.40,
                eligible=True,
            ),
        ),
        eligible_model_count=2,
        excluded_model_count=0,
    )


def risks():
    return (
        ForecastRiskFactor(
            name="Elevated volatility",
            severity=0.80,
            description="Price variance remains above its long-run norm.",
        ),
        ForecastRiskFactor(
            name="Liquidity reversal",
            severity=0.45,
            description="Liquidity conditions may weaken.",
            mitigated=True,
        ),
    )


def candidates():
    return (
        (
            "analog-2020",
            "2020 Bull Cycle",
            MarketRegime.BULL,
            "Strong subsequent appreciation.",
            {"momentum": 0.88, "liquidity": 0.82},
        ),
        (
            "analog-2023",
            "2023 Recovery",
            MarketRegime.BULL,
            "Moderate sustained recovery.",
            {"momentum": 0.75, "liquidity": 0.72},
        ),
    )


def test_driver_attribution_normalizes_importance() -> None:
    drivers = ForecastDriverAttributionEngine().attribute(
        (
            ("Momentum", 0.12, "technical"),
            ("Liquidity", 0.08, "macro"),
            ("Valuation", -0.05, "fundamental"),
        )
    )

    assert sum(item.importance for item in drivers) == pytest.approx(1.0)
    assert drivers[0].name == "Momentum"
    assert drivers[0].polarity is DriverPolarity.POSITIVE
    assert drivers[-1].polarity is DriverPolarity.NEGATIVE


def test_zero_driver_contributions_receive_equal_importance() -> None:
    drivers = ForecastDriverAttributionEngine().attribute(
        (
            ("A", 0.0, "general"),
            ("B", 0.0, "general"),
        )
    )

    assert all(
        item.importance == pytest.approx(0.50)
        for item in drivers
    )
    assert all(
        item.polarity is DriverPolarity.NEUTRAL
        for item in drivers
    )


def test_risks_are_ranked_unmitigated_first() -> None:
    ranked = ForecastDriverAttributionEngine.rank_risks(risks())

    assert ranked[0].name == "Elevated volatility"
    assert ranked[-1].mitigated is True


def test_historical_similarity_ranks_closest_analog() -> None:
    analogs = HistoricalSimilarityEngine().rank(
        current_features={"momentum": 0.90, "liquidity": 0.85},
        candidates=candidates(),
    )

    assert analogs[0].label == "2020 Bull Cycle"
    assert analogs[0].similarity_score > analogs[1].similarity_score


def test_historical_similarity_requires_positive_limit() -> None:
    with pytest.raises(ValueError, match="limit must be positive"):
        HistoricalSimilarityEngine().rank(
            current_features={"momentum": 0.90},
            candidates=candidates(),
            limit=0,
        )


def test_historical_similarity_ignores_no_common_features() -> None:
    analogs = HistoricalSimilarityEngine().rank(
        current_features={"momentum": 0.90},
        candidates=(
            (
                "x",
                "No Match",
                MarketRegime.UNKNOWN,
                "Unknown.",
                {"liquidity": 0.50},
            ),
        ),
    )

    assert analogs == ()


def test_evidence_graph_contains_core_nodes() -> None:
    graph = ForecastEvidenceGraphBuilder().build(
        forecast_id="forecast-001",
        quality_score=0.88,
        consensus_score=0.93,
        calibration_score=0.87,
        ensemble_weights={"model-a 1.0.0": 0.60, "model-b 1.0.0": 0.40},
        drivers=ForecastDriverAttributionEngine().attribute(
            (("Momentum", 0.12, "technical"),)
        ),
        risks=risks(),
        analogs=HistoricalSimilarityEngine().rank(
            current_features={"momentum": 0.90, "liquidity": 0.85},
            candidates=candidates(),
        ),
    )

    node_types = {node.node_type.value for node in graph.nodes}
    assert "forecast" in node_types
    assert "quality" in node_types
    assert "consensus" in node_types
    assert "calibration" in node_types
    assert len(graph.edges) > 3


def test_evidence_graph_rejects_unknown_edge_nodes() -> None:
    from foundation.intelligence.forecasting.intelligence import (
        EvidenceEdge,
        EvidenceNode,
        EvidenceNodeType,
        ForecastEvidenceGraph,
    )

    with pytest.raises(ValueError, match="known node ids"):
        ForecastEvidenceGraph(
            nodes=(
                EvidenceNode(
                    node_id="known",
                    node_type=EvidenceNodeType.FORECAST,
                    label="Known",
                ),
            ),
            edges=(
                EvidenceEdge(
                    source_id="missing",
                    target_id="known",
                    relationship="supports",
                ),
            ),
        )


def test_narrative_is_deterministic() -> None:
    engine = ForecastNarrativeEngine()
    kwargs = dict(
        asset_id="BTC-USD",
        direction=ForecastDirection.UP,
        quality_score=0.88,
        consensus_score=0.93,
        calibrated_confidence=0.87,
        drivers=ForecastDriverAttributionEngine().attribute(
            (
                ("Momentum", 0.12, "technical"),
                ("Valuation", -0.05, "fundamental"),
            )
        ),
        risks=risks(),
        analogs=HistoricalSimilarityEngine().rank(
            current_features={"momentum": 0.90, "liquidity": 0.85},
            candidates=candidates(),
        ),
        leading_model="model-a 1.0.0",
    )

    assert engine.generate(**kwargs) == engine.generate(**kwargs)


def test_narrative_mentions_primary_driver_and_risk() -> None:
    narrative = ForecastNarrativeEngine().generate(
        asset_id="BTC-USD",
        direction=ForecastDirection.UP,
        quality_score=0.88,
        consensus_score=0.93,
        calibrated_confidence=0.87,
        drivers=ForecastDriverAttributionEngine().attribute(
            (
                ("Momentum", 0.12, "technical"),
                ("Valuation", -0.05, "fundamental"),
            )
        ),
        risks=risks(),
        analogs=(),
        leading_model="model-a 1.0.0",
    )

    assert "Momentum" in narrative
    assert "Valuation" in narrative
    assert "Elevated volatility" in narrative


def test_service_builds_complete_explanation() -> None:
    explanation = ExplainableForecastIntelligenceService().explain(
        forecast(),
        asset_class="crypto",
        quality_score=quality_score(),
        consensus_result=consensus_result(),
        calibration_result=calibration_result(),
        weight_result=weight_result(),
        raw_driver_contributions=(
            ("Momentum", 0.12, "technical"),
            ("Liquidity", 0.08, "macro"),
            ("Valuation", -0.05, "fundamental"),
        ),
        risks=risks(),
        current_features={"momentum": 0.90, "liquidity": 0.85},
        historical_candidates=candidates(),
    )

    assert explanation.asset_id == "BTC-USD"
    assert explanation.drivers[0].name == "Momentum"
    assert explanation.historical_analogs[0].label == "2020 Bull Cycle"
    assert explanation.ensemble_weights["model-a 1.0.0"] == 0.60
    assert explanation.narrative


def test_service_rejects_mismatched_quality_model() -> None:
    other_evidence = ForecastModelEvidence(
        engine_name="other",
        engine_version="1.0.0",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        evaluation_date=date(2026, 7, 17),
        sample_size=250,
        accuracy_score=0.80,
        calibration_score=0.80,
        directional_accuracy=0.80,
        stability_score=0.80,
        coverage_score=0.80,
    )

    with pytest.raises(ValueError, match="does not match forecast"):
        ExplainableForecastIntelligenceService().explain(
            forecast(),
            asset_class="crypto",
            quality_score=ForecastQualityEngine().score(other_evidence),
            consensus_result=consensus_result(),
            calibration_result=calibration_result(),
            weight_result=weight_result(),
            raw_driver_contributions=(),
            risks=(),
            current_features={},
            historical_candidates=(),
        )


def test_service_rejects_mismatched_consensus_asset() -> None:
    bad = ForecastConsensusResult(
        asset_id="ETH-USD",
        asset_class="crypto",
        horizon=ForecastHorizon.ONE_YEAR,
        model_count=2,
        consensus_value=100.0,
        consensus_direction=ForecastDirection.UP,
        value_agreement_score=0.8,
        direction_agreement_score=1.0,
        quality_agreement_score=0.8,
        consensus_score=0.85,
        strength=ConsensusStrength.STRONG,
        dispersion_ratio=0.02,
        confidence_adjustment=0.05,
    )

    with pytest.raises(ValueError, match="asset_id"):
        ExplainableForecastIntelligenceService().explain(
            forecast(),
            asset_class="crypto",
            quality_score=quality_score(),
            consensus_result=bad,
            calibration_result=calibration_result(),
            weight_result=weight_result(),
            raw_driver_contributions=(),
            risks=(),
            current_features={},
            historical_candidates=(),
        )


def test_explanation_to_dict_is_json_safe() -> None:
    explanation = ExplainableForecastIntelligenceService().explain(
        forecast(),
        asset_class="crypto",
        quality_score=quality_score(),
        consensus_result=consensus_result(),
        calibration_result=calibration_result(),
        weight_result=weight_result(),
        raw_driver_contributions=(("Momentum", 0.12, "technical"),),
        risks=risks(),
        current_features={"momentum": 0.90, "liquidity": 0.85},
        historical_candidates=candidates(),
    )

    payload = explanation_to_dict(explanation)
    encoded = json.dumps(payload)

    assert payload["asset_id"] == "BTC-USD"
    assert '"direction": "up"' in encoded


def test_explanation_json_is_deterministic() -> None:
    explanation = ExplainableForecastIntelligenceService().explain(
        forecast(),
        asset_class="crypto",
        quality_score=quality_score(),
        consensus_result=consensus_result(),
        calibration_result=calibration_result(),
        weight_result=weight_result(),
        raw_driver_contributions=(("Momentum", 0.12, "technical"),),
        risks=risks(),
        current_features={"momentum": 0.90, "liquidity": 0.85},
        historical_candidates=candidates(),
    )

    assert explanation_to_json(explanation) == explanation_to_json(explanation)


def test_explanation_weights_must_sum_to_one() -> None:
    from foundation.intelligence.forecasting.intelligence import (
        ForecastEvidenceGraph,
        ForecastExplanation,
    )

    with pytest.raises(ValueError, match="must sum to 1.0"):
        ForecastExplanation(
            forecast_id="x",
            asset_id="BTC-USD",
            asset_class="crypto",
            horizon=ForecastHorizon.ONE_YEAR,
            direction=ForecastDirection.UP,
            point_forecast=100.0,
            confidence=0.8,
            quality_score=0.8,
            consensus_score=0.8,
            calibrated_confidence=0.8,
            ensemble_weights={"a": 0.7, "b": 0.2},
            drivers=(),
            risks=(),
            historical_analogs=(),
            evidence_graph=ForecastEvidenceGraph(nodes=(), edges=()),
            narrative="Narrative.",
        )
