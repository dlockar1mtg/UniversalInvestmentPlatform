# UIP Metals Regime Probability V1

## Status

Rehearsal candidate only. This authority is not production-certified and does not advance the rich publication contract until rehearsal, production wiring/proof, and formal recognition all pass.

## Authority boundary

`UIP_NATIVE_METALS_REGIME_PROBABILITY_V1` is a new, explicitly non-legacy-equivalent commodity-level authority. It consumes only the current certified UIP-native Metals cycle and the versioned Metals methodology registry. It does not copy the restored 12 legacy regime-probability rows, does not consume vehicle Risk V1 as commodity probability evidence, and does not project commodity regimes to vehicles.

## Regime taxonomy

V1 uses exactly three labels:

- `POSITIVE_TREND`
- `NEUTRAL_OR_MIXED`
- `NEGATIVE_TREND`

The taxonomy is intentionally smaller and differently named than the restored legacy taxonomy. Legacy labels remain historical evidence only.

## Probability semantics

The `probability` field is **descriptive normalized regime support**, not a statistically calibrated probability estimate. V1 must not make calibration claims.

For each commodity, the current certified native cycle must provide identical `benchmark_momentum`, `vehicle_confirmation`, confidence, and as-of state across its certified horizons. The regime output is therefore horizon-invariant in V1. If those source inputs diverge across horizons, V1 fails closed.

The directional signal is:

`(0.45 * benchmark_momentum + 0.35 * vehicle_confirmation) / 0.80`

The positive neutral boundary is the methodology registry's `buy_min_return`; the negative neutral boundary is the absolute value of `hold_min_return`.

For a positive signal, directional support grows linearly from zero at 0 to one at the positive boundary. For a negative signal, negative support grows linearly using the negative boundary. Directional support is then multiplied by the current native-cycle confidence. All remaining mass is assigned to `NEUTRAL_OR_MIXED`. The three values must sum to one within the governed tolerance.

This method deliberately treats lower confidence as greater neutral/uncertain support rather than pretending to have a calibrated posterior distribution.

## Evidence requirements

Each commodity must have at least two benchmark observations and at least one confirming vehicle series in the current native-cycle component state. Missing evidence fails closed; V1 does not impute probabilities.

## Output grain

One row is emitted per commodity per regime. With the current certified nine-commodity universe and three-label taxonomy, the present rehearsal expectation is 27 rows. The authority is commodity-level only.

## Safety and publication boundary

The rehearsal builder performs no source collection, PostgreSQL writes, publication staging, or publication activation. It does not alter the central publisher. Production certification requires a separate wiring change, successful normal Metals Production Cycle proof, and formal rich-contract recognition.
