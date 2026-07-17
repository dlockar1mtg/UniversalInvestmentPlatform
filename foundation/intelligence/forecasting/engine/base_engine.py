"""Abstract base class for all universal forecast engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta, timezone
from typing import Any

from ..models import UniversalForecast, validate_forecast
from .engine_context import ForecastExecutionContext
from .engine_contracts import (
    ForecastEngineMetadata,
    ForecastExecutionResult,
    ForecastExecutionStatus,
    ForecastRequest,
    ForecastValidationError,
)


class BaseForecastEngine(ABC):
    """Template-method implementation of the forecast execution lifecycle."""

    @property
    @abstractmethod
    def metadata(self) -> ForecastEngineMetadata:
        """Return immutable metadata describing the engine."""

    @abstractmethod
    def generate_forecast(
        self,
        request: ForecastRequest,
        context: ForecastExecutionContext,
    ) -> UniversalForecast:
        """Generate a forecast after request validation and preparation."""

    def validate_request(self, request: ForecastRequest) -> None:
        """Validate engine compatibility with the request."""

        if request.asset_class not in self.metadata.asset_classes:
            raise ForecastValidationError(
                f"Engine {self.metadata.engine_name!r} does not support "
                f"asset class {request.asset_class!r}."
            )
        if request.horizon not in self.metadata.supported_horizons:
            raise ForecastValidationError(
                f"Engine {self.metadata.engine_name!r} does not support "
                f"horizon {request.horizon.value!r}."
            )

    def prepare_request(
        self,
        request: ForecastRequest,
        context: ForecastExecutionContext,
    ) -> ForecastRequest:
        """Hook for feature preparation or dependency resolution."""

        return request

    def validate_output(
        self,
        request: ForecastRequest,
        forecast: UniversalForecast,
    ) -> None:
        """Validate common request-to-output invariants."""

        validate_forecast(forecast)

        if forecast.asset_id != request.asset_id:
            raise ForecastValidationError(
                "Forecast asset_id does not match the request."
            )
        if forecast.as_of_date != request.as_of_date:
            raise ForecastValidationError(
                "Forecast as_of_date does not match the request."
            )
        if forecast.horizon is not request.horizon:
            raise ForecastValidationError(
                "Forecast horizon does not match the request."
            )
        if forecast.currency != request.currency:
            raise ForecastValidationError(
                "Forecast currency does not match the request."
            )
        if request.target_date is not None:
            if forecast.target_date != request.target_date:
                raise ForecastValidationError(
                    "Forecast target_date does not match the request."
                )

    def after_success(
        self,
        request: ForecastRequest,
        forecast: UniversalForecast,
        context: ForecastExecutionContext,
    ) -> None:
        """Hook invoked after successful output validation."""

    def after_failure(
        self,
        request: ForecastRequest,
        error: Exception,
        context: ForecastExecutionContext,
    ) -> None:
        """Hook invoked after rejected or failed execution."""

    def execute(
        self,
        request: ForecastRequest,
        context: ForecastExecutionContext | None = None,
        *,
        raise_errors: bool = False,
    ) -> ForecastExecutionResult:
        """Execute the full forecast lifecycle and return an audit result."""

        runtime = context or ForecastExecutionContext()
        started_at = datetime.now(timezone.utc)

        try:
            self.validate_request(request)
            prepared_request = self.prepare_request(request, runtime)
            forecast = self.generate_forecast(prepared_request, runtime)
            self.validate_output(prepared_request, forecast)
            self.after_success(prepared_request, forecast, runtime)
        except ForecastValidationError as exc:
            self.after_failure(request, exc, runtime)
            if raise_errors:
                raise
            return self._failure_result(
                request=request,
                status=ForecastExecutionStatus.REJECTED,
                started_at=started_at,
                error=exc,
            )
        except Exception as exc:
            self.after_failure(request, exc, runtime)
            if raise_errors:
                raise
            return self._failure_result(
                request=request,
                status=ForecastExecutionStatus.FAILED,
                started_at=started_at,
                error=exc,
            )

        completed_at = datetime.now(timezone.utc)
        return ForecastExecutionResult(
            request_id=request.request_id,
            engine_name=self.metadata.engine_name,
            engine_version=self.metadata.engine_version,
            status=ForecastExecutionStatus.SUCCEEDED,
            started_at=started_at,
            completed_at=completed_at,
            forecast=forecast,
            metrics={
                "asset_class": request.asset_class,
                "horizon": request.horizon.value,
            },
        )

    def resolve_target_date(self, request: ForecastRequest) -> date:
        """Resolve target date from the request or normalized horizon."""

        return request.target_date or (
            request.as_of_date
            + timedelta(days=request.horizon.approximate_days)
        )

    def _failure_result(
        self,
        *,
        request: ForecastRequest,
        status: ForecastExecutionStatus,
        started_at: datetime,
        error: Exception,
    ) -> ForecastExecutionResult:
        return ForecastExecutionResult(
            request_id=request.request_id,
            engine_name=self.metadata.engine_name,
            engine_version=self.metadata.engine_version,
            status=status,
            started_at=started_at,
            completed_at=datetime.now(timezone.utc),
            error_type=type(error).__name__,
            error_message=str(error),
            metrics={
                "asset_class": request.asset_class,
                "horizon": request.horizon.value,
            },
        )
