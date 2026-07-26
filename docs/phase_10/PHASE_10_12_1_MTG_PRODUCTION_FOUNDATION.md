# Phase 10.12.1 — MTG Production Foundation

## Objective

Establish the UIP-owned MTG orchestration boundary without changing or invoking the Crypto production deployment, without changing the Metals workflow, and without scheduling MTG production.

## Isolation guarantees

- The workflow is manual-dispatch only.
- No `schedule` trigger exists.
- `UIP_MTG_LIVE_EXECUTION` is fixed to `false` in the foundation workflow.
- The workflow does not check out `CryptoIntelligencePlatform`.
- The workflow does not check out or execute the MTG source repository.
- The workflow does not invoke Metals.
- No shared multi-domain controller is introduced in this phase.
- No GitHub environment or production secrets are required.

## Components

- `config/mtg/production.json` defines the fail-closed control contract.
- `foundation/production/mtg/readiness.py` evaluates source, configuration, and live-gate readiness.
- `foundation/production/mtg/cycle.py` publishes structured safe-hold evidence.
- `scripts/run_mtg_production_cycle.py` provides the UIP command entry point.
- `tests/production/test_mtg_production_cycle.py` certifies fail-closed behavior.
- `.github/workflows/mtg-production-foundation.yml` validates the foundation manually.

## Current execution behavior

With the live gate disabled, the runner exits successfully with `SAFE_HOLD` and publishes:

`data/operations/mtg/production_cycle/latest.json`

Opening the live gate does not run marketplace collection or source code. It returns `NOT_IMPLEMENTED` until the live pipeline is added and separately certified.

## Deferred work

The following remain intentionally deferred until Crypto staging is complete and the MTG source execution contract is reviewed:

- MTG source repository checkout
- eBay or TCGplayer API calls
- Marketplace observation persistence
- MTG export and UIP import execution
- GitHub Actions environments and secrets
- Scheduled triggers
- Shared Metals/Crypto/MTG controller
- Cross-domain production health aggregation
