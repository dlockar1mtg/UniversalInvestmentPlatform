# Universal Investment Platform — Change Ledger

## Purpose

The ledger permanently records material decisions that change UIP architecture, roadmap, repository authority, recovery status, contracts, certification, production operation, security, scope, or cost.

Its main purpose is:

`Control future changes`

## Mandatory logging

Always log:

- architecture decisions;
- roadmap decisions;
- repository-authority changes;
- recovery dispositions;
- material contract and schema policy;
- certification policy;
- production provider and topology decisions;
- security-boundary changes;
- material scope and recurring-cost changes.

Routine implementation may be summarized through commits and certification evidence when it does not change approved direction.

## Governance authority

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

The hierarchy in `02_SYSTEM_OF_RECORD.md`.

A ledger entry may change policy prospectively, but cannot rewrite historical production facts or make uncertified implementation authoritative.

## Entry fields

Each material entry should record:

- change ID;
- date;
- status;
- type;
- title;
- approval authority;
- decision;
- prior state;
- new state;
- reason;
- affected systems and repositories;
- roadmap impact;
- architecture impact;
- certification impact;
- risk and cost impact;
- reversal path;
- evidence;
- superseded entries;
- next required action.

Identifier format:

`UIP-CHG-YYYY-NNN`

## Statuses

- `PROPOSED`
- `APPROVED`
- `ACTIVE`
- `IMPLEMENTING`
- `IMPLEMENTED`
- `CERTIFIED`
- `REJECTED`
- `DEFERRED`
- `SUPERSEDED`
- `REVERSED`
- `FAILED`

## Reversal classifications

- `FULLY_REVERSIBLE`
- `REVERSIBLE_WITH_MIGRATION`
- `REVERSIBLE_WITH_DATA_RESTORE`
- `PARTIALLY_REVERSIBLE`
- `NOT_PRACTICALLY_REVERSIBLE`
- `NOT_YET_IMPLEMENTED`

## Approval boundary

Devon approves:

- architecture;
- roadmap;
- scope;
- material contract policy;
- repository authority;
- paid services;
- production providers;
- destructive cleanup;
- recovery restoration;
- model-promotion policy;
- final production acceptance.

Automated validation approves only implementation conformance and coordinated activation within already-approved policy.

# Initial change history

## UIP-CHG-2026-001 — Establish Project Control Center

Date: 2026-07-30  
Status: ACTIVE  
Type: ARCHITECTURE, ROADMAP, DATA_GOVERNANCE  
Approval authority: Devon Lockard

Decision:

Create a repository-backed Project Control Center as durable authority for future UIP work.

Next action:

Create and commit the approved files.

---

## UIP-CHG-2026-002 — Define repository ownership

Date: 2026-07-30  
Status: ACTIVE  
Type: ARCHITECTURE, REPOSITORY_AUTHORITY

Decision:

- UIP: `dlockar1mtg/UniversalInvestmentPlatform`
- MTG: `dlockar1mtg/mtg-investment-terminal`
- Crypto: `dlockar1mtg/CryptoIntelligencePlatform`
- Metals: native inside UIP

---

## UIP-CHG-2026-003 — Adopt remote-first laptop-independent architecture

Date: 2026-07-30  
Status: ACTIVE  
Type: ARCHITECTURE, REMOTE_INFRASTRUCTURE

Decision:

Final production may not require Devon’s laptop, local databases, Windows Task Scheduler, localhost, required Windows paths, or a laptop self-hosted runner.

---

## UIP-CHG-2026-004 — Prioritize lowest sustainable recurring cost

Date: 2026-07-30  
Status: ACTIVE  
Type: COST, REMOTE_INFRASTRUCTURE

Decision:

Minimize recurring cost without weakening security, persistence, backups, reliability, lineage, exportability, or laptop independence.

---

## UIP-CHG-2026-005 — Define processing cadence

Date: 2026-07-30  
Status: ACTIVE  
Type: ARCHITECTURE, PRODUCTION

Decision:

Use immediate operational transaction updates, on-demand affected analytics, and daily certified full processing.

---

## UIP-CHG-2026-006 — Protect all trust boundaries

Date: 2026-07-30  
Status: ACTIVE  
Type: SECURITY, ARCHITECTURE

Decision:

Dashboard, API, database, workflows, artifacts, packages, secrets, backups, archives, and administrator actions require mandatory controls.

---

## UIP-CHG-2026-007 — Define UIP system boundary

Date: 2026-07-30  
Status: ACTIVE  
Type: ARCHITECTURE, SCOPE

Decision:

UIP owns Metals, universal integration, portfolio ledger, analytics, recommendations, orchestration, and dashboard. MTG and Crypto remain independent source repositories.

---

## UIP-CHG-2026-008 — Define failure escalation

Date: 2026-07-30  
Status: ACTIVE  
Type: PRODUCTION, CERTIFICATION

Decision:

`Detect → safe retry → repeated retry → escalation`

Escalate through the dashboard and deduplicated GitHub issues.

---

## UIP-CHG-2026-009 — Require expandable lineage

Date: 2026-07-30  
Status: ACTIVE  
Type: DATA_GOVERNANCE, DASHBOARD

Decision:

Every certified or decision-relevant result requires expandable lineage.

---

## UIP-CHG-2026-010 — Define retention and archive model

Date: 2026-07-30  
Status: ACTIVE  
Type: DATA_GOVERNANCE

Decision:

Keep recent data quickly accessible, move older records through archive tiers, retrieve archives automatically, and retain authoritative records according to applicable legal, tax, contractual, regulatory, recovery, and governance requirements.

---

## UIP-CHG-2026-011 — Define dashboard landing priority

Date: 2026-07-30  
Status: ACTIVE  
Type: DASHBOARD

Decision:

The dashboard opens to portfolio changes and attention items.

---

## UIP-CHG-2026-012 — Define transaction-ledger scope

Date: 2026-07-30  
Status: ACTIVE  
Type: ARCHITECTURE, DATA_GOVERNANCE, DASHBOARD

Decision:

Initial dashboard transaction scope is purchases and sales. The immutable ledger is authoritative; holdings are derived.

---

## UIP-CHG-2026-013 — Define recommendation completion

Date: 2026-07-30  
Status: ACTIVE  
Type: DASHBOARD, MODEL_GOVERNANCE

Decision:

The approved user action is `MARK_COMPLETED`, supported by reconciled transaction evidence. Other lifecycle states are system managed.

---

## UIP-CHG-2026-014 — Define model promotion

Date: 2026-07-30  
Status: ACTIVE  
Type: MODEL_GOVERNANCE, CERTIFICATION

Decision:

Promote models by best validated net risk-adjusted performance using point-in-time backtests and rollback on material degradation.

---

## UIP-CHG-2026-015 — Define coordinated contract upgrades

Date: 2026-07-30  
Status: ACTIVE  
Type: DATA_CONTRACT, SCHEMA, CERTIFICATION

Decision:

Use atomic coordinated upgrades at the production-release level. Devon approves material policy; automated validation approves conformance and activation.

---

## UIP-CHG-2026-016 — Define production certification

Date: 2026-07-30  
Status: ACTIVE  
Type: CERTIFICATION

Decision:

Final readiness requires one successful end-to-end certification covering dashboard, analytics, sources, automation, remote operation, transactions, lineage, backups, recovery, roles, archives, and laptop independence.

---

## UIP-CHG-2026-017 — Initial roadmap infrastructure ordering

Date: 2026-07-30  
Status: SUPERSEDED  
Type: ROADMAP

Prior decision:

Place remote infrastructure before complete dashboard implementation.

Superseded by:

`UIP-CHG-2026-018`

---

## UIP-CHG-2026-018 — Place dashboard before final infrastructure

Date: 2026-07-30  
Status: ACTIVE  
Type: ROADMAP, DASHBOARD, REMOTE_INFRASTRUCTURE

Decision:

Complete and certify the dashboard before selecting and hardening final remote production infrastructure.

Render is provisional, not automatically final.

---

## UIP-CHG-2026-019 — Classify recovered project state

Date: 2026-07-30  
Status: SUPERSEDED  
Type: RECOVERY, ROADMAP

Prior decision:

`RECOVERED_AND_READY_FOR_INTEGRATION` with inspection required.

Superseded by:

`UIP-CHG-2026-021`

---

## UIP-CHG-2026-020 — Harmonize Project Control Center

Date: 2026-07-30  
Status: ACTIVE  
Type: ARCHITECTURE, ROADMAP, DATA_GOVERNANCE, CERTIFICATION, DASHBOARD

Decision:

Adopt the cross-document consistency corrections:

- immediate ledger and holdings updates;
- certification duties divided across Phases G, H, and J;
- separate governance, implementation, and production-data authority;
- contract policy approval separated from automated conformance;
- release-level coordinated upgrades;
- Render recorded as provisional dashboard environment;
- refresh actions clarified;
- lineage scoped to certified and decision-relevant results;
- recommendation controls separated from system lifecycle;
- retention terminology standardized;
- incident ownership clarified.

---

## UIP-CHG-2026-021 — Complete recovered-repository inspection

Date: 2026-07-30  
Status: ACTIVE  
Type: RECOVERY, REPOSITORY_AUTHORITY, CERTIFICATION, ROADMAP  
Approval authority: Devon Lockard

Decision:

Classify the recovered state as:

`MULTI_BRANCH_RECONCILIATION_REQUIRED_BEFORE_INTEGRATION`

Evidence:

- stable baseline `7bd8d0e`;
- complete baseline suite: 1,201 passed;
- recovery archive SHA-256 verified;
- historical-performance commit `c6606d0` is a clean one-commit child of the baseline;
- all four targeted recovered tests fail;
- current UIP database contains 23 objects and no historical-performance objects;
- MTG orchestration remote branch is 26 commits ahead and 50 behind;
- Phase 11 is 5 commits ahead and 21 behind;
- Crypto and Metals candidate branches are already contained in `main`.

Disposition:

- do not merge `c6606d0` directly;
- reconstruct historical performance under governed migrations and contracts;
- selectively port MTG orchestration from remote tip `b22ccc0`;
- evaluate Phase 11 after domain reconciliation;
- preserve all recovery evidence.

Next required action:

`CREATE_PROJECT_CONTROL_CENTER_FILES`

Reversal:

`NOT_YET_IMPLEMENTED`

---

## UIP-CHG-2026-022 — Commit Project Control Center

Date: 2026-07-30  
Status: IMPLEMENTED  
Type: ARCHITECTURE, ROADMAP, DATA_GOVERNANCE  
Approval authority: Devon Lockard

Decision:

Commit the seven approved and harmonized Project Control Center documents to the governance branch.

Implementation evidence:

- branch: `recovery/uip-project-control-center`
- commit: `607f425`
- files committed: 7
- inserted lines: 1,834
- protected recovery resources remained untracked

New state:

`PROJECT_CONTROL_CENTER_COMMITTED`

Next required action:

`GENERATE_SCHEMA_CONTROL_ARTIFACTS`

Reversal:

`FULLY_REVERSIBLE`

---

## UIP-CHG-2026-023 — Establish Database Schema Control Artifacts

Date: 2026-07-30
Status: IMPLEMENTED
Type: DATA_GOVERNANCE, DATABASE_SCHEMA, RECOVERY_CONTROL
Approval authority: Devon Lockard

Decision:

Generate, validate, commit, and publish the UIP database schema-control artifacts from the active ordered SQL files and read-only DuckDB introspection.

Implementation evidence:

- branch: `recovery/uip-project-control-center`
- commit: `bae641f`
- generator: `scripts/generate_uip_schema_control_artifacts.py`
- schema manifest: `schemas/database/schema_manifest.yaml`
- semantic dictionary: `docs/project_control/UIP_DATA_DICTIONARY.md`
- generated Markdown catalog: `docs/project_control/generated/UIP_DATABASE_SCHEMA_CATALOG.md`
- generated JSON catalog: `docs/project_control/generated/uip_database_schema_catalog.json`
- observed database objects: 23
- observed base tables: 12
- observed views: 11
- active ordered SQL files: 3
- read-only schema introspection: confirmed
- schema-control validation: PASS
- Markdown and JSON object agreement: PASS
- production database modification: none
- protected recovery resources remained untracked

Active ordered SQL authority:

1. `001_initialize_universal_database.sql`
2. `002_audit_registry_integration.sql`
3. `003_health_status_latest_attempt.sql`

Preserved non-canonical evidence excluded from migration authority:

`002_audit_registry_integration_before_1_3_6_2_20260717_085304.sql`

New state:

`SCHEMA_CONTROL_ARTIFACTS_COMMITTED`

Next required action:

`RECONCILE_ORDERED_MIGRATION_CHAIN`

Reversal:

`FULLY_REVERSIBLE`

---

## UIP-CHG-2026-024 — Certify Ordered Migration Chain

Date: 2026-07-30
Status: IMPLEMENTED
Type: DATABASE_SCHEMA, CERTIFICATION, RECOVERY_CONTROL
Approval authority: Devon Lockard

Decision:

Certify that the active ordered migration chain reproduces the current UIP baseline database schema.

Implementation evidence:

- branch: `recovery/uip-project-control-center`
- commit: `8201e9b`
- inspector: `scripts/inspect_uip_migration_chain.py`
- Markdown evidence: `docs/project_control/generated/UIP_MIGRATION_CHAIN_RECONCILIATION.md`
- JSON evidence: `docs/project_control/generated/uip_migration_chain_reconciliation.json`
- active migration files executed: 3
- current database objects: 23
- reconstructed database objects: 23
- missing reconstructed objects: 0
- extra reconstructed objects: 0
- definition mismatches: 0
- object types: matched
- columns and nullability: matched
- constraints: matched
- indexes: matched
- view definitions: matched
- fresh reconstruction: PASS
- production database hash before and after: unchanged

Certified disposition:

`MIGRATION_CHAIN_REPRODUCES_CURRENT_SCHEMA`

Preserved non-authoritative evidence:

`002_audit_registry_integration_before_1_3_6_2_20260717_085304.sql`

The preserved file differs from canonical migration `002`, but it is not part of the active migration authority.

New state:

`MIGRATION_CHAIN_RECONCILIATION_PASS`

Next required action:

`CREATE_MTG_RECONCILIATION_BRANCH`

Reversal:

`FULLY_REVERSIBLE`

# Future change procedure

Before material work:

1. read the ledger;
2. identify the latest relevant active entry;
3. verify roadmap authorization;
4. identify superseded decisions;
5. create a proposed entry when direction changes.

## Ledger integrity

Never:

- silently rewrite history;
- delete earlier decisions;
- recreate the ledger from memory;
- hide a failed or superseded state;
- use chat summaries as a substitute for the committed ledger.

Corrections require a new dated entry.

## Ledger principle

> Architecture and roadmap decisions must never depend on memory or informal conversation alone. Every material change must identify the prior state, approved new state, reason, impact, evidence, and reversal path.
