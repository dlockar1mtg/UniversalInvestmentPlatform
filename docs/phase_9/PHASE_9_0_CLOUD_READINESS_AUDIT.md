# Phase 9.0 — Cloud Architecture and Readiness Audit

## Objective

Establish a complete, evidence-backed inventory of every dependency that prevents the Universal Investment Platform (UIP) and its source domains from running as a fully cloud-portable production system.

This phase is an audit and decision phase. It does not migrate production state or retire local execution.

## In Scope

The audit covers five systems:

1. Universal Investment Platform (UIP)
2. Metals source platform
3. MTG Investment Terminal
4. Crypto Intelligence Platform
5. Render deployment and managed services

## Required Inventory Categories

Every system must be evaluated for:

- local filesystem paths;
- local or embedded databases;
- external and internal source APIs;
- secrets and credentials;
- manual inputs and operator steps;
- historical files and retained packages;
- Python and non-Python package dependencies;
- operating-system assumptions;
- runtime duration and resource demand;
- external repository dependencies;
- generated artifacts and publication destinations;
- scheduled jobs and trigger mechanisms;
- network access requirements;
- failure handling and recovery behavior;
- observability, health, and audit evidence.

## Evidence Standard

Each matrix row must identify an evidence source whenever possible, including one or more of:

- repository path;
- configuration key;
- workflow name;
- database or schema name;
- environment-variable name;
- local path supplied by the operator;
- command output;
- generated inventory artifact;
- deployment-service setting.

Unsupported assumptions must be marked `UNVERIFIED`, not treated as fact.

## Readiness Statuses

Use only the following statuses:

- `READY` — portable and already proven in a cloud or clean Linux runtime;
- `PARTIAL` — portable components exist, but certification or integration is incomplete;
- `BLOCKED` — a known dependency prevents cloud production;
- `UNVERIFIED` — evidence has not yet been collected;
- `NOT_APPLICABLE` — the category does not apply.

## Risk Levels

- `CRITICAL` — prevents production execution or risks loss/corruption of state;
- `HIGH` — prevents reliable automation, promotion, recovery, or security;
- `MEDIUM` — requires manual work or creates material operational fragility;
- `LOW` — cleanup, optimization, or documentation gap.

## Required Deliverables

### 1. Cloud-readiness matrix

File: `docs/phase_9/cloud_readiness_matrix.csv`

The matrix must cover all five systems and every required inventory category.

### 2. Architecture findings report

File: `docs/phase_9/PHASE_9_0_FINDINGS.md`

The report must summarize:

- current architecture;
- local-only dependencies;
- cloud-capable components already present;
- required credentials;
- state-placement decisions;
- Linux and Docker gaps;
- GitHub Actions gaps;
- Render and PostgreSQL gaps;
- object-storage requirements;
- estimated production operating footprint;
- recommended Phase 9.1 entry criteria.

### 3. Machine-readable inventory

Generated under:

`artifacts/phase_9/cloud_readiness/`

The audit runner must produce JSON and CSV evidence suitable for comparison and certification.

## Existing Cloud Foundation to Preserve

Phase 9 begins with existing cloud-oriented assets already present in UIP, including:

- a Render blueprint;
- a Docker runtime;
- PostgreSQL backend configuration;
- production API entry points;
- Phase 8 unified production control-plane capabilities.

These assets must be audited and extended rather than replaced without evidence.

## Audit Workstreams

### 9.0.1 — UIP Repository Inventory

Inventory paths, configuration, dependencies, databases, commands, workflows, generated packages, and production-control-plane behavior.

### 9.0.2 — Metals Source Inventory

Identify local source paths, provider credentials, runtime requirements, historical state, package outputs, and all dependencies needed to reproduce a clean production cycle.

### 9.0.3 — MTG Source Inventory

Identify repository/runtime dependencies, marketplace credentials, retained history, manual inputs, package outputs, and scheduling constraints.

### 9.0.4 — Crypto Source Inventory

Identify repository/runtime dependencies, market-data credentials, retained state, package outputs, and scheduling constraints.

### 9.0.5 — Render and Managed-Service Inventory

Document current web service, database connectivity, environment variables, deployment behavior, persistent-state assumptions, backup posture, and production limits.

### 9.0.6 — Cross-System Placement Decisions

Classify every stateful asset as one of:

- PostgreSQL;
- object storage;
- repository-controlled configuration;
- ephemeral runtime artifact;
- secret manager / GitHub or Render secret;
- prohibited local-only production dependency.

### 9.0.7 — Findings and Phase 9.1 Gate

Phase 9.0 passes only when:

- all required matrix categories have evidence or are explicitly `UNVERIFIED`;
- every critical blocker has an owner and remediation phase;
- state-placement decisions are documented;
- required secrets are named without exposing values;
- all production commands are identified;
- Linux/Docker compatibility gaps are listed;
- a Phase 9.1 implementation backlog is approved.

## Non-Goals

Phase 9.0 does not:

- provision object storage;
- create or migrate production PostgreSQL schemas;
- move source pipelines into GitHub Actions;
- change Render production routing;
- retire local execution;
- add Stocks/ETFs.

## Initial Decision

Stocks/ETFs remain deferred until Phase 9 cloud portability is certified. Adding another asset domain before state, orchestration, and runtime portability are standardized would increase migration scope and operational risk.
