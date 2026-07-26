# Phase 6.1 — Certified Metals Domain Adapter

## Purpose

Convert the already-certified Metals universal export package into the UIP cross-domain opportunity contract without modifying or importing the Metals source project.

## Authority boundary

- Metals owns data collection, forecasting, risk, positions, and recommendation evidence.
- UIP owns monthly capital allocation and all future scheduling.
- The adapter is read-only and file-based.
- No Metals workflow or scheduler is created.

## Required certified package files

- `asset_master.csv`
- `forecasts.csv`
- `recommendations.csv`
- `risk_metrics.csv`
- `portfolio_positions.csv`
- `platform_status.csv`

The source package remains the certified Phase 1.2/Phase 8.1 Metals adapter output. Phase 6.1 does not replace it.

## Governed forecast policy

The adapter uses a 12-month forecast horizon by default. Vehicle recommendations inherit economic evidence only through this explicit crosswalk:

- GLD, IAU, SGOL → gold
- SLV, SIVR → silver
- PPLT → platinum
- CPER, COPX → copper
- URA → uranium
- BIL → no commodity forecast

The adapter reads `expected_total_return` from the selected forecast. Missing forecast evidence remains `null`; it is never manufactured as zero.

## Signal mapping

Explicit source actions are preserved only when supported by positive linked forecast evidence. A source `STRONG_BUY`, `BUY`, or `ACCUMULATE` with missing or non-positive forecast evidence is capped at `WATCH`.

Native `RANKED_OPPORTUNITY` rows are converted deterministically:

- score at least 75 and positive expected return → `STRONG_BUY`
- score at least 60 and positive expected return → `BUY`
- score at least 50 → `WATCH`
- otherwise → `HOLD`

A recommendation is deployable only when:

- platform readiness passes;
- the signal is `STRONG_BUY`, `BUY`, or `ACCUMULATE`;
- the normalized score clears the UIP deployment threshold;
- positive forecast evidence is present;
- the allocation ceiling supports at least one increment.

## Readiness policy

A package is ready when either:

1. `status` is `READY`, `PASS`, or `SUCCESS`; or
2. legacy `status` is blank while `run_status=SUCCESS`, `warning_count=0`, and `error_count=0`.

Errors always fail closed. A blank legacy status with warnings is not accepted.

## Portfolio and risk evidence

Positions and risks join by `universal_asset_id`. A real zero-valued position is preserved as zero and is not treated as missing data.

## Allocation semantics

Metals recommendations are dollar-denominated and support fractional allocation. The default increment is `$1.00`; UIP may change it when building the package. `maximum_allocation` is constrained by the UIP-provided ceiling and any certified recommended-dollar or target-weight cap in the source package.

## Fail-closed behavior

Missing required files, degraded readiness, missing forecast evidence, or non-positive forecast evidence prevent capital deployment. UIP excludes incomplete domains while preserving other domain decisions and the cash option.

## CLI

```text
python scripts/build_metals_domain_package.py \
  --package-root <certified-metals-package> \
  --allocation-ceiling 3000 \
  --forecast-horizon-months 12 \
  --output data/domain_packages/metals/latest.json
```

## Scheduling

No schedule is added in this phase. UIP remains the sole future scheduling and orchestration authority.
