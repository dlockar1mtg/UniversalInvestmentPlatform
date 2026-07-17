"""Reconstruction of serialized universal decisions."""

from __future__ import annotations

import json
from typing import Any, Mapping

from ..contracts.decision_action import DecisionAction
from ..contracts.decision_evidence import DecisionEvidence
from ..contracts.decision_result import DecisionResult
from ..contracts.decision_score import DecisionScore
from ..contracts.decision_status import (
    DecisionStatus,
    EligibilityStatus,
)
from .serialization_errors import DecisionDeserializationError
from .serialization_utils import (
    parse_datetime,
    parse_decimal,
    require_mapping,
    require_sequence,
    require_string,
)


class UniversalDecisionDeserializer:
    """Reconstruct stable DecisionResult objects from serialized data."""

    SUPPORTED_SCHEMA_VERSIONS = {"1.0"}

    def from_json(self, raw_json: str) -> DecisionResult:
        """Deserialize a JSON string into a DecisionResult."""

        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            raise DecisionDeserializationError(
                "Decision JSON is invalid."
            ) from exc

        return self.deserialize(payload)

    def deserialize(
        self,
        payload: Mapping[str, Any],
    ) -> DecisionResult:
        """Reconstruct the final DecisionResult from a schema record."""

        record = require_mapping(
            payload,
            field_name="payload",
        )

        schema_version = require_string(
            record.get("schema_version"),
            field_name="schema_version",
        )

        if schema_version not in self.SUPPORTED_SCHEMA_VERSIONS:
            raise DecisionDeserializationError(
                f"Unsupported schema_version {schema_version!r}."
            )

        if record.get("record_type") != (
            "universal_investment_decision"
        ):
            raise DecisionDeserializationError(
                "record_type must be "
                "'universal_investment_decision'."
            )

        decision = require_mapping(
            record.get("decision"),
            field_name="decision",
        )

        score_payload = require_mapping(
            decision.get("score"),
            field_name="decision.score",
        )

        score = DecisionScore(
            base_score=float(score_payload["base_score"]),
            penalty_score=float(score_payload["penalty_score"]),
            final_score=float(score_payload["final_score"]),
            component_scores=dict(
                score_payload.get("component_scores", {})
            ),
            penalty_components=dict(
                score_payload.get("penalty_components", {})
            ),
            scoring_version=require_string(
                score_payload.get("scoring_version"),
                field_name="decision.score.scoring_version",
            ),
        )

        evidence = tuple(
            self._deserialize_evidence(item)
            for item in require_sequence(
                decision.get("evidence", []),
                field_name="decision.evidence",
            )
        )

        expires_raw = decision.get("expires_at")
        expires_at = (
            parse_datetime(
                expires_raw,
                field_name="decision.expires_at",
            )
            if expires_raw is not None
            else None
        )

        try:
            action = DecisionAction(decision["action"])
            status = DecisionStatus(decision["status"])
            eligibility = EligibilityStatus(
                decision["eligibility"]
            )
        except (KeyError, ValueError) as exc:
            raise DecisionDeserializationError(
                "Serialized decision contains an invalid enum value."
            ) from exc

        try:
            return DecisionResult(
                decision_id=require_string(
                    decision.get("decision_id"),
                    field_name="decision.decision_id",
                ),
                asset_id=require_string(
                    decision.get("asset_id"),
                    field_name="decision.asset_id",
                ),
                asset_class=require_string(
                    decision.get("asset_class"),
                    field_name="decision.asset_class",
                ),
                action=action,
                status=status,
                eligibility=eligibility,
                score=score,
                confidence=float(decision["confidence"]),
                maximum_allocation=parse_decimal(
                    decision.get("maximum_allocation"),
                    field_name="decision.maximum_allocation",
                ),
                recommended_allocation=parse_decimal(
                    decision.get("recommended_allocation"),
                    field_name="decision.recommended_allocation",
                ),
                reasons=tuple(decision.get("reasons", [])),
                evidence=evidence,
                policy_violations=tuple(
                    decision.get("policy_violations", [])
                ),
                policy_id=require_string(
                    decision.get("policy_id"),
                    field_name="decision.policy_id",
                ),
                policy_version=require_string(
                    decision.get("policy_version"),
                    field_name="decision.policy_version",
                ),
                generated_at=parse_datetime(
                    decision.get("generated_at"),
                    field_name="decision.generated_at",
                ),
                expires_at=expires_at,
                metadata=dict(decision.get("metadata", {})),
            )
        except Exception as exc:
            if isinstance(exc, DecisionDeserializationError):
                raise

            raise DecisionDeserializationError(
                "Serialized decision could not be reconstructed."
            ) from exc

    @staticmethod
    def _deserialize_evidence(
        payload: Any,
    ) -> DecisionEvidence:
        evidence = require_mapping(
            payload,
            field_name="evidence item",
        )

        return DecisionEvidence(
            evidence_id=require_string(
                evidence.get("evidence_id"),
                field_name="evidence.evidence_id",
            ),
            category=require_string(
                evidence.get("category"),
                field_name="evidence.category",
            ),
            source=require_string(
                evidence.get("source"),
                field_name="evidence.source",
            ),
            description=require_string(
                evidence.get("description"),
                field_name="evidence.description",
            ),
            value=evidence.get("value"),
            weight=float(evidence.get("weight", 1.0)),
            observed_at=parse_datetime(
                evidence.get("observed_at"),
                field_name="evidence.observed_at",
            ),
            metadata=dict(evidence.get("metadata", {})),
        )
