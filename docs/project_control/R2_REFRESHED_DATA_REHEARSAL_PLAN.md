# UIP R2 Refreshed-Data Rehearsal Plan

## Purpose

R2 proves the governed R1 refresh/orchestration contracts against real fresh MTG, Metals, and Crypto output before any production UIP activation.

R2 does not reinterpret native models, create cross-asset ranking, create allocation policy, or authorize automatic execution.

## Governing sequence

`R1 certified contracts -> R2 real fresh rehearsal -> R3 output rationality/domain health -> E1`

## Global rehearsal rules

- Use current source-domain production entrypoints only.
- External-domain collection and model execution remain source-owned.
- Metals remains UIP-native.
- Capture all 19 R1 cycle-evidence fields for every domain.
- Use disposable UIP state for import/compatibility proof.
- Preserve failed-cycle evidence and prior certified state.
- Do not partially activate a failed multi-domain rehearsal.
- Do not synthesize missing authority.
- Do not treat observed asset counts as permanent constants.

## MTG rehearsal

1. Trigger the source-owned `MTG Marketplace Production` workflow on MTG `main` with `live_execution=true`.
2. Require a successful source run and downloadable production evidence artifact.
3. Preserve the producer run ID, source commit, timestamps, package/delivery identity, warnings/errors, freshness and collection/model-execution evidence.
4. Prove the refreshed hosted delivery can be losslessly reconciled to the certified MTG native-authority interface.
5. Preserve Collector, Pre-Collector, and Secret Lair semantics; preserve missing authority; preserve Secret Lair dynamic-universe and manual-price-check rules.
6. Import only into disposable UIP state during R2.

MTG disposition remains `R2_COMPATIBILITY_PROOF_REQUIRED` until this proof passes.

## Metals rehearsal

1. Run the canonical current Metals production cycle with export and live providers enabled.
2. Capture cycle history, latest-success evidence, readiness status, operations status, package ID, data-as-of and warnings/errors.
3. Prove the fresh package still satisfies the certified Metals A1 semantic boundary.
4. Preserve noninvestable commodity benchmark semantics, NULL missing forecast authority, and native recommendations.
5. Use disposable UIP state for any rehearsal import/verification that could affect canonical state.

## Crypto rehearsal

1. Trigger the source-owned `Crypto Production Cycle` workflow on Crypto `main` with `full_refresh=true`.
2. Require successful readiness, production pipeline, hosted-database freshness, UIP delivery preparation, production tests and artifact upload.
3. Preserve source commit, producer run ID, timestamps, package identity, dataset coverage, warnings/errors and collection/model-execution evidence.
4. Import the fresh package into disposable UIP state.
5. Prove certified mappings remain intact: `WAIT -> watch`, `AVOID -> sell`, unknown labels fail closed, absent holdings remain absent, and UIP does not mutate the source database.

## Required evidence

Each domain rehearsal must populate the governed R2 evidence record with all fields defined in:

`config/orchestration/r2_rehearsal_evidence_template.json`

## Pass gate

R2 passes only when all three domains have:

- successful real refresh evidence;
- required 19-field evidence captured;
- package/integrity evidence captured;
- disposable UIP compatibility/import proof;
- lineage proof;
- no unauthorized semantic reinterpretation;
- no production UIP activation during rehearsal;
- no cross-asset ranking, allocation policy, or automatic execution created.

If any domain fails, R2 remains open and the failure is routed to the owning source/native project without compensating downstream.

## Next gate

`UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW`

R3 reviews the exact fresh R2 outputs for plausibility, self-consistency, outliers, change-from-prior behavior, semantic preservation, decision readiness, and investigation routing.
