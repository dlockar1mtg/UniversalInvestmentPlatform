# Universal Investment Platform — Architecture and Data Flow

## Architectural priorities

Priority order:

1. reliability;
2. auditability;
3. security;
4. correctness;
5. explainability;
6. maintainability;
7. lowest sustainable recurring cost;
8. performance appropriate to the workload.

## Topology

UIP is the central portfolio-intelligence platform.

### Independent external source repositories

- MTG
- Crypto

These systems publish certified packages. They cannot write directly to the UIP production database.

### Native internal domain

- Metals

Metals may write only to Metals-owned or staging storage. Promotion into canonical UIP layers requires an internal certified publication boundary.

## Remote-first target

Final production must be:

- GitHub-centered;
- fully remote;
- laptop-independent;
- accessible from any authorized laptop;
- persistent when Devon’s laptop is offline.

Production must not depend on:

- localhost;
- a required Windows path;
- Windows Task Scheduler;
- a laptop-hosted database;
- an always-on personal computer;
- a laptop self-hosted GitHub runner.

## GitHub control plane

GitHub controls:

- repositories;
- Actions;
- secrets;
- environments;
- deployment definitions;
- contracts;
- migrations;
- certification;
- audit evidence;
- release history.

## Remote service classes

The final architecture requires:

- persistent remote database;
- protected dashboard;
- protected API or backend service;
- remote object storage;
- backups;
- archives;
- monitoring and incident evidence.

Provider selection occurs after workload and cost comparison.

## Provisional dashboard environment

The dashboard is already started on Render.

Render is the current provisional dashboard environment and an incumbent production candidate.

Phase H will inventory and certify the dashboard using provisional development or staging infrastructure.

Phase I will determine whether to:

- retain and harden Render;
- change the Render service structure;
- pair Render with another database or storage provider;
- migrate to a more sustainable provider.

Provisional infrastructure is not automatically authoritative production infrastructure.

## Processing model

### Immediate transaction processing

Transactions update:

- immutable ledger;
- holdings;
- cost basis;
- cash;
- allocation;
- portfolio state;
- recommendation applicability.

### On-demand analytics

User-initiated actions may run:

- recommendation refresh;
- portfolio-dependent forecast refresh;
- affected risk refresh;
- capital-allocation refresh.

Dashboard labels should distinguish:

- `Refresh Using Latest Certified Data`
- `Run Full Analytical Refresh`
- `Refresh Source Data`

### Daily batch processing

GitHub Actions or approved remote orchestration performs:

- source refresh;
- package certification;
- imports;
- full valuations;
- forecasting;
- risk;
- ranking;
- recommendations;
- historical analytics;
- model evaluation;
- backups;
- archives.

## Reliability and graceful degradation

User-facing services receive the strongest availability protections.

When a new cycle fails:

- preserve the prior certified state;
- retry transient failures safely;
- operate read-only when necessary;
- show freshness and failure status;
- prevent partial activation.

## Security

Required controls include:

- authentication;
- backend authorization;
- least privilege;
- encrypted transport;
- secrets management;
- package-integrity validation;
- backup protection;
- audit logging;
- environment separation.

## Environments

Logical environments:

- development;
- automated test;
- staging;
- production.

Temporary preview environments are permitted.

## Failure and incident handling

Failure flow:

`Detect → safe retry → repeated retry → escalation`

Escalation channels:

- dashboard;
- deduplicated GitHub issues.

Issue ownership:

- source implementation failure → source repository;
- UIP ingestion or orchestration failure → UIP repository;
- cross-system failure → primary issue in the repository requiring correction, with a linked UIP reference where useful.

## Data lineage

Full expandable lineage is required for every certified or decision-relevant result, including:

- holdings;
- valuations;
- portfolio totals;
- performance;
- forecasts;
- risk;
- rankings;
- allocations;
- recommendations;
- operational statuses.

Pure presentation calculations may inherit lineage from their certified source dataset.

## Dashboard information architecture

The dashboard opens to Portfolio Overview and emphasizes:

> What changed in my portfolio, and does anything require attention?

Planned sections:

- Portfolio
- Recommendations
- Forecasts
- Risk
- Assets
- Transactions
- Performance
- History
- Operations
- Administration

## Transaction workflow

Initial dashboard support:

- purchases;
- sales.

Requirements:

- immutable ledger authority;
- idempotent transactional posting;
- before-and-after impact;
- reconciliation;
- clear success or rollback result.

## Recommendation evaluation

A user may mark a recommendation completed only when reconciled transaction evidence supports completion.

After completion, evaluate:

- actual performance;
- counterfactual or benchmark performance;
- allocation effect;
- risk effect;
- portfolio effect.

Evaluation must avoid hindsight leakage.

## Model promotion

Promote models by best validated net risk-adjusted performance.

Required methods:

- point-in-time data;
- walk-forward testing;
- champion/challenger;
- shadow operation;
- anti-lookahead controls;
- survivorship controls;
- rollback.

Material degradation triggers review or rollback.

## Contract deployment

Contract policy and material semantic changes require Devon’s approval.

Automated validation may approve implementation conformance and coordinated activation after all established gates pass.

Use:

`Atomic coordinated upgrade at the production-release level`

A short controlled sequence is allowed:

`consumer readiness → producer activation → end-to-end verification → obsolete compatibility removal`

Long-term mixed contract versions require explicit approval.

## Production readiness

Production certification must prove:

- dashboard;
- analytics;
- source integrations;
- automation;
- remote operation;
- transaction reliability;
- lineage;
- backups;
- recovery;
- authentication and roles;
- archive retrieval;
- laptop independence.

## Architecture principle

> UIP integrates independent source intelligence into one governed portfolio system. Production must remain secure, traceable, recoverable, remotely available, and independent of a personal laptop.
