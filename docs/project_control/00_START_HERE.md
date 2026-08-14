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

`RECOVERED_AND_READY_FOR_GOVERNED_DOMAIN_INTEGRATION`

Current execution state:

`CERTIFIED_DOMAIN_INTEGRATION_SEQUENCE_ACTIVE`

Current phase:

`Certified domain integration`

Current governed main baseline:

`4dfc98df10dcd1cf59db075b41cce95c237956b2`

Historical recovery baseline:

`7bd8d0e3cb0f8cfa61208a0950cb7c3f51c7b5e8`

Historical recovery baseline evidence:

`1,201 tests passed`

Recovered historical-performance commit:

`c6606d0b31add9fb356db8c3c15bc44af3b8175f`

Recovered targeted-test evidence:

`4 tests failed`

Current next authorized action:

`UIP_CRYPTO_A0_A1_DOMAIN_BINDING`

The controlled MTG reconciliation branch and its recovery evidence remain preserved. Under `UIP-CHG-2026-026`, `UIP-CHG-2026-027`, and `UIP-CHG-2026-028`, UIP-MTG-A2 is certified complete and the active next action is UIP-METALS-A0/A1 domain binding. The former historical-performance reconstruction path is no longer the active prerequisite, and certified MTG source-domain work must not be reopened without a verified governance defect.

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
