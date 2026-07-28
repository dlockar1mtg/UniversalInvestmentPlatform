# Phase 9.0 — Cloud Readiness Findings

## Executive Status

**Current certification:** NOT YET CERTIFIED

**Audit branch:** `phase-9.0-cloud-readiness-audit`

**Current conclusion:** UIP already contains meaningful cloud foundations, but the complete production system still has unverified state, runtime, secret, repository, and persistence dependencies across Metals, MTG, Crypto, UIP, and Render.

## Confirmed Existing Foundation

The following capabilities are already present and should be preserved:

- private GitHub repositories for UIP, MTG, and Crypto;
- a Docker-based UIP runtime;
- a Render service blueprint;
- PostgreSQL backend environment configuration;
- a production API entry point;
- a Phase 8 unified production control plane;
- governed domain package ingestion and publication concepts.

## Preliminary Critical Findings

### 1. Persistent package storage is not yet established

Render service disks must be treated as ephemeral unless an explicitly provisioned persistent service is used. Production packages, histories, checksums, and latest-success pointers therefore require object storage.

**Target phase:** 9.2

### 2. Database placement is not yet fully certified

UIP is configured to support PostgreSQL, but production schemas, staging schemas, migrations, promotion behavior, package registry, run history, dashboard views, and backup policy require Phase 9.3 certification.

**Target phase:** 9.3

### 3. Source-domain portability remains unverified

Metals, MTG, and Crypto must each prove a clean Linux or container run with deterministic dependencies and no undeclared local state.

**Target phases:** 9.0, 9.1, and 9.4

### 4. Repository orchestration boundaries require formalization

MTG and Crypto are available as private GitHub repositories. Metals requires a final authoritative source-repository decision. UIP orchestration must pin or record exact source revisions for every production cycle.

**Target phases:** 9.0, 9.1, and 9.5

### 5. Secret inventories are incomplete

Environment-variable names can be inventoried safely, but credential values must remain exclusively in GitHub or Render secret stores. A reconciled secret registry is required before cloud execution.

**Target phases:** 9.0 and 9.5

## State Placement Policy

| State type | Required placement |
|---|---|
| Relational production state | Render PostgreSQL |
| Staging and promotion state | Render PostgreSQL staging schemas |
| Versioned packages and large historical files | Object storage |
| Latest-success pointers and checksums | Object storage with registry references in PostgreSQL |
| Source-controlled configuration | GitHub repository |
| Credentials and tokens | GitHub Actions secrets or Render secret environment variables |
| Temporary run workspace | Ephemeral runner or container filesystem |
| Local-only production state | Prohibited after Phase 9.7 certification |

## Evidence Collection Remaining

- complete UIP path and database scan;
- Metals authoritative source path and repository decision;
- Metals dependency and runtime timing inventory;
- MTG local-state and manual-input inventory;
- MTG dependency and runtime timing inventory;
- Crypto local-state and manual-input inventory;
- Crypto dependency and runtime timing inventory;
- Render service and PostgreSQL plan inventory;
- GitHub Actions workflow and secret-name inventory;
- generated-package size and retention estimates;
- expected monthly runtime, storage, database, and network footprint.

## Phase 9.1 Entry Gate

Phase 9.1 may begin when:

1. every matrix row has an evidence reference or explicit `UNVERIFIED` disposition;
2. all critical local paths and databases are identified;
3. the Metals repository strategy is decided;
4. required secret names are documented without values;
5. current production commands are documented for all domains;
6. expected runtime and package sizes are measured;
7. state-placement decisions are approved;
8. the Phase 9.1 backlog is derived from confirmed blockers.

## Stocks/ETFs Decision

Stocks/ETFs remain out of scope until Phase 9.7. The cloud runtime, state, orchestration, and certification model should be proven with the existing domains before a new source platform is introduced.
