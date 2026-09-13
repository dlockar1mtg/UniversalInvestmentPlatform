# Metals Regime Probability Authority Design V1

## Purpose

Determine whether UIP has enough governed native evidence to design a new, explicitly non-legacy-equivalent Metals regime-probability authority.

This gate is read-only. It does not create regime-probability rows, collect new source data, write to PostgreSQL, stage a publication, activate a publication, or modify the central publisher.

## Current recovery position

Metals rich publication recovery is formally 7 of 10 certified families. The remaining uncertified families are `regime_probability`, `uncertainty_adjusted`, and `tactical_state`.

The restored rich publication contains 12 `metals_regime_probability` rows. Those rows are historical evidence only. Their count, taxonomy, formulas, and lineage must not be copied or inferred into a new authority without explicit governance.

## Candidate evidence available to the design audit

The audit may inspect only governed evidence already available to UIP:

- restored rich-publication lineage and payload shape for `metals_regime_probability`;
- the latest successful UIP-native Metals production artifact;
- the current native forecast state from `native_cycle/latest.json`;
- the certified UIP-native model-component authority;
- the certified UIP-native Risk V1 authority;
- the versioned Metals methodology registry;
- persisted benchmark and vehicle observation history through read-only PostgreSQL queries.

## Candidate boundary

The candidate V1 boundary is `BENCHMARK_COMMODITY_ASSET_ONLY`.

This boundary does **not** authorize projecting vehicle-only Risk V1 measurements directly into commodity-level regime probabilities. Any use of vehicle evidence must be explicitly defined by the future regime methodology.

## Required semantics before a builder may be authorized

A later implementation must explicitly govern all of the following:

1. canonical regime label taxonomy and exact label count;
2. probability output schema and record grain;
3. probability normalization and fail-closed tolerance for sum-to-one;
4. exact classifier inputs and versioned transformations;
5. whether regime probabilities are horizon-independent or horizon-specific;
6. historical as-of cadence and temporal cutoff rules if probabilities are reconstructed historically;
7. same-day multi-source revision handling;
8. whether values are descriptive normalized scores or statistically calibrated probabilities;
9. minimum evidence/completeness requirements and unavailable-state behavior;
10. methodology-version transition policy;
11. prohibition on copying restored legacy rows forward as fresh authority;
12. prohibition on ungoverned vehicle-to-commodity projection.

## Safety requirements

Any future V1 authority must:

- use a new UIP-native authority identifier;
- set `legacy_equivalent=false`;
- fail closed when required evidence or semantics are missing;
- preserve source and methodology lineage;
- avoid claiming statistical calibration unless calibration is actually implemented and certified;
- leave the central production publication gate closed until the family is separately rehearsed, production-wired, production-proven, and formally recognized.

## Design-audit decision

The design audit may return `AUTHORIZE_UIP_NATIVE_METALS_REGIME_PROBABILITY_V1_DESIGN` only if the restored family is observable as evidence and the current UIP-native forecast, model-component, risk, methodology, and historical observation authorities are all present and internally coherent.

Authorization at this stage means only that UIP has enough governed evidence to design the V1 contract. It does not authorize regime-probability production output.
