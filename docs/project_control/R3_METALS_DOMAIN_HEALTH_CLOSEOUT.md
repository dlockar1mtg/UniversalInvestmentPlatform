# UIP R3 Metals — Output Rationality and Domain Health Closeout

## Disposition

`UIP_R3_METALS_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_PASS`

Metals is certified healthy and rational for UIP presentation under native Metals semantics. This closeout does not create cross-asset ranking, universal allocation policy, or automatic purchase authority.

## Authoritative state

- Branch: `phase-uip-r3-metals-domain-health`
- Governed pre-closeout implementation head: `43443aa94a08d8bbea27d0b889a8a37120eda332`
- Authoritative UIP database SHA-256 after governed repairs: `22320b879c1737cec054b91db0abf147ac5f18e0f9d395031c0f4524d3eeca59`
- Current Metals package: `metals-20260728T182311Z-5da5336b`
- Current Metals import: `14cfce16-f806-4db1-9303-210de844c194`

## Current certified Metals surface

- `asset_master_current`: 16 rows
- `forecasts_current`: 16 rows
- `recommendations_current`: 12 rows
- `risk_metrics_current`: 11 rows
- health: `HEALTHY`
- registry: `ACTIVE`
- last import: `IMPORTED`
- warnings: 0
- errors: 0

## R3 defects discovered and repaired

### 1. Metals vehicle identity case transition

Legacy package history used lower-case vehicle IDs such as `metals:vehicle:gld`, while later adapter output used canonical upper-case ticker suffixes such as `metals:vehicle:GLD`. Because universal current views partitioned on `universal_asset_id`, both historical identities could survive as current rows.

Migration 007 reconciles Metals vehicle current-state identity case without deleting historical rows or globally changing identity semantics for other domains.

Certified result:

- stale Metals current rows: 0
- duplicate Metals platform-asset groups: 0
- legacy history deleted: false

### 2. Historical forecast alias loss

The July 28 package contained authoritative forecast fields including `expected_total_return`, `probability_positive_return`, and `forecast_confidence`, but the July importer predated the contract-to-history alias translation later introduced by commit `a2f0e1939e60f909332b0443db8cb0be5396abf8`.

A governed recovery restored only values already present in the exact checksum-verified certified package into the matching historical forecast rows.

Certified result:

- expected returns recovered: 16/16
- positive-return probabilities recovered: 16/16
- forecast confidence recovered: 16/16
- point forecast synthesized: false
- forecast bounds synthesized: false
- scenario synthesized: false
- source refresh executed: false
- native Metals model rerun: false

## Final rationality review

Final read-only review completed with:

- failure count: 0
- warning count: 0
- portfolio-level risk semantics accepted
- vehicle allocation weight sum: effectively 100%
- commodity opportunity weights treated as a separate native surface and not combined with vehicle allocation
- all current forecast expected-return, positive-probability, and confidence authorities present
- missing point forecasts, bounds, and scenarios preserved as NULL because no source authority exists

Selected 24-month native forecast observations:

| Metal | Expected return | Positive-return probability | Confidence |
| --- | ---: | ---: | ---: |
| Gold | 28.02% | 92.44% | 42.98 |
| Silver | 36.35% | 80.56% | 16.95 |
| Platinum | 20.39% | 71.90% | 44.31 |
| Copper | 12.59% | 70.07% | 61.17 |

These figures remain native Metals evidence, not universal cross-domain scores or guarantees of future performance.

## Production Cycle #23 disposition

The exact original root cause of historical Metals Production Cycle #23 is not available in preserved evidence and must not be invented.

Final classification:

`HISTORICAL_FAILURE_EXACT_ROOT_CAUSE_UNRESOLVED_NO_CURRENT_DOMAIN_HEALTH_BLOCKER`

Supporting basis:

- later certified Metals production/rehearsal evidence passed;
- current Metals domain health is clean;
- current package/import lineage is coherent;
- final R3 rationality review passed with zero failures and zero warnings;
- the two defects discovered by R3 were UIP integration/history defects, not evidence of persistent native source or model failure.

Therefore Cycle #23 is compatible with a transient operational/infrastructure failure, but that is not asserted as a proven cause. No rerun is required solely to retroactively determine its cause.

## Governance restrictions preserved

- native Metals semantics reinterpreted: false
- cross-asset ranking authorized: false
- cross-domain allocation policy created: false
- automatic purchase execution authorized: false
- missing authority synthesized: false

## Permanent evidence

`docs/project_control/generated/r3_metals_domain_health/metals_r3_domain_health_certification.json`

## Next gate

`UIP_R3_MTG_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW`
