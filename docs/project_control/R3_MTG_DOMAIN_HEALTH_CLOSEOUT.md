# UIP R3 MTG — Domain Health Closeout

## Status

`UIP_R3_MTG_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_PASS`

The MTG R3 lane is certified complete. The authoritative UIP database now carries the certified 968-row native MTG authority, while recovery-era generic uppercase `MTG` current analytical surfaces are excluded from current authority and preserved in history.

## Authoritative database

Final certified SHA-256:

`df7406361639e4b165afb8007f97feca60242e91d290c58ae521e423d82578cc`

Pre-native-cutover backup SHA-256:

`22320b879c1737cec054b91db0abf147ac5f18e0f9d395031c0f4524d3eeca59`

Pre-migration-009 backup SHA-256:

`e4320a722e2feebfd99bc05b6bd9aa7189a9f063e229b3d04045f6835d374470`

The final read-only certification modified none of these files.

## Native MTG authority

Current rows: `968`

History rows: `968`

Lane counts:

- Collector V1: `50`
- Pre-Collector V1: `131`
- Secret Lair V1.1: `787`

Population permanence semantics:

- Collector: snapshot population not permanent
- Pre-Collector: all 131 canonical disposition rows permanent
- Secret Lair: dynamic population; snapshot population not permanent
- full MTG snapshot: not a permanent universe

Rank structure:

- Collector: 49 ranked rows / 49 distinct ranks
- Pre-Collector: 95 ranked rows / 95 distinct ranks
- Secret Lair: 787 ranked rows / 704 governed production rank groups

The Secret Lair tied-rank structure is certified native behavior, not a ranking defect.

## Secret Lair execution boundary

BUY candidates: `88`

All 88 remain model-qualified entry candidates that require manual execution-price checking.

Execution-ready purchase authority: `false`

Automatic purchase execution: `false`

## Native semantic integrity

Certified null profile:

- current price NULL: 10
- forecast price NULL: 37
- forecast return NULL: 37
- native rank NULL: 37
- native purchase status NULL: 37
- purchase semantic NULL: 37

Current-price authority mismatches: `0`

Forecast-authority mismatches: `0`

Maximum forecast price/return arithmetic residual: `0.0`

Native lineage-missing rows: `0`

Native current authority belongs to one package/import group:

- package: `mtg-v1-native-authority-aa363cd474ae6b846588bb4a`
- import: `84bcb0f3-ed3f-4d09-9957-22f8b3e236e9`

## Legacy recovery-era authority

Legacy uppercase `MTG` history remains preserved exactly:

- asset history: 7,987
- forecast history: 4,286
- recommendation history: 5,117
- risk history: 2,282
- platform-status history: 7

Legacy import ledger remains preserved exactly:

- packages: 7
- imports: 7
- datasets: 30
- errors: 0

No legacy history was deleted or rewritten.

Generic legacy MTG analytical current authority after cutover:

- asset current: 0
- forecast current: 0
- recommendation current: 0
- risk current: 0

Current MTG platform status is canonical lower-case `mtg` using adapter `mtg-v1-native-authority-binding-1.0.0`.

## Production cutover correction

Migration `008_mtg_native_authority_current_cutover.sql` establishes the authority boundary:

- legacy generic MTG remains visible until native authority exists;
- after successful native activation, legacy generic MTG analytical rows cease to be current;
- all legacy history remains preserved;
- current platform status reconciles `MTG` and `mtg` case-insensitively.

The R3 activation wrapper `foundation/integrations/mtg/r3_native_activation.py` imports the certified 968 native rows plus one canonical platform-status row transactionally.

## Forecast-current determinism correction

The production cutover exposed a pre-existing nondeterministic tie in `forecasts_current` for five Crypto forecast keys. Underlying non-MTG history and forecast semantics did not change; only `_source_row_number` differed between equally recent duplicate lineage rows.

Migration `009_forecasts_current_deterministic_tie_breaker.sql` adds stable lineage tie-breakers after the established recency ordering.

Certified deterministic forecast-current fingerprint:

`4bb256b40df170060e503273b0ee9cb117b94a9be3252a8c82502fc2d134e17b`

Repeated governed view rebuilds produced the same fingerprint.

Non-MTG forecast-current semantic rows: `136`

Non-MTG forecast semantics changed: `false`

Non-MTG history changed: `false`

## Governance boundaries retained

- no universal cross-asset ranking authorized
- no cross-domain allocation policy created
- no automatic purchase execution
- no execution-ready MTG purchase authority
- no native MTG semantic reinterpretation
- no synthetic replacement for missing values
- no MTG native-model rerun
- no unnecessary MTG source refresh rerun

## Permanent evidence

`docs/project_control/generated/r3_mtg_domain_health/mtg_r3_domain_health_certification.json`

## Disposition

`UIP_R3_MTG_CERTIFIED_COMPLETE`

## Next authorized gate

`UIP_R3_CROSS_DOMAIN_RECONCILIATION_AND_CLOSEOUT`

R3 cross-domain reconciliation may compare platform health, lineage completeness, current-authority integrity, and operational readiness. It may not introduce universal asset ranking, cross-domain investment weighting, or automatic execution without separate governance.
