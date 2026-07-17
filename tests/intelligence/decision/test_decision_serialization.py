"""Tests for universal decision serialization and audit exports."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from foundation.intelligence.decision import (
    DecisionAction,
    DecisionContext,
    DecisionDeserializationError,
    DecisionEvidence,
    DecisionExportError,
    DecisionInput,
    DecisionSerializationProfile,
    SerializationConfigurationError,
    UniversalDecisionDeserializer,
    UniversalDecisionExporter,
    UniversalDecisionOrchestrator,
    UniversalDecisionSerializer,
)


FIXED_TIME = datetime(
    2026,
    7,
    17,
    21,
    0,
    0,
    tzinfo=timezone.utc,
)


def build_input(
    *,
    asset_id: str = "ETF:VOO",
) -> DecisionInput:
    return DecisionInput(
        asset_id=asset_id,
        asset_class="etf",
        time_horizon="3_year",
        context=DecisionContext(
            portfolio_id="PORTFOLIO-001",
            as_of=FIXED_TIME,
            portfolio_value=Decimal("100000"),
            available_capital=Decimal("3000"),
            current_position_value=Decimal("0"),
            current_asset_weight=0.0,
            current_asset_class_weight=0.20,
        ),
        forecast_strength=88.0,
        forecast_confidence=86.0,
        historical_reliability=82.0,
        risk_adjusted_opportunity=84.0,
        market_regime_alignment=76.0,
        diversification_fit=80.0,
        liquidity_quality=95.0,
        valuation_attractiveness=79.0,
        data_quality=96.0,
        evidence=(
            DecisionEvidence(
                evidence_id="EVIDENCE-001",
                category="forecast",
                source="forecast_engine",
                description="Serialization evidence.",
                value=12.5,
                weight=0.95,
                observed_at=FIXED_TIME,
                metadata={"model": "universal"},
            ),
        ),
        metadata={
            "source_system": "test",
            "minimum_transaction_amount": "1.00",
        },
    )


def build_result():
    return UniversalDecisionOrchestrator().evaluate(
        build_input(),
        generated_at=FIXED_TIME,
        decision_id="DECISION-SERIALIZATION-001",
    )


def test_serializer_produces_schema_record() -> None:
    payload = UniversalDecisionSerializer().serialize(
        build_result()
    )

    assert payload["record_type"] == (
        "universal_investment_decision"
    )
    assert payload["schema_version"] == "1.0"
    assert payload["decision"]["decision_id"] == (
        "DECISION-SERIALIZATION-001"
    )
    assert payload["decision"]["action"] in {
        "buy",
        "strong_buy",
    }


def test_decimals_are_serialized_as_strings() -> None:
    payload = UniversalDecisionSerializer().serialize(
        build_result()
    )

    assert isinstance(
        payload["decision"]["maximum_allocation"],
        str,
    )
    assert isinstance(
        payload["decision"]["recommended_allocation"],
        str,
    )


def test_timestamps_are_iso_formatted() -> None:
    payload = UniversalDecisionSerializer().serialize(
        build_result()
    )

    assert payload["decision"]["generated_at"] == (
        FIXED_TIME.isoformat()
    )


def test_json_output_is_deterministic() -> None:
    serializer = UniversalDecisionSerializer()
    result = build_result()

    first = serializer.to_json(result)
    second = serializer.to_json(result)

    assert first == second


def test_compact_json_profile_is_supported() -> None:
    raw = UniversalDecisionSerializer().to_json(
        build_result(),
        profile=DecisionSerializationProfile(
            json_indent=None
        ),
    )

    assert "\n" not in raw
    assert json.loads(raw)["schema_version"] == "1.0"


def test_intermediate_artifacts_can_be_omitted() -> None:
    payload = UniversalDecisionSerializer().serialize(
        build_result(),
        profile=DecisionSerializationProfile(
            include_intermediate_artifacts=False
        ),
    )

    assert "artifacts" not in payload


def test_explanation_can_be_omitted() -> None:
    payload = UniversalDecisionSerializer().serialize(
        build_result(),
        profile=DecisionSerializationProfile(
            include_explanation=False
        ),
    )

    assert "explanation" not in payload


def test_audit_facts_can_be_omitted() -> None:
    payload = UniversalDecisionSerializer().serialize(
        build_result(),
        profile=DecisionSerializationProfile(
            include_audit_facts=False
        ),
    )

    assert payload["explanation"]["audit_facts"] == {}


def test_source_metadata_can_be_omitted() -> None:
    payload = UniversalDecisionSerializer().serialize(
        build_result(),
        profile=DecisionSerializationProfile(
            include_source_metadata=False
        ),
    )

    assert "source_metadata" not in (
        payload["decision"]["metadata"]
    )


def test_audit_record_contains_complete_payload() -> None:
    payload = UniversalDecisionSerializer().audit_record(
        build_result()
    )

    assert payload["record_type"] == "universal_decision_audit"
    assert payload["decision_id"] == (
        "DECISION-SERIALIZATION-001"
    )
    assert "artifacts" in payload["payload"]
    assert "explanation" in payload["payload"]


def test_summary_record_is_flat() -> None:
    summary = UniversalDecisionSerializer().summary_record(
        build_result()
    )

    assert summary["decision_id"] == (
        "DECISION-SERIALIZATION-001"
    )
    assert summary["asset_id"] == "ETF:VOO"
    assert summary["action"] in {"buy", "strong_buy"}
    assert isinstance(summary["recommended_allocation"], str)


def test_round_trip_reconstructs_decision_result() -> None:
    serializer = UniversalDecisionSerializer()
    deserializer = UniversalDecisionDeserializer()

    original = build_result().decision_result
    reconstructed = deserializer.from_json(
        serializer.to_json(build_result())
    )

    assert reconstructed.decision_id == original.decision_id
    assert reconstructed.asset_id == original.asset_id
    assert reconstructed.action is original.action
    assert reconstructed.score.final_score == (
        original.score.final_score
    )
    assert reconstructed.maximum_allocation == (
        original.maximum_allocation
    )
    assert reconstructed.recommended_allocation == (
        original.recommended_allocation
    )
    assert reconstructed.generated_at == original.generated_at
    assert reconstructed.expires_at == original.expires_at
    assert reconstructed.evidence[0].evidence_id == (
        "EVIDENCE-001"
    )


def test_unsupported_schema_is_rejected() -> None:
    payload = UniversalDecisionSerializer().serialize(
        build_result()
    )
    payload["schema_version"] = "99.0"

    with pytest.raises(DecisionDeserializationError):
        UniversalDecisionDeserializer().deserialize(payload)


def test_invalid_record_type_is_rejected() -> None:
    payload = UniversalDecisionSerializer().serialize(
        build_result()
    )
    payload["record_type"] = "invalid"

    with pytest.raises(DecisionDeserializationError):
        UniversalDecisionDeserializer().deserialize(payload)


def test_invalid_json_is_rejected() -> None:
    with pytest.raises(DecisionDeserializationError):
        UniversalDecisionDeserializer().from_json("{invalid")


def test_invalid_enum_is_rejected() -> None:
    payload = UniversalDecisionSerializer().serialize(
        build_result()
    )
    payload["decision"]["action"] = "not_an_action"

    with pytest.raises(DecisionDeserializationError):
        UniversalDecisionDeserializer().deserialize(payload)


def test_json_export_writes_file(tmp_path) -> None:
    destination = tmp_path / "decision.json"

    path = UniversalDecisionExporter().export_json(
        build_result(),
        destination,
    )

    assert path == destination
    assert destination.exists()
    assert json.loads(
        destination.read_text(encoding="utf-8")
    )["schema_version"] == "1.0"


def test_audit_export_writes_file(tmp_path) -> None:
    destination = tmp_path / "audit.json"

    UniversalDecisionExporter().export_audit_json(
        build_result(),
        destination,
    )

    payload = json.loads(
        destination.read_text(encoding="utf-8")
    )

    assert payload["record_type"] == "universal_decision_audit"


def test_csv_export_writes_summary_row(tmp_path) -> None:
    destination = tmp_path / "decisions.csv"

    UniversalDecisionExporter().export_summary_csv(
        [build_result()],
        destination,
    )

    with destination.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["decision_id"] == (
        "DECISION-SERIALIZATION-001"
    )
    assert rows[0]["asset_id"] == "ETF:VOO"


def test_csv_export_requires_at_least_one_decision(
    tmp_path,
) -> None:
    with pytest.raises(DecisionExportError):
        UniversalDecisionExporter().export_summary_csv(
            [],
            tmp_path / "empty.csv",
        )


def test_invalid_json_indent_is_rejected() -> None:
    with pytest.raises(SerializationConfigurationError):
        DecisionSerializationProfile(json_indent=-1)


def test_reconstructed_decision_preserves_action_type() -> None:
    reconstructed = UniversalDecisionDeserializer().from_json(
        UniversalDecisionSerializer().to_json(build_result())
    )

    assert isinstance(reconstructed.action, DecisionAction)
