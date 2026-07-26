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

## Signal mapping

Explicit source actions are preserved when they map to UIP actions. Native `RANKED_OPPORTUNITY` rows are converted deterministically:

- score at least 75 and positive expected return → `STRONG_BUY`
- score at least 60 and positive expected return → `BUY`
- score at least 50 → `WATCH`
- otherwise → `HOLD`

A recommendation is deployable only when:

- platform status is `READY`, `PASS`, or `SUCCESS`;
- no platform errors are reported;
- the signal is `STRONG_BUY`, `BUY`, or `ACCUMULATE`;
- the normalized score clears the UIP deployment threshold;
- the allocation ceiling supports at least one increment.

## Allocation semantics

Metals recommendations are dollar-denominated and support fractional allocation. The default increment is `$1.00`; UIP may change it when building the package. `maximum_allocation` is constrained by the UIP-provided ceiling and any certified recommended-dollar or target-weight cap in the source package.

## Fail-closed behavior

Missing required files or a degraded platform status produce `domain_status=INCOMPLETE`. UIP excludes incomplete domains from capital allocation while preserving the remaining domain decisions and cash option.

## CLI

```text
python scripts/build_metals_domain_package.py \
  --package-root <certified-metals-package> \
  --allocation-ceiling 3000 \
  --output data/domain_packages/metals/latest.json
```

## Scheduling

No schedule is added in this phase. UIP remains the sole future scheduling and orchestration authority.
