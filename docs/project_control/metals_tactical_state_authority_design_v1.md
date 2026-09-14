# Metals Tactical State Authority Design V1 — Read-Only Gate

Status: DESIGN AUDIT ONLY

## Purpose

Determine whether UIP has enough governed native Metals evidence to design a new, explicitly non-legacy-equivalent tactical-state authority.

This gate is read-only. It does not create tactical-state rows, stage a publication, activate a publication, alter the central publisher, or authorize portfolio/allocation/execution behavior.

## Current recovery position

Metals rich publication recovery is formally 9 of 10 certified families. The only remaining uncertified family is `tactical_state`.

The restored rich publication contains 10 `tactical_state` rows. Those rows are historical evidence only. Their count, subject grain, action mappings, classifier behavior, and lineage must not be copied or inferred into a new authority without explicit governance.

## Evidence this audit may use

- current certified UIP-native Metals forecasts and governed recommendation vocabulary;
- certified `UIP_NATIVE_METALS_RECOMMENDATION_CHANGE_V1` commodity recommendation history;
- certified `UIP_NATIVE_METALS_REGIME_PROBABILITY_V1` descriptive regime context;
- certified `UIP_NATIVE_METALS_UNCERTAINTY_ADJUSTED_V1` commodity-horizon confidence haircut evidence;
- certified `UIP_NATIVE_METALS_RISK_V1` evidence while preserving its `VEHICLE_ONLY` boundary;
- persisted UIP-owned benchmark and vehicle observations, queried read-only;
- restored tactical-state rows only as historical schema/lineage evidence.

## Authorization boundary

A PASS authorizes only the design of a future `UIP_NATIVE_METALS_TACTICAL_STATE_V1` authority.

The candidate subject boundary is intentionally unresolved at the design-audit stage. Before any builder exists, governance must explicitly choose one of these patterns:

1. `BENCHMARK_COMMODITY_ASSET_ONLY`, using certified commodity recommendation/regime/uncertainty authorities;
2. `VEHICLE_ONLY`, using certified vehicle observation/risk authorities; or
3. separately versioned commodity and vehicle tactical-state authorities with no implicit projection between them.

A design PASS does not authorize production rows or recognition as family 10 of 10.

## Semantics that must be governed before a builder exists

The rehearsal contract must explicitly define:

1. canonical subject boundary and row grain;
2. canonical tactical-state taxonomy and exact meaning of every state;
3. whether tactical state is descriptive context or an action recommendation;
4. exact mapping, if any, from `STRONG_BUY / BUY / HOLD / REDUCE / AVOID` into tactical states;
5. whether Regime Probability V1 contributes, and how confidence double-counting is prevented;
6. whether Uncertainty Adjusted V1 contributes and the exact threshold semantics;
7. whether Risk V1 contributes; because Risk V1 is vehicle-only, any vehicle-to-commodity mapping requires separate explicit governance and must otherwise remain prohibited;
8. horizon policy: current state, selected horizon, multi-horizon consensus, or horizon-specific states;
9. minimum evidence thresholds and unavailable behavior; missing authority must remain missing rather than defaulting to `HOLD` or `WAIT`;
10. historical reconstruction rules if tactical-state history is ever produced;
11. same-date revision handling for historical source observations;
12. methodology-version transitions and reproducibility requirements;
13. prohibition on copying restored tactical-state rows, action mappings, or classifier outputs forward as fresh authority;
14. prohibition on cross-asset ranking, portfolio allocation, trade sizing, or automatic execution semantics in V1.

## Fail-closed requirements

The design audit must fail closed if the current native cycle, Regime Probability V1, Uncertainty Adjusted V1, Risk V1, Recommendation Change V1, methodology registry, or persisted observation history does not satisfy its declared checks.

Vehicle tactical context must never be presented as commodity tactical state unless a separately governed mapping is explicitly certified.

Missing state stays missing. The system may not translate unavailable tactical authority into `WAIT`, `HOLD`, zero, or any synthetic state.

## Decision vocabulary

The audit may emit only one of these design decisions:

- `AUTHORIZE_UIP_NATIVE_METALS_TACTICAL_STATE_V1_DESIGN`
- `DO_NOT_AUTHORIZE_TACTICAL_STATE_V1_UNTIL_MISSING_AUTHORITY_IS_RESOLVED`

The next step after a PASS is a separate V1 rehearsal contract and builder, followed by production wiring/proof and only then formal 10-of-10 recognition. Central publication remains paused/manual until that entire sequence is complete and the rich publication contract passes.
