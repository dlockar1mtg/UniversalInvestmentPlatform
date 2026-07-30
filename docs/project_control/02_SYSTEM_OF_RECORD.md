# Universal Investment Platform — System of Record

## Purpose

This document defines which system is authoritative for code, schemas, source data, certified packages, portfolio data, transactions, recommendations, and historical evidence.

## Repository ownership

Repositories are owned under `dlockar1mtg`.

- UIP: `dlockar1mtg/UniversalInvestmentPlatform`
- MTG: `dlockar1mtg/mtg-investment-terminal`
- Crypto: `dlockar1mtg/CryptoIntelligencePlatform`
- Metals: native subsystem inside UIP; no separate Metals repository

## Authority hierarchy

### Source-domain authority

The source production database or governed native state is authoritative for source-domain facts.

### Certified publication authority

A certified package is the authoritative immutable snapshot of what a source domain published for a specific run.

### UIP canonical authority

The UIP production database is authoritative for:

- imported universal records;
- portfolio ledger;
- derived holdings;
- cross-domain analytics;
- recommendation state;
- portfolio-level history.

### GitHub authority

GitHub is authoritative for:

- committed implementation;
- ordered migrations;
- schemas and contracts;
- tests;
- workflow definitions;
- deployment definitions;
- documentation;
- certification code;
- release and tag history.

GitHub is not the production-data authority.

## Secrets

GitHub secrets and environment secrets may be used. Secret values must never be committed.

## Production databases

Production persistence is required for:

- UIP;
- Crypto;
- MTG.

Metals uses a dedicated native database only when its verified runtime design requires one. Repository inventory has identified native Metals operational storage that must be cataloged before final architecture certification.

## Schema authority

The authoritative schema chain is:

1. ordered migration manifest;
2. ordered migration files;
3. generated schema introspection catalog;
4. semantic data dictionary.

An initialization process may create a fresh database only by applying the authoritative migration chain.

Editing an original initialization file alone is not an acceptable production migration strategy.

## Universal package requirements

Every certified source delivery must include:

- contract version;
- package and run identifiers;
- generated timestamp;
- file manifest and hashes;
- validation status;
- complete declared asset coverage;
- `asset_coverage.csv` or an approved equivalent coverage declaration;
- required source lineage.

All authoritative assets must remain represented. Unavailable analytics must use nulls, status, confidence, eligibility, or suppression reasons rather than silent disappearance.

## Package retention

Retain:

- latest complete certified package;
- prior complete certified package;
- permanent lightweight package and certification history.

Longer history moves through active, archive, and deep-archive tiers according to policy.

## Import guarantees

UIP imports must be:

- validated before activation;
- atomic;
- backed up before material production change;
- idempotent;
- replay-protected;
- rolled back on failure;
- reconciled after completion.

The prior certified state remains available when a new import fails.

## Processing cadence

### Immediate operational updates

- transaction ledger;
- affected holdings;
- cost basis;
- cash impact;
- allocation;
- portfolio state;
- recommendation applicability.

### On-demand analytical updates

- recommendations;
- portfolio-dependent forecasts;
- capital allocation;
- directly affected risk measures.

### Daily certified batch

- complete source refresh;
- full valuations;
- full forecasts;
- complete risk models;
- ranking;
- universal recommendations;
- historical analytics;
- model evaluation;
- reconciliation;
- backups;
- archive lifecycle.

## Backup and restoration

Default retention target:

- 30 daily backups;
- 24 monthly backups.

Restoration requires Devon’s manual approval.

Backups and recovery evidence must be stored remotely before local deletion is authorized.

## Conflict resolution

When records conflict:

1. identify the authoritative source;
2. preserve conflicting evidence;
3. correct the problem at the source where possible;
4. republish and reimport;
5. document the correction and certification result.

No downstream silent patch may replace authoritative correction.

## Local cleanup

Local deletion requires:

- classification;
- verified backup;
- identification of system owner;
- confirmation that no active workflow depends on it;
- Devon’s approval.

## Sensitive data

Strongest protection applies to:

- secrets;
- holdings;
- transactions;
- account-related data;
- portfolio snapshots;
- personal financial exports.

Viewer and operator dashboard keys are secrets. Operator permissions cannot bypass governance controls.

## Historical analytics and model governance

Maintain enough point-in-time history for:

- walk-forward analysis;
- champion/challenger models;
- shadow evaluation;
- anti-lookahead controls;
- survivorship controls;
- adaptive learning;
- counterfactual evaluation;
- rollback to a prior model.

Original observations must be preserved when automated correction or normalization occurs.

## Transaction authority

The immutable transaction ledger is authoritative.

Holdings, cost basis, allocation, and portfolio state are derived from ledger evidence and governed market data.

Initial transaction scope:

- purchases;
- sales.

## Recommendation completion

The user-recorded action is:

`MARK_COMPLETED`

Completion requires linked reconciled transaction evidence.

System-managed lifecycle states may include:

- `PARTIALLY_COMPLETED`
- `SUPERSEDED`
- `EXPIRED`
- `INVALIDATED`
- `WITHDRAWN`
- `PERFORMANCE_MONITORING`
- `PERFORMANCE_EVALUATED`

## Retention terminology

Retention must satisfy applicable:

- legal;
- tax;
- contractual;
- regulatory;
- recovery;
- governance requirements.

UIP must not be described as a regulated entity unless that becomes factually applicable.

## System-of-record principle

> Source systems own native facts, certified packages own published snapshots, UIP owns canonical portfolio truth, the immutable ledger owns transactions, and GitHub owns implementation. No single chat, local export, or unverified database copy may silently replace those authorities.
