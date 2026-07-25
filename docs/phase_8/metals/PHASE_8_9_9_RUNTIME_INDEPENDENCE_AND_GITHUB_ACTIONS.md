# Phase 8.9.9 — Metals Runtime Independence and GitHub Actions Automation

## Objective

Move every production responsibility required for the Metals domain into the Universal Investment Platform (UIP) repository so the complete supported Metals cycle can run on GitHub-hosted Actions runners without access to `C:\Users\DevonLockard\metals` or any other workstation-local path.

## Current state

The certified UIP Metals cycle still accepts a standalone `metals_root` and uses the legacy folder for:

- native Metals exports;
- the standalone DuckDB database;
- adapter package generation;
- transactional import inputs;
- portions of readiness and parity verification.

The repository also contains a scheduled GitHub Actions workflow, but its current scheduled job runs only the bounded UIP provider-check scheduler. It does not execute the complete Metals production cycle.

## Target architecture

```text
GitHub Actions schedule / manual dispatch
                |
                v
UIP-native Metals collectors
                |
                v
UIP-native raw and normalized persistence
                |
                v
UIP-native forecast, decision, risk, and vehicle surfaces
                |
                v
UIP package generation and transactional import
                |
                v
Readiness, visibility, outcome, and constraint publication
                |
                v
Artifacts + durable PostgreSQL operational evidence
```

No supported production stage may require a path outside the checked-out UIP repository or a secret stored only on a workstation.

## Workstreams

### 8.9.9.1 Dependency inventory and migration contract

- Register every production dependency on the standalone Metals project.
- Classify each dependency as migrate, replace, freeze as historical evidence, or retire.
- Record source module, UIP destination, required inputs, output contract, persistence target, and validation evidence.
- Fail certification while any required dependency remains unclassified.

### 8.9.9.2 UIP-native Metals persistence

- Replace production reads from `data/metals_intelligence.duckdb` with UIP-owned persistence.
- Use PostgreSQL for durable automated environments and a supported local backend for development/tests.
- Preserve lineage, data-as-of timestamps, checksums, package IDs, import IDs, and model-version evidence.
- Do not commit generated databases or mutable production datasets to Git.

### 8.9.9.3 UIP-native collection and transformation

- Move or rebuild required official-provider collectors inside UIP.
- Preserve World Bank and EIA benchmark authority and existing provider health behavior.
- Preserve daily vehicle collection, metadata, freshness, and divergence contracts.
- Store all API credentials as GitHub environment/repository secrets.

### 8.9.9.4 UIP-native model and decision execution

- Move required Metals-specific forecasting, regime, uncertainty, recommendation, risk, and reporting logic into UIP-owned modules.
- Reuse universal forecasting, validation, decision, allocation, and audit capabilities rather than duplicating them.
- Preserve registered methodology and parity evidence.

### 8.9.9.5 Standalone-free package and readiness cycle

- Replace `--metals-root` with UIP-native inputs for the supported production path.
- Keep any legacy-root flags only in explicit migration/audit commands, never in the canonical production cycle.
- Add a strict runtime-independence gate that fails if production commands reference an external Metals root.
- Run all Metals publications from the same canonical cycle.

### 8.9.9.6 GitHub Actions production automation

- Add a dedicated Metals workflow with `schedule` and `workflow_dispatch` triggers.
- Run on a GitHub-hosted Ubuntu runner.
- Validate required secrets before execution.
- Apply concurrency control so Metals cycles cannot overlap.
- Persist durable run evidence to PostgreSQL.
- Upload bounded diagnostic artifacts even on failure.
- Return a nonzero result when any required stage fails.

### 8.9.9.7 Cutover, observation, and retirement

- Execute a UIP-native live cycle without the standalone folder.
- Rename or temporarily remove the local legacy folder and repeat the cycle to prove independence.
- Begin the retirement observation window at the verified cutover time.
- Archive the standalone project, record SHA-256, document recovery, and verify zero post-cutover access.
- Run the Phase 8.9.8 strict verifier against actual evidence.

### 8.9.9.8 Final Phase 8.9 certification

- Require all focused, production, and full-platform tests to pass.
- Require GitHub Actions manual-dispatch success.
- Require at least one scheduled run success.
- Require strict live retirement verification `PASS`.
- Create `uiip-phase-8.9-certified` only after all gates pass.
- Close Issue #12 only after the final tag is pushed.

## GitHub Actions secret contract

The final workflow may require the following, depending on provider configuration:

- `UIIP_DATABASE_URL`
- `UIIP_FRED_API_KEY`
- `UIIP_ALPHA_VANTAGE_API_KEY`
- additional official-provider credentials only when a provider actually requires them

Secrets must never be written to cycle evidence, uploaded artifacts, logs, or committed configuration.

## Repository and artifact policy

Commit:

- source code;
- schemas and migrations;
- deterministic fixtures;
- configuration without credentials;
- tests;
- documentation;
- small methodology and registry records.

Do not commit:

- mutable production databases;
- API responses containing restricted data;
- secrets;
- large generated exports;
- complete operational history that belongs in PostgreSQL or Actions artifacts.

## Definition of done

Phase 8.9.9 is complete only when:

1. the complete Metals production cycle runs from a fresh GitHub Actions checkout;
2. no production stage reads or executes `C:\Users\DevonLockard\metals`;
3. all required state is reproducible from UIP code, supported durable persistence, and configured secrets;
4. cycle evidence, package lineage, readiness, visibility, outcomes, and constraints are produced;
5. manual and scheduled GitHub Actions runs pass;
6. the standalone system passes strict live retirement verification;
7. the final Phase 8.9 certification tag is created.
