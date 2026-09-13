# Metals Recommendation Change Authority Design V1

## Purpose

Determine whether UIP has enough governed native evidence to design a new, explicitly non-legacy-equivalent Metals recommendation-change authority.

This gate is read-only. It does not create recommendation-change rows, stage a publication, activate a publication, or modify the central publisher.

## Evidence boundary

The audit may use:

- restored `metals_recommendation_change` presentation rows only as historical schema evidence;
- the latest successful UIP-native Metals production artifact for current recommendation state;
- `config/metals/model_methodology_registry.json` for the governed recommendation policy;
- read-only persisted UIP-owned benchmark and vehicle observations to determine whether historical states are reconstructible.

Restored recommendation-change rows must never be copied forward as fresh authority.

## Candidate authority boundary

The candidate V1 boundary is `BENCHMARK_COMMODITY_ASSET_ONLY`.

Current UIP-native recommendations are issued by the benchmark commodity forecast cycle. There is no governed authority to project those recommendations onto ETF/vehicle assets. Any future vehicle recommendation-change authority requires a separate design.

## Required design decision

Exactly one decision is valid:

- `AUTHORIZE_UIP_NATIVE_METALS_RECOMMENDATION_CHANGE_V1_DESIGN`
- `DO_NOT_AUTHORIZE_RECOMMENDATION_CHANGE_V1_UNTIL_MISSING_AUTHORITY_IS_RESOLVED`

Authorization here permits only semantic design work. It does not authorize a builder, production wiring, formal rich-family recognition, publication staging, or activation.

## Semantics that must be frozen before a builder

A later builder proposal must explicitly govern:

1. canonical output schema;
2. historical as-of cadence and cutoff rule;
3. event grain, with a preference for one row per commodity transition rather than per forecast horizon;
4. first-observation behavior;
5. same-day revision ordering;
6. methodology-version transitions during historical reconstruction;
7. whether unchanged repeated states are omitted;
8. explicit prohibition on commodity-to-vehicle recommendation projection.

## Safety invariants

- PostgreSQL access is read-only for this audit.
- No production rows are written.
- No publication is staged or activated.
- `legacy_equivalent` remains false.
- Missing authority stays missing.
- The central rich publisher remains manual/paused.
