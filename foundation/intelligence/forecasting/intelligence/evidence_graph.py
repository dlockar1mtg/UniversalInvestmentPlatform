"""Forecast evidence graph construction."""

from __future__ import annotations

from .explainability_contracts import (
    EvidenceEdge,
    EvidenceNode,
    EvidenceNodeType,
    ForecastDriver,
    ForecastEvidenceGraph,
    ForecastRiskFactor,
    HistoricalAnalog,
)


class ForecastEvidenceGraphBuilder:
    """Build a deterministic evidence graph for a forecast explanation."""

    def build(
        self,
        *,
        forecast_id: str,
        quality_score: float,
        consensus_score: float,
        calibration_score: float,
        ensemble_weights: dict[str, float],
        drivers: tuple[ForecastDriver, ...],
        risks: tuple[ForecastRiskFactor, ...],
        analogs: tuple[HistoricalAnalog, ...],
    ) -> ForecastEvidenceGraph:
        root_id = f"forecast:{forecast_id}"
        nodes = [
            EvidenceNode(
                node_id=root_id,
                node_type=EvidenceNodeType.FORECAST,
                label="Forecast",
            ),
            EvidenceNode(
                node_id="quality",
                node_type=EvidenceNodeType.QUALITY,
                label="Historical model quality",
                score=quality_score,
            ),
            EvidenceNode(
                node_id="consensus",
                node_type=EvidenceNodeType.CONSENSUS,
                label="Cross-model consensus",
                score=consensus_score,
            ),
            EvidenceNode(
                node_id="calibration",
                node_type=EvidenceNodeType.CALIBRATION,
                label="Calibrated confidence",
                score=calibration_score,
            ),
        ]
        edges = [
            EvidenceEdge("quality", root_id, "supports"),
            EvidenceEdge("consensus", root_id, "supports"),
            EvidenceEdge("calibration", root_id, "supports"),
        ]

        for index, (model, weight) in enumerate(
            sorted(ensemble_weights.items())
        ):
            node_id = f"weight:{index}"
            nodes.append(
                EvidenceNode(
                    node_id=node_id,
                    node_type=EvidenceNodeType.ENSEMBLE_WEIGHT,
                    label=model,
                    score=weight,
                )
            )
            edges.append(
                EvidenceEdge(node_id, root_id, "contributes", weight)
            )

        for index, driver in enumerate(drivers):
            node_id = f"driver:{index}"
            nodes.append(
                EvidenceNode(
                    node_id=node_id,
                    node_type=EvidenceNodeType.DRIVER,
                    label=driver.name,
                    score=driver.importance,
                    metadata={
                        "contribution": driver.contribution,
                        "polarity": driver.polarity.value,
                    },
                )
            )
            edges.append(
                EvidenceEdge(
                    node_id,
                    root_id,
                    "influences",
                    driver.importance,
                )
            )

        for index, risk in enumerate(risks):
            node_id = f"risk:{index}"
            nodes.append(
                EvidenceNode(
                    node_id=node_id,
                    node_type=EvidenceNodeType.RISK,
                    label=risk.name,
                    score=risk.severity,
                    metadata={"mitigated": risk.mitigated},
                )
            )
            edges.append(
                EvidenceEdge(
                    node_id,
                    root_id,
                    "threatens",
                    risk.severity,
                )
            )

        for index, analog in enumerate(analogs):
            node_id = f"analog:{index}"
            nodes.append(
                EvidenceNode(
                    node_id=node_id,
                    node_type=EvidenceNodeType.HISTORICAL_ANALOG,
                    label=analog.label,
                    score=analog.similarity_score,
                    metadata={"regime": analog.regime.value},
                )
            )
            edges.append(
                EvidenceEdge(
                    node_id,
                    root_id,
                    "resembles",
                    analog.similarity_score,
                )
            )

        return ForecastEvidenceGraph(
            nodes=tuple(nodes),
            edges=tuple(edges),
        )
