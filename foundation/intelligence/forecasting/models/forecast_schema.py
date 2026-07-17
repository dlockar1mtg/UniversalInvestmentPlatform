"""Serialization and validation utilities for the forecast contract."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping

from .forecast_enums import (
    ForecastDirection,
    ForecastHorizon,
    ForecastMethod,
    ForecastScenario,
    ForecastStatus,
    IntervalType,
)
from .forecast_models import (
    ForecastDistribution,
    ForecastInterval,
    ForecastProvenance,
    ForecastScenarioResult,
    UniversalForecast,
)

FORECAST_SCHEMA_NAME = "universal_forecast"
FORECAST_SCHEMA_VERSION = "1.0.0"


class ForecastSchemaError(ValueError):
    """Raised when a forecast payload violates the universal contract."""


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def forecast_to_dict(forecast: UniversalForecast) -> dict[str, Any]:
    """Serialize a UniversalForecast to a JSON-compatible dictionary."""

    validate_forecast(forecast)
    payload = _serialize(asdict(forecast))
    payload["schema_name"] = FORECAST_SCHEMA_NAME
    return payload


def _required(payload: Mapping[str, Any], key: str) -> Any:
    try:
        value = payload[key]
    except KeyError as exc:
        raise ForecastSchemaError(f"Missing required field: {key}") from exc
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ForecastSchemaError(f"Required field is empty: {key}")
    return value


def _parse_date(value: Any, field_name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise ForecastSchemaError(
            f"{field_name} must be an ISO date."
        ) from exc


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ForecastSchemaError(
                f"{field_name} must be an ISO datetime."
            ) from exc
    if parsed.tzinfo is None:
        raise ForecastSchemaError(f"{field_name} must include a timezone.")
    return parsed


def _enum(enum_type: type[Enum], value: Any, field_name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ForecastSchemaError(
            f"{field_name} must be one of: {allowed}."
        ) from exc


def _interval_from_dict(payload: Mapping[str, Any] | None) -> ForecastInterval | None:
    if payload is None:
        return None
    return ForecastInterval(
        lower=float(_required(payload, "lower")),
        upper=float(_required(payload, "upper")),
        coverage=float(payload.get("coverage", 0.80)),
        interval_type=_enum(
            IntervalType,
            payload.get("interval_type", IntervalType.PREDICTION.value),
            "interval.interval_type",
        ),
    )


def _distribution_from_dict(
    payload: Mapping[str, Any] | None,
) -> ForecastDistribution | None:
    if payload is None:
        return None
    return ForecastDistribution(
        distribution_name=str(_required(payload, "distribution_name")),
        mean=float(_required(payload, "mean")),
        median=float(_required(payload, "median")),
        standard_deviation=float(_required(payload, "standard_deviation")),
        minimum=(
            None if payload.get("minimum") is None else float(payload["minimum"])
        ),
        maximum=(
            None if payload.get("maximum") is None else float(payload["maximum"])
        ),
        sample_count=(
            None
            if payload.get("sample_count") is None
            else int(payload["sample_count"])
        ),
        quantiles={
            str(key): float(value)
            for key, value in dict(payload.get("quantiles", {})).items()
        },
    )


def _provenance_from_dict(payload: Mapping[str, Any]) -> ForecastProvenance:
    return ForecastProvenance(
        model_name=str(_required(payload, "model_name")),
        model_version=str(_required(payload, "model_version")),
        method=_enum(
            ForecastMethod,
            _required(payload, "method"),
            "provenance.method",
        ),
        generated_at=_parse_datetime(
            _required(payload, "generated_at"),
            "provenance.generated_at",
        ),
        training_data_start=(
            None
            if payload.get("training_data_start") is None
            else _parse_date(
                payload["training_data_start"],
                "provenance.training_data_start",
            )
        ),
        training_data_end=(
            None
            if payload.get("training_data_end") is None
            else _parse_date(
                payload["training_data_end"],
                "provenance.training_data_end",
            )
        ),
        source_run_id=payload.get("source_run_id"),
        source_dataset_ids=tuple(payload.get("source_dataset_ids", ())),
        feature_set_version=payload.get("feature_set_version"),
        code_commit=payload.get("code_commit"),
        parameters=dict(payload.get("parameters", {})),
    )


def _scenario_from_dict(payload: Mapping[str, Any]) -> ForecastScenarioResult:
    return ForecastScenarioResult(
        scenario=_enum(
            ForecastScenario,
            _required(payload, "scenario"),
            "scenarios[].scenario",
        ),
        target_value=float(_required(payload, "target_value")),
        probability=(
            None
            if payload.get("probability") is None
            else float(payload["probability"])
        ),
        expected_return=(
            None
            if payload.get("expected_return") is None
            else float(payload["expected_return"])
        ),
        interval=_interval_from_dict(payload.get("interval")),
        assumptions=tuple(payload.get("assumptions", ())),
    )


def forecast_from_dict(payload: Mapping[str, Any]) -> UniversalForecast:
    """Deserialize and validate a universal forecast dictionary."""

    try:
        provenance_payload = _required(payload, "provenance")
        if not isinstance(provenance_payload, Mapping):
            raise ForecastSchemaError("provenance must be an object.")

        forecast = UniversalForecast(
            forecast_id=str(payload.get("forecast_id", "")).strip()
            or __import__("uuid").uuid4().hex,
            schema_version=str(
                payload.get("schema_version", FORECAST_SCHEMA_VERSION)
            ),
            asset_id=str(_required(payload, "asset_id")),
            as_of_date=_parse_date(_required(payload, "as_of_date"), "as_of_date"),
            target_date=_parse_date(
                _required(payload, "target_date"),
                "target_date",
            ),
            horizon=_enum(
                ForecastHorizon,
                _required(payload, "horizon"),
                "horizon",
            ),
            reference_value=float(_required(payload, "reference_value")),
            point_forecast=float(_required(payload, "point_forecast")),
            currency=str(_required(payload, "currency")),
            provenance=_provenance_from_dict(provenance_payload),
            status=_enum(
                ForecastStatus,
                payload.get("status", ForecastStatus.DRAFT.value),
                "status",
            ),
            direction=_enum(
                ForecastDirection,
                payload.get("direction", ForecastDirection.UNKNOWN.value),
                "direction",
            ),
            confidence_score=(
                None
                if payload.get("confidence_score") is None
                else float(payload["confidence_score"])
            ),
            expected_return=(
                None
                if payload.get("expected_return") is None
                else float(payload["expected_return"])
            ),
            interval=_interval_from_dict(payload.get("interval")),
            distribution=_distribution_from_dict(payload.get("distribution")),
            scenarios=tuple(
                _scenario_from_dict(item)
                for item in payload.get("scenarios", ())
            ),
            calibration_score=(
                None
                if payload.get("calibration_score") is None
                else float(payload["calibration_score"])
            ),
            backtest_run_id=payload.get("backtest_run_id"),
            notes=tuple(payload.get("notes", ())),
            metadata=dict(payload.get("metadata", {})),
        )
    except ForecastSchemaError:
        raise
    except (TypeError, ValueError) as exc:
        raise ForecastSchemaError(str(exc)) from exc

    validate_forecast(forecast)
    return forecast


def validate_forecast(forecast: UniversalForecast) -> None:
    """Validate a UniversalForecast instance.

    Dataclass construction performs most field validation. This function adds
    platform contract checks that span multiple fields.
    """

    if forecast.schema_version != FORECAST_SCHEMA_VERSION:
        raise ForecastSchemaError(
            "Unsupported schema_version "
            f"{forecast.schema_version!r}; expected {FORECAST_SCHEMA_VERSION!r}."
        )

    expected_return = (
        (forecast.point_forecast / forecast.reference_value) - 1.0
        if forecast.reference_value != 0
        else None
    )
    if (
        expected_return is not None
        and forecast.expected_return is not None
        and abs(expected_return - forecast.expected_return) > 1e-6
    ):
        raise ForecastSchemaError(
            "expected_return is inconsistent with reference_value and "
            "point_forecast."
        )

    by_name = {scenario.scenario: scenario for scenario in forecast.scenarios}
    if {
        ForecastScenario.BEAR,
        ForecastScenario.BASE,
        ForecastScenario.BULL,
    }.issubset(by_name):
        bear = by_name[ForecastScenario.BEAR].target_value
        base = by_name[ForecastScenario.BASE].target_value
        bull = by_name[ForecastScenario.BULL].target_value
        if not bear <= base <= bull:
            raise ForecastSchemaError(
                "Scenario target values must satisfy bear <= base <= bull."
            )


def validate_forecast_payload(payload: Mapping[str, Any]) -> list[str]:
    """Return validation errors for a dictionary without raising them."""

    try:
        forecast_from_dict(payload)
    except (ForecastSchemaError, TypeError, ValueError) as exc:
        return [str(exc)]
    return []
