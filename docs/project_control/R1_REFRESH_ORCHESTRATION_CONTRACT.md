# UIP R1 Refresh and Orchestration Contract

## Purpose

R1 defines how UIP coordinates refreshed MTG, Metals, and Crypto intelligence without taking ownership of native source-domain modeling semantics.

R1 does not certify fresh outputs. R2 performs the real refreshed-data rehearsal. R3 then determines whether those fresh outputs are internally coherent, plausible, semantically preserved, and suitable as inputs to later UIP decision logic.

## Global orchestration rules

- Source domains remain authoritative for native collection, modeling, ranking, risk, forecasting, and recommendation semantics.
- UIP may trigger a source-owned remote workflow for an external domain, but UIP must not directly invoke that domain's collectors or production internals.
- Metals remains a UIP-native domain and may use its canonical native production entrypoint.
- A failed cycle preserves the latest certified UIP state.
- Partial activation is not authorized.
- Missing authority remains missing; it is not synthesized as zero, WAIT, worst rank, or another default.
- Current population sizes are evidence, not permanent universe constants.
- Every activated package must retain package and row lineage.
- R1 does not authorize cross-asset ranking, allocation policy, or automatic execution.

Canonical machine-readable authority:

`config/orchestration/r1_domain_refresh_contracts.json`

Typed fail-closed interface:

`foundation/orchestration/refresh_contracts.py`

## Domain refresh boundaries

### MTG

Producer repository:

`dlockar1mtg/mtg-investment-terminal`

Source-owned remote trigger:

`.github/workflows/mtg-marketplace-production.yml`

R1 requests a live source-domain run through workflow dispatch with `live_execution=true`. The MTG workflow owns marketplace collection, certification, decisioning, hosted UIP delivery, and source-refresh handoff evidence. UIP does not call eBay, TCGCSV, Secret Lair collectors, marketplace runners, or other MTG production internals directly.

Declared live delivery:

`data/operations/mtg_uip_delivery/latest`

R2 requirement:

The current hosted live delivery must be proven compatible with the certified MTG native-authority boundary before activation. This is intentionally marked `R2_COMPATIBILITY_PROOF_REQUIRED` rather than assumed compatible. If an adapter is required, it must be lossless and must not flatten Collector, Pre-Collector, or Secret Lair semantics.

### Metals

Ownership:

`uip_native_domain`

Canonical native entrypoint:

`scripts/run_metals_production_cycle.py`

The cycle already owns native export, transactional import, readiness evaluation, and durable operations evidence. R2 must run a real fresh cycle and prove that the current native package still satisfies the certified Metals A1 contract.

The refresh must preserve the rules that commodity benchmarks are not direct investment vehicles, unsupported authority is not synthesized, missing forecast authority remains NULL, and native recommendation semantics remain authoritative.

### Crypto

Producer repository:

`dlockar1mtg/CryptoIntelligencePlatform`

Source-owned remote trigger:

`.github/workflows/crypto-production-cycle.yml`

R1 requests `full_refresh=true`. The Crypto repository owns provider refresh, Modules 1–44, hosted database persistence, readiness, and UIP delivery. UIP must not mutate the Crypto source database or substitute its own model logic.

UIP consumer entrypoint:

`scripts/import_certified_crypto_package.py`

R2 must prove a fresh package imports with the certified mappings intact, including `WAIT -> watch`, `AVOID -> sell`, unknown-label fail-closed behavior, and absence of holdings remaining absence rather than becoming zero-valued holdings.

## Required cycle evidence

Each R2 domain rehearsal must capture at minimum:

- domain identity and source/native boundary;
- source commit or version;
- refresh start/completion timestamps;
- data-as-of evidence;
- producer run ID;
- package ID and manifest hash or equivalent package-integrity evidence;
- dataset coverage;
- native status and freshness status;
- warnings and errors;
- whether data collection occurred;
- whether native model execution occurred;
- UIP import status/import ID;
- lineage status.

## Failure behavior

If a producer refresh, package validation, import, semantic reconciliation, or lineage gate fails:

1. do not partially activate the new cycle;
2. preserve the prior certified state;
3. retain the failed-cycle evidence;
4. route the defect to the owning repository;
5. do not compensate by changing native semantics in UIP.

## R2 gate

`UIP_R2_REFRESHED_DATA_REHEARSAL`

R2 proves the orchestration contract against real fresh MTG, Metals, and Crypto output. Production database activation is not required for the rehearsal; disposable UIP import environments are preferred until all gates pass.

## R3 gate — output rationality and domain health

`UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW`

R3 is a hard rationale/health gate after R2 and before E1 or dashboard decision logic.

R3 does not create a universal rank or allocation model. It asks whether the fresh native outputs themselves deserve to be trusted as inputs.

Required review dimensions:

1. freshness and completeness;
2. native self-consistency;
3. distribution and outliers;
4. change-from-prior plausibility;
5. UIP semantic preservation;
6. decision readiness;
7. investigation routing.

Allowed findings:

- `PASS`
- `PASS_WITH_GOVERNED_GAPS`
- `REVIEW`
- `DOMAIN_INVESTIGATION_REQUIRED`

A suspicious result must identify the domain, affected assets/surfaces, observed anomaly, native authority needed to resolve it, and whether that domain should be excluded from later UIP decision logic until reviewed.

## Sequence

`R1 contracts -> R2 real fresh rehearsal -> R3 output rationality/domain health -> E1 Stocks/ETF extension -> dashboard decision logic`

No later UIP decision layer should treat MTG, Metals, or Crypto as decision-ready merely because a package imported successfully.
