# Universal Investment Platform — Start Here

## Purpose

This file is the mandatory entry point for every new UIP development, recovery, integration, dashboard, infrastructure, or certification session.

Before making changes, read the Project Control Center in this order:

1. `00_START_HERE.md`
2. `01_PROJECT_CHARTER.md`
3. `02_SYSTEM_OF_RECORD.md`
4. `03_ARCHITECTURE_AND_DATA_FLOW.md`
5. `04_ACTIVE_ROADMAP.md`
6. `05_PROJECT_STATE.md`
7. `06_CHANGE_LEDGER.md`
8. `UIP_DATA_DICTIONARY.md`, when present
9. Generated database schema artifacts, when present

## Required startup verification

Every new UIP session must verify and summarize:

- current roadmap phase and milestone;
- active branch;
- authoritative stable commit;
- last certified state;
- next authorized action;
- open risks and blockers;
- protected local-only resources;
- relevant repository permissions;
- whether the proposed work is consistent with the latest active change-ledger entry.

Repository evidence controls implementation truth. Chat history is supporting context only.

## Current authority model

### Project direction and governance

Latest active change-ledger entry  
→ active roadmap  
→ approved architecture  
→ system-of-record policy  
→ project charter

### Implementation truth

Certified repository commit  
→ ordered migrations  
→ generated schema evidence  
→ certification evidence

### Production-data truth

The authority hierarchy defined in `02_SYSTEM_OF_RECORD.md`.

A ledger entry may change policy prospectively, but it cannot rewrite historical production facts or make uncertified code authoritative.

## Mandatory operating rules

- Preserve recovery evidence before changing recovered work.
- Never merge recovered code solely because it exists.
- Never delete protected local resources without classification, backup, and Devon’s approval.
- Never commit secrets or personal financial snapshots.
- Never treat local paths as final production architecture.
- Never bypass migration, contract, lineage, transaction, backup, or certification controls.
- Correct conflicts at the authoritative source rather than patching downstream silently.
- Keep failed or superseded evidence traceable.
- Use the latest certified state when a new run fails.

## Current startup state

Recovery classification:

`RECOVERED_AND_READY_FOR_INTEGRATION`

Current execution state:

`MULTI_BRANCH_RECONCILIATION_REQUIRED_BEFORE_INTEGRATION`

Current phase:

`Phase A — Project control and recovery stabilization`

Current stable baseline:

`7bd8d0e3cb0f8cfa61208a0950cb7c3f51c7b5e8`

Baseline evidence:

`1,201 tests passed`

Recovered historical-performance commit:

`c6606d0b31add9fb356db8c3c15bc44af3b8175f`

Recovered targeted-test evidence:

`4 tests failed`

Current next authorized action:

`RECONSTRUCT_MTG_HISTORICAL_PERFORMANCE`

The controlled MTG reconciliation branch was created from `df8e796`, pushed to GitHub, and verified to exclude the defective Phase 10.12 recovery implementation. The next action is controlled reconstruction of MTG historical performance.

## Session summary template

At the beginning of each new session, provide:

```text
UIP startup verification

Roadmap phase:
Current milestone:
Active branch:
Stable baseline:
Last certification:
Next authorized action:
Open blockers:
Protected local resources:
Relevant active change IDs:
```

## Governing principle

> UIP development must begin from durable repository-backed governance, verified implementation evidence, and an explicit authorized action. No future chat, branch, script, or deployment may silently redefine the project.
