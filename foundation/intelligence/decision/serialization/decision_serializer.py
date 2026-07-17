"""Stable serialization of orchestrated investment decisions."""

from __future__ import annotations

import json
from typing import Any, Mapping

from ..orchestration.orchestration_result import (
    DecisionOrchestrationResult,
)
from .serialization_profile import DecisionSerializationProfile
from .serialization_utils import to_primitive


class UniversalDecisionSerializer:
    """Serialize complete decisions into stable schema-versioned records."""

    RECORD_TYPE = "universal_investment_decision"

    def serialize(
        self,
        result: DecisionOrchestrationResult,
        *,
        profile: DecisionSerializationProfile | None = None,
    ) -> dict[str, Any]:
        """Return a complete JSON-safe decision record."""

        active_profile = profile or DecisionSerializationProfile()

        payload: dict[str, Any] = {
            "record_type": self.RECORD_TYPE,
            "schema_version": active_profile.schema_version,
            "serialization_version": (
                active_profile.serialization_version
            ),
            "engine_version": result.engine_version,
            "decision": to_primitive(result.decision_result),
        }

        if active_profile.include_intermediate_artifacts:
            payload["artifacts"] = {
                "eligibility": to_primitive(
                    result.eligibility_result
                ),
                "classification": to_primitive(
                    result.classification_result
                ),
                "confidence": to_primitive(
                    result.confidence_result
                ),
                "constraints": to_primitive(
                    result.constraint_result
                ),
                "allocation": to_primitive(
                    result.allocation_result
                ),
            }

        if active_profile.include_explanation:
            explanation = to_primitive(result.explanation)

            if not active_profile.include_audit_facts:
                explanation["audit_facts"] = {}

            payload["explanation"] = explanation

        if not active_profile.include_source_metadata:
            decision = payload["decision"]
            metadata = dict(decision.get("metadata", {}))
            metadata.pop("source_metadata", None)
            decision["metadata"] = metadata

        return payload

    def to_json(
        self,
        result: DecisionOrchestrationResult,
        *,
        profile: DecisionSerializationProfile | None = None,
    ) -> str:
        """Serialize a decision into deterministic JSON text."""

        active_profile = profile or DecisionSerializationProfile()
        payload = self.serialize(result, profile=active_profile)

        return json.dumps(
            payload,
            indent=active_profile.json_indent,
            sort_keys=active_profile.sort_keys,
            ensure_ascii=False,
            separators=(
                (",", ":")
                if active_profile.json_indent is None
                else None
            ),
        )

    def audit_record(
        self,
        result: DecisionOrchestrationResult,
        *,
        profile: DecisionSerializationProfile | None = None,
    ) -> dict[str, Any]:
        """Create an immutable reconstruction-oriented audit record."""

        active_profile = profile or DecisionSerializationProfile()

        return {
            "record_type": "universal_decision_audit",
            "schema_version": active_profile.schema_version,
            "serialization_version": (
                active_profile.serialization_version
            ),
            "decision_id": result.decision_result.decision_id,
            "asset_id": result.decision_result.asset_id,
            "generated_at": (
                result.decision_result.generated_at.isoformat()
            ),
            "engine_version": result.engine_version,
            "payload": self.serialize(
                result,
                profile=DecisionSerializationProfile(
                    profile_id=active_profile.profile_id,
                    schema_version=active_profile.schema_version,
                    serialization_version=(
                        active_profile.serialization_version
                    ),
                    include_intermediate_artifacts=True,
                    include_explanation=True,
                    include_audit_facts=True,
                    include_source_metadata=True,
                    sort_keys=active_profile.sort_keys,
                    json_indent=active_profile.json_indent,
                ),
            ),
        }

    def summary_record(
        self,
        result: DecisionOrchestrationResult,
    ) -> Mapping[str, Any]:
        """Create a flat summary suitable for ranking and CSV export."""

        decision = result.decision_result
        allocation = result.allocation_result
        confidence = result.confidence_result
        constraints = result.constraint_result

        return {
            "decision_id": decision.decision_id,
            "asset_id": decision.asset_id,
            "asset_class": decision.asset_class,
            "action": decision.action.value,
            "status": decision.status.value,
            "eligibility": decision.eligibility.value,
            "decision_score": decision.score.final_score,
            "confidence": decision.confidence,
            "confidence_band": confidence.confidence_band.value,
            "maximum_allocation": str(decision.maximum_allocation),
            "recommended_allocation": str(
                decision.recommended_allocation
            ),
            "allocation_percentage": allocation.allocation_percentage,
            "constraint_status": constraints.status.value,
            "binding_constraint": constraints.binding_constraint,
            "policy_id": decision.policy_id,
            "policy_version": decision.policy_version,
            "scoring_version": decision.score.scoring_version,
            "engine_version": result.engine_version,
            "generated_at": decision.generated_at.isoformat(),
            "expires_at": (
                decision.expires_at.isoformat()
                if decision.expires_at is not None
                else None
            ),
            "headline": result.explanation.headline,
        }
