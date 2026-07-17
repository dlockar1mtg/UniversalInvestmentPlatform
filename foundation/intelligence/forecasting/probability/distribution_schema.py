"""Serialization and validation for probabilistic forecast distributions."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from enum import Enum
import json
from typing import Any, Mapping

from ..models import ForecastHorizon
from .distribution_enums import (
    DistributionFamily,
    DistributionStatus,
    TailRiskSide,
)
from .distribution_models import (
    DistributionProvenance,
    DistributionStatistics,
    ForecastConfidenceInterval,
    ForecastDistributionResult,
    ForecastPercentile,
    TailRiskMetrics,
)

DISTRIBUTION_SCHEMA_NAME = "forecast_distribution"
DISTRIBUTION_SCHEMA_VERSION = "1.0.0"


class DistributionSchemaError(ValueError):
    """Raised when a distribution payload violates the contract."""


def _serialize(value: Any) -> Any:
    if is_dataclass(value):
        return {
            item.name: _serialize(getattr(value, item.name))
            for item in fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {
            str(key): _serialize(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def distribution_to_dict(
    distribution: ForecastDistributionResult,
) -> dict[str, Any]:
    """Serialize a distribution to a JSON-compatible dictionary."""

    validate_distribution(distribution)
    payload = _serialize(distribution)
    payload["schema_name"] = DISTRIBUTION_SCHEMA_NAME
    return payload


def distribution_to_json(
    distribution: ForecastDistributionResult,
    *,
    indent: int | None = 2,
) -> str:
    """Serialize a distribution deterministically to JSON."""

    return json.dumps(
        distribution_to_dict(distribution),
        indent=indent,
        sort_keys=True,
    )


def _required(payload: Mapping[str, Any], name: str) -> Any:
    try:
        value = payload[name]
    except KeyError as exc:
        raise DistributionSchemaError(
            f"Missing required field: {name}"
        ) from exc
    if value is None or (isinstance(value, str) and not value.strip()):
        raise DistributionSchemaError(
            f"Required field is empty: {name}"
        )
    return value


def _parse_date(value: Any, name: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise DistributionSchemaError(
            f"{name} must be an ISO date."
        ) from exc


def _parse_datetime(value: Any, name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        except (TypeError, ValueError) as exc:
            raise DistributionSchemaError(
                f"{name} must be an ISO datetime."
            ) from exc
    if parsed.tzinfo is None:
        raise DistributionSchemaError(
            f"{name} must include a timezone."
        )
    return parsed


def _enum(enum_type: type[Enum], value: Any, name: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise DistributionSchemaError(
            f"{name} must be one of: {allowed}."
        ) from exc


def _statistics(payload: Mapping[str, Any]) -> DistributionStatistics:
    return DistributionStatistics(
        mean=float(_required(payload, "mean")),
        median=float(_required(payload, "median")),
        variance=float(_required(payload, "variance")),
        standard_deviation=float(
            _required(payload, "standard_deviation")
        ),
        minimum=float(_required(payload, "minimum")),
        maximum=float(_required(payload, "maximum")),
        skewness=(
            None
            if payload.get("skewness") is None
            else float(payload["skewness"])
        ),
        excess_kurtosis=(
            None
            if payload.get("excess_kurtosis") is None
            else float(payload["excess_kurtosis"])
        ),
        mode=(
            None
            if payload.get("mode") is None
            else float(payload["mode"])
        ),
        sample_count=(
            None
            if payload.get("sample_count") is None
            else int(payload["sample_count"])
        ),
    )


def _provenance(payload: Mapping[str, Any]) -> DistributionProvenance:
    return DistributionProvenance(
        model_name=str(_required(payload, "model_name")),
        model_version=str(_required(payload, "model_version")),
        generated_at=_parse_datetime(
            _required(payload, "generated_at"),
            "provenance.generated_at",
        ),
        source_forecast_ids=tuple(
            payload.get("source_forecast_ids", ())
        ),
        source_run_id=payload.get("source_run_id"),
        random_seed=(
            None
            if payload.get("random_seed") is None
            else int(payload["random_seed"])
        ),
        simulation_count=(
            None
            if payload.get("simulation_count") is None
            else int(payload["simulation_count"])
        ),
        code_commit=payload.get("code_commit"),
        parameters=dict(payload.get("parameters", {})),
    )


def distribution_from_dict(
    payload: Mapping[str, Any],
) -> ForecastDistributionResult:
    """Deserialize and validate a forecast distribution payload."""

    try:
        statistics_payload = _required(payload, "statistics")
        provenance_payload = _required(payload, "provenance")
        if not isinstance(statistics_payload, Mapping):
            raise DistributionSchemaError(
                "statistics must be an object."
            )
        if not isinstance(provenance_payload, Mapping):
            raise DistributionSchemaError(
                "provenance must be an object."
            )

        result = ForecastDistributionResult(
            distribution_id=str(
                payload.get("distribution_id", "")
            ).strip()
            or __import__("uuid").uuid4().hex,
            schema_version=str(
                payload.get(
                    "schema_version",
                    DISTRIBUTION_SCHEMA_VERSION,
                )
            ),
            status=_enum(
                DistributionStatus,
                payload.get(
                    "status",
                    DistributionStatus.DRAFT.value,
                ),
                "status",
            ),
            asset_id=str(_required(payload, "asset_id")),
            asset_class=str(_required(payload, "asset_class")),
            as_of_date=_parse_date(
                _required(payload, "as_of_date"),
                "as_of_date",
            ),
            target_date=_parse_date(
                _required(payload, "target_date"),
                "target_date",
            ),
            horizon=_enum(
                ForecastHorizon,
                _required(payload, "horizon"),
                "horizon",
            ),
            reference_value=float(
                _required(payload, "reference_value")
            ),
            currency=str(_required(payload, "currency")),
            family=_enum(
                DistributionFamily,
                _required(payload, "family"),
                "family",
            ),
            statistics=_statistics(statistics_payload),
            provenance=_provenance(provenance_payload),
            percentiles=tuple(
                ForecastPercentile(
                    probability=float(
                        _required(item, "probability")
                    ),
                    value=float(_required(item, "value")),
                    label=item.get("label"),
                )
                for item in payload.get("percentiles", ())
            ),
            confidence_intervals=tuple(
                ForecastConfidenceInterval(
                    lower_probability=float(
                        _required(item, "lower_probability")
                    ),
                    upper_probability=float(
                        _required(item, "upper_probability")
                    ),
                    lower_value=float(
                        _required(item, "lower_value")
                    ),
                    upper_value=float(
                        _required(item, "upper_value")
                    ),
                    coverage=float(_required(item, "coverage")),
                )
                for item in payload.get(
                    "confidence_intervals",
                    (),
                )
            ),
            tail_risk=tuple(
                TailRiskMetrics(
                    confidence_level=float(
                        _required(item, "confidence_level")
                    ),
                    side=_enum(
                        TailRiskSide,
                        _required(item, "side"),
                        "tail_risk[].side",
                    ),
                    value_at_risk=float(
                        _required(item, "value_at_risk")
                    ),
                    expected_shortfall=float(
                        _required(item, "expected_shortfall")
                    ),
                    probability_of_loss=float(
                        _required(item, "probability_of_loss")
                    ),
                    probability_of_target_shortfall=(
                        None
                        if item.get(
                            "probability_of_target_shortfall"
                        )
                        is None
                        else float(
                            item[
                                "probability_of_target_shortfall"
                            ]
                        )
                    ),
                    target_return=(
                        None
                        if item.get("target_return") is None
                        else float(item["target_return"])
                    ),
                )
                for item in payload.get("tail_risk", ())
            ),
            probability_above_reference=(
                None
                if payload.get("probability_above_reference")
                is None
                else float(
                    payload["probability_above_reference"]
                )
            ),
            probability_below_reference=(
                None
                if payload.get("probability_below_reference")
                is None
                else float(
                    payload["probability_below_reference"]
                )
            ),
            probability_above_target=(
                None
                if payload.get("probability_above_target")
                is None
                else float(payload["probability_above_target"])
            ),
            target_value=(
                None
                if payload.get("target_value") is None
                else float(payload["target_value"])
            ),
            notes=tuple(payload.get("notes", ())),
            metadata=dict(payload.get("metadata", {})),
        )
    except DistributionSchemaError:
        raise
    except (TypeError, ValueError) as exc:
        raise DistributionSchemaError(str(exc)) from exc

    validate_distribution(result)
    return result


def validate_distribution(
    distribution: ForecastDistributionResult,
) -> None:
    """Validate cross-field distribution contract rules."""

    if distribution.schema_version != DISTRIBUTION_SCHEMA_VERSION:
        raise DistributionSchemaError(
            "Unsupported schema_version "
            f"{distribution.schema_version!r}; expected "
            f"{DISTRIBUTION_SCHEMA_VERSION!r}."
        )

    percentile_by_probability = {
        item.probability: item
        for item in distribution.percentiles
    }
    for interval in distribution.confidence_intervals:
        lower = percentile_by_probability.get(
            interval.lower_probability
        )
        upper = percentile_by_probability.get(
            interval.upper_probability
        )
        if lower is not None and abs(
            lower.value - interval.lower_value
        ) > 1e-9:
            raise DistributionSchemaError(
                "Confidence interval lower value is inconsistent "
                "with the matching percentile."
            )
        if upper is not None and abs(
            upper.value - interval.upper_value
        ) > 1e-9:
            raise DistributionSchemaError(
                "Confidence interval upper value is inconsistent "
                "with the matching percentile."
            )

    median = percentile_by_probability.get(0.5)
    if (
        median is not None
        and abs(
            median.value - distribution.statistics.median
        )
        > 1e-9
    ):
        raise DistributionSchemaError(
            "The 50th percentile must equal statistics.median."
        )


def validate_distribution_payload(
    payload: Mapping[str, Any],
) -> list[str]:
    """Return payload validation errors without raising them."""

    try:
        distribution_from_dict(payload)
    except (DistributionSchemaError, TypeError, ValueError) as exc:
        return [str(exc)]
    return []
