# Phase 4.1.3 — Forecast Engine Abstraction

## Purpose

Phase 4.1.3 defines the common execution lifecycle used by every forecasting
implementation in the Universal Investment Intelligence Platform.

## Components

- `ForecastRequest`: immutable platform-wide engine input.
- `ForecastEngineMetadata`: engine identity and compatibility declaration.
- `ForecastExecutionContext`: runtime services, logging, and deterministic RNG.
- `BaseForecastEngine`: template lifecycle for validation, preparation,
  generation, output validation, success handling, and failure handling.
- `ForecastExecutionResult`: auditable success, rejection, or failure result.
- `ForecastEngineRegistry`: versioned registration and compatible resolution.

## Execution lifecycle

1. Validate request compatibility.
2. Prepare request data.
3. Generate a `UniversalForecast`.
4. Validate the universal forecast and request/output invariants.
5. Run success or failure hooks.
6. Return a structured audit result.

## Extension rule

Asset-specific engines subclass `BaseForecastEngine`, declare immutable
metadata, and implement `generate_forecast`. Shared orchestration behavior must
remain in the base abstraction rather than being duplicated by asset engines.
