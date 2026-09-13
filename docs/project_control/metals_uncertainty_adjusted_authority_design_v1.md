# Metals Uncertainty Adjusted Authority Design V1 — Read-Only Gate

Status: DESIGN AUDIT ONLY

## Purpose

Determine whether UIP has enough governed native Metals evidence to design a new, explicitly non-legacy-equivalent uncertainty-adjusted authority.

This gate is read-only. It does not create uncertainty-adjusted rows, stage a publication, activate a publication, alter the central publisher, or authorize portfolio/allocation/execution behavior.

## Current recovery position

Metals rich publication recovery is formally 8 of 10 certified families. The two remaining uncertified families are `uncertainty_adjusted` and `tactical_state`.

The restored rich publication contains 32 `metals_uncertainty_adjusted` rows. Those rows are historical evidence only. Their count, formulas, asset/horizon grain, and lineage must not be copied or inferred into a new authority without explicit governance.

## Evidence this audit may use

- current certified UIP-native Metals forecasts and their expected-return/confidence fields;
- certified `UIP_NATIVE_METALS_REGIME_PROBABILITY_V1` evidence, explicitly descriptive and not statistically calibrated;
- certified `UIP_NATIVE_METALS_RISK_V1` evidence, while preserving its `VEHICLE_ONLY` boundary;
- certified `UIP_NATIVE_METALS_RECOMMENDATION_CHANGE_V1` evidence;
- persisted UIP-owned benchmark and vehicle observations, queried read-only;
- restored uncertainty-adjusted rows only as historical schema/lineage evidence.

## Authorization boundary

A PASS authorizes only the design of a future `UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1` authority.

The candidate boundary is `BENCHMARK_COMMODITY_ASSET_BY_FORECAST_HORIZON`. That boundary is not itself a production contract; the rehearsal must later define and test the exact grain and formula.

A design PASS does not authorize production rows or recognition as family 9 of 10.

## Semantics that must be governed before a builder exists

The rehearsal contract must explicitly define:

1. the exact uncertainty-adjusted quantity or quantities;
2. row grain and horizon treatment;
3. the uncertainty source and what native confidence does and does not mean;
4. whether Regime Probability V1 contributes, without double-counting confidence;
5. whether Risk V1 contributes at all; because Risk V1 is vehicle-only, any vehicle-to-commodity mapping requires separate explicit governance and must otherwise remain prohibited;
6. the adjustment/shrinkage formula, parameter bounds, monotonicity, and treatment of zero or negative expected returns;
7. minimum evidence thresholds and unavailable behavior;
8. historical reconstruction rules if historical adjusted views are ever produced;
9. same-date revision handling for historical source observations;
10. methodology-version transitions and reproducibility requirements;
11. prohibition on copying the restored 32 rows forward as fresh authority;
12. prohibition on cross-asset ranking, portfolio allocation, or automatic execution semantics in R1.

## Fail-closed requirements

The design audit must fail closed if the current native cycle, Regime Probability V1, Risk V1, Recommendation Change V1, methodology registry, or persisted observation history does not satisfy its declared checks.

No statistically calibrated interval, probability, or error distribution may be claimed unless that calibration is actually implemented and certified.

## Decision vocabulary

The audit may emit only one of these design decisions:

- `AUTHORIZE_UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1_DESIGN`
- `DO_NOT_AUTHORIZE_UNCERTAINTY_ADJUSTED_V1_UNTIL_MISSING_AUTHORITY_IS_RESOLVED`

The next step after a PASS is a separate V1 rehearsal contract and builder, followed by production wiring/proof and only then formal 9-of-10 recognition.
