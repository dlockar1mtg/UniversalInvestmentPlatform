"""Tests for Phase 4.1.3 forecast engine abstraction."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from foundation.intelligence.forecasting.engine import (
    BaseForecastEngine,
    DuplicateForecastEngineError,
    ForecastEngineMetadata,
    ForecastEngineNotFoundError,
    ForecastEngineRegistry,
    ForecastExecutionContext,
    ForecastExecutionStatus,
    ForecastRequest,
    ForecastValidationError,
)
from foundation.intelligence.forecasting.models import (
    ForecastDirection,
    ForecastHorizon,
    ForecastMethod,
    ForecastProvenance,
    UniversalForecast,
)


class StaticForecastEngine(BaseForecastEngine):
    def __init__(
        self,
        *,
        version: str = "1.0.0",
        asset_classes: tuple[str, ...] = ("crypto",),
        horizons: tuple[ForecastHorizon, ...] = (
            ForecastHorizon.ONE_YEAR,
        ),
        fail: bool = False,
        wrong_asset: bool = False,
    ) -> None:
        self._metadata = ForecastEngineMetadata(
            engine_name="static-baseline",
            engine_version=version,
            asset_classes=asset_classes,
            supported_horizons=horizons,
            description="Deterministic test forecast engine.",
        )
        self.fail = fail
        self.wrong_asset = wrong_asset
        self.success_calls = 0
        self.failure_calls = 0

    @property
    def metadata(self) -> ForecastEngineMetadata:
        return self._metadata

    def generate_forecast(
        self,
        request: ForecastRequest,
        context: ForecastExecutionContext,
    ) -> UniversalForecast:
        if self.fail:
            raise RuntimeError("model failure")

        point_forecast = request.reference_value * 1.10
        return UniversalForecast(
            asset_id="WRONG" if self.wrong_asset else request.asset_id,
            as_of_date=request.as_of_date,
            target_date=self.resolve_target_date(request),
            horizon=request.horizon,
            reference_value=request.reference_value,
            point_forecast=point_forecast,
            currency=request.currency,
            provenance=ForecastProvenance(
                model_name=self.metadata.engine_name,
                model_version=self.metadata.engine_version,
                method=ForecastMethod.RULE_BASED,
                generated_at=datetime(
                    2026, 7, 17, 18, 0, tzinfo=timezone.utc
                ),
            ),
            direction=ForecastDirection.UP,
            expected_return=0.10,
        )

    def after_success(self, request, forecast, context) -> None:
        self.success_calls += 1

    def after_failure(self, request, error, context) -> None:
        self.failure_calls += 1


def build_request(**changes) -> ForecastRequest:
    values = {
        "request_id": "request-001",
        "asset_id": "BTC-USD",
        "asset_class": "crypto",
        "as_of_date": date(2026, 7, 17),
        "horizon": ForecastHorizon.ONE_YEAR,
        "reference_value": 100_000.0,
        "currency": "USD",
        "features": {"momentum": 0.25},
        "options": {"scenario_count": 2_000},
    }
    values.update(changes)
    return ForecastRequest(**values)


def test_request_freezes_feature_and_option_mappings() -> None:
    request = build_request()

    with pytest.raises(TypeError):
        request.features["momentum"] = 0.50
    with pytest.raises(TypeError):
        request.options["scenario_count"] = 100


def test_execution_context_returns_seeded_random_generator() -> None:
    context = ForecastExecutionContext(random_seed=42)

    assert context.create_random().random() == context.create_random().random()


def test_engine_executes_successful_lifecycle() -> None:
    engine = StaticForecastEngine()

    result = engine.execute(build_request())

    assert result.status is ForecastExecutionStatus.SUCCEEDED
    assert result.forecast is not None
    assert result.forecast.asset_id == "BTC-USD"
    assert result.forecast.point_forecast == pytest.approx(110_000.0)
    assert result.metrics["horizon"] == "1y"
    assert result.duration_seconds >= 0
    assert engine.success_calls == 1
    assert engine.failure_calls == 0


def test_target_date_is_resolved_from_horizon() -> None:
    engine = StaticForecastEngine()
    result = engine.execute(build_request())

    assert result.forecast is not None
    assert result.forecast.target_date == date(2027, 7, 17)


def test_explicit_target_date_is_preserved() -> None:
    engine = StaticForecastEngine()
    request = build_request(target_date=date(2027, 8, 1))

    result = engine.execute(request)

    assert result.forecast is not None
    assert result.forecast.target_date == date(2027, 8, 1)


def test_unsupported_asset_class_is_rejected() -> None:
    engine = StaticForecastEngine()

    result = engine.execute(build_request(asset_class="metals"))

    assert result.status is ForecastExecutionStatus.REJECTED
    assert result.error_type == "ForecastValidationError"
    assert "does not support asset class" in result.error_message
    assert engine.failure_calls == 1


def test_unsupported_horizon_is_rejected() -> None:
    engine = StaticForecastEngine()

    result = engine.execute(
        build_request(horizon=ForecastHorizon.FIVE_YEARS)
    )

    assert result.status is ForecastExecutionStatus.REJECTED
    assert "does not support horizon" in result.error_message


def test_model_exception_returns_failed_result() -> None:
    engine = StaticForecastEngine(fail=True)

    result = engine.execute(build_request())

    assert result.status is ForecastExecutionStatus.FAILED
    assert result.error_type == "RuntimeError"
    assert result.error_message == "model failure"
    assert engine.failure_calls == 1


def test_raise_errors_propagates_validation_failure() -> None:
    engine = StaticForecastEngine()

    with pytest.raises(ForecastValidationError):
        engine.execute(
            build_request(asset_class="housing"),
            raise_errors=True,
        )


def test_output_asset_mismatch_is_rejected() -> None:
    engine = StaticForecastEngine(wrong_asset=True)

    result = engine.execute(build_request())

    assert result.status is ForecastExecutionStatus.REJECTED
    assert "asset_id does not match" in result.error_message


def test_registry_registers_and_gets_exact_engine() -> None:
    registry = ForecastEngineRegistry()
    engine = StaticForecastEngine(version="1.0.0")
    registry.register(engine)

    assert len(registry) == 1
    assert registry.get("static-baseline", "1.0.0") is engine


def test_registry_rejects_duplicate_engine_key() -> None:
    registry = ForecastEngineRegistry()
    registry.register(StaticForecastEngine())

    with pytest.raises(DuplicateForecastEngineError):
        registry.register(StaticForecastEngine())


def test_registry_gets_latest_version() -> None:
    registry = ForecastEngineRegistry()
    older = StaticForecastEngine(version="1.2.0")
    newer = StaticForecastEngine(version="1.10.0")
    registry.register(older)
    registry.register(newer)

    assert registry.get("static-baseline") is newer


def test_registry_resolves_compatible_engine() -> None:
    registry = ForecastEngineRegistry()
    crypto = StaticForecastEngine(version="1.0.0")
    multi_asset = StaticForecastEngine(
        version="2.0.0",
        asset_classes=("crypto", "metals"),
        horizons=(
            ForecastHorizon.ONE_YEAR,
            ForecastHorizon.FIVE_YEARS,
        ),
    )
    registry.register(crypto)
    registry.register(multi_asset)

    resolved = registry.resolve(
        asset_class="metals",
        horizon=ForecastHorizon.FIVE_YEARS,
    )

    assert resolved is multi_asset


def test_registry_raises_when_no_engine_is_compatible() -> None:
    registry = ForecastEngineRegistry()
    registry.register(StaticForecastEngine())

    with pytest.raises(ForecastEngineNotFoundError):
        registry.resolve(
            asset_class="housing",
            horizon=ForecastHorizon.FIVE_YEARS,
        )


def test_registry_unregisters_engine() -> None:
    registry = ForecastEngineRegistry()
    registry.register(StaticForecastEngine())
    registry.unregister("static-baseline", "1.0.0")

    assert len(registry) == 0


def test_registry_listing_is_serializable_and_sorted() -> None:
    registry = ForecastEngineRegistry()
    registry.register(StaticForecastEngine(version="2.0.0"))
    registry.register(StaticForecastEngine(version="1.0.0"))

    listing = registry.list_engines()

    assert [item.engine_version for item in listing] == [
        "1.0.0",
        "2.0.0",
    ]
    assert listing[0].supported_horizons == ("1y",)

