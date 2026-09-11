# UIP Native Metals Risk V1 — Multi-source same-date reconciliation

## Purpose

`UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1` is keyed by `(ticker, observation_date, source)`. Therefore a governed vehicle can legitimately have more than one source row for the same observation date.

Risk V1 consumes a single daily close series. The builder must not silently choose between conflicting source values.

## Frozen rule

For each `(universal_asset_id, observation_date)` group:

1. all rows must remain vehicle rows under `UIP_NATIVE_METALS_VEHICLE_OBSERVATIONS_V1` with `UNADJUSTED_CLOSE` semantics;
2. all rows must map to the same ticker;
3. all `close_usd` values must be positive finite numbers;
4. close values are considered equivalent only when every value is `math.isclose()` to the first value using `rel_tol=1e-9` and `abs_tol=1e-8`;
5. when equivalent, the group is deterministically collapsed to one canonical observation for risk calculation;
6. when any same-date close conflicts beyond those tolerances, Risk V1 fails closed.

No source-priority ranking is introduced. The canonical row exists only to provide one price per date after equality has been established. Source metadata is not used to prefer one market value over another.

## Evidence

The Risk V1 manifest records:

- raw source-history row count;
- canonical unique-date observation count;
- same-date duplicate source rows collapsed;
- reconciliation policy and numerical tolerances.

This does not mutate the certified native history family and does not claim legacy equivalence.
