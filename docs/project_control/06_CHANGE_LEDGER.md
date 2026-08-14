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

---

## UIP-CHG-2026-025 — Create Controlled MTG Reconciliation Branch

Date: 2026-07-30
Status: IMPLEMENTED
Type: BRANCH_CONTROL, RECOVERY_CONTROL, MTG_INTEGRATION
Approval authority: Devon Lockard

Decision:

Create a clean MTG historical-performance reconciliation branch from the approved governance baseline rather than merging or directly continuing the defective Phase 10.12 recovery implementation.

Implementation evidence:

- source governance commit: `df8e796`
- new branch: `recovery/mtg-historical-performance-reconciliation`
- worktree: `C:\Users\DevonLockard\InvestmentPlatform-MTG-Reconciliation`
- remote branch published: confirmed
- remote tracking configured: confirmed
- old recovery commit tested: `c6606d0b31add9fb356db8c3c15bc44af3b8175f`
- old recovery commit included in ancestry: no
- protected interpretation resources present in worktree: no
- protected recovery-inspection resources present in worktree: no
- starting working tree status: clean

Preserved evidence policy:

The old Phase 10.12 branch and commit remain available as implementation evidence. They must not be merged or cherry-picked wholesale. Individual concepts may be selectively reimplemented only after contract, migration, test, and certification review.

New state:

`MTG_RECONCILIATION_BRANCH_CREATED`

Next required action:

`RECONSTRUCT_MTG_HISTORICAL_PERFORMANCE`

Reversal:

`FULLY_REVERSIBLE`


## UIP-CHG-2026-026 — Activate Certified Domain Integration Sequence

Date: 2026-08-13
Status: ACTIVE
Type: ROADMAP, MTG_INTEGRATION, DATA_CONTRACT, CERTIFICATION, DOMAIN_GOVERNANCE
Approval authority: Devon Lockard

Decision:

Prospectively supersede the recovery-era
`RECONSTRUCT_MTG_HISTORICAL_PERFORMANCE` next-action requirement with:

`UIP_MTG_A1_EXPORT_ACCEPTANCE_AND_SEMANTIC_PRESERVATION`

Historical branch creation, recovery findings, failed-run evidence, migration
controls, and all recovery evidence through `UIP-CHG-2026-025` remain
preserved.

Certified MTG upstream authority:

- repository: `dlockar1mtg/mtg-investment-terminal`
- Unified MTG V1 production commit:
  `94c2bd3273eaba4d05ee8f7f5c3d6c4dcc283768`
- MTG-to-UIP export certification commit:
  `f7dea3e2611f27de4ff6541da3b1d6a60dc6d695`
- certified payload SHA-256:
  `006ba3951565437291284d8e86e93a40208d2c0e783f43d3652e9f8f510914e1`
- Collector rows: 50
- Pre-Collector rows: 131
- Secret Lair V1.1 rows: 787
- current total rows: 968
- current total is a permanent universe constant: false
- export transformations: 0
- UIP acceptance testing authorized: true
- UIP integration certified: false
- UIP cross-asset ranking authorized: false
- automatic purchase execution: false

Semantic-preservation requirements:

- preserve MTG lane identity;
- preserve native rank together with native rank type;
- native rank is not a global MTG rank;
- native rank is not a cross-asset UIP rank;
- preserve native purchase status and purchase semantic;
- missing price remains missing;
- missing forecast remains missing;
- missing rank remains missing;
- missing purchase status remains missing;
- Secret Lair `BUY_CANDIDATE_NOW` means
  `MODEL_QUALIFIED_ENTRY_CANDIDATE`;
- Secret Lair BUY is not execution-ready purchase authority;
- manual execution-price validation remains required where governed;
- Secret Lair discovery remains dynamic;
- automatic purchase execution remains false.

Domain-boundary rule:

MTG, Metals, Crypto, and future Stocks/ETFs retain their native data,
modeling, forecast, risk, ranking, recommendation, refresh, and
recertification semantics unless separately governed.

UIP may consume certified outputs, preserve lineage, orchestrate governed
refresh routes, and present native evidence.

Thresholds, weights, ranking semantics, recommendation policies, or model
assumptions may not transfer between domains without explicit governance.

No universal cross-asset ranking is authorized by this change.

Refresh rule:

Current-price refresh, liquidity refresh, new-asset discovery, historical
append, model rerun, model retraining, recommendation rerun, recertification,
and full rebuild remain distinct governed operations.

Active integration sequence:

1. `UIP-MTG-A1`
2. `UIP-MTG-A2`
3. `UIP-METALS-A0/A1`
4. `UIP-CRYPTO-A0/A1`
5. `UIP-D1`
6. `UIP-R1`
7. `UIP-R2`
8. `UIP-E1`
9. `UIP-DASH-1`
10. `UIP-DASH-2`

Prior state:

`RECONSTRUCT_MTG_HISTORICAL_PERFORMANCE`

New state:

`CERTIFIED_DOMAIN_INTEGRATION_SEQUENCE_ACTIVE`

Superseded scope:

Only the prospective next-action requirement of `UIP-CHG-2026-025` is
superseded. Its historical implementation decision and evidence remain
preserved.

Reversal:

`FULLY_REVERSIBLE`

Next required action:

`UIP_MTG_A1_EXPORT_ACCEPTANCE_AND_SEMANTIC_PRESERVATION`

---

## UIP-CHG-2026-027 — Certify UIP-MTG-A1 and Activate UIP-MTG-A2

Date: 2026-08-14
Status: ACTIVE
Type: MTG_INTEGRATION, CERTIFICATION, ROADMAP_STATE, DATA_LINEAGE
Approval authority: Devon Lockard

Decision:

Certify completion of `UIP_MTG_A1_EXPORT_ACCEPTANCE_AND_SEMANTIC_PRESERVATION` and activate `UIP_MTG_A2_INTEGRATION_CERTIFICATION`.

This transition implements the sequence already approved by `UIP-CHG-2026-026`. It does not create cross-asset ranking authority, change MTG model semantics, or reopen certified MTG source-domain work.

A1 evidence:

- implementation commit: `7b02c11bf30096c37f08eeea02716d7e0cc9d176`;
- pull request: `#35`;
- governed merge commit: `8d414f599684dd9ead27008d821fd2b41d5fd9e7`;
- certified MTG export authority: `62905717e7944591a83578abaef16ad0ca16e1f5`;
- production authority: `94c2bd3273eaba4d05ee8f7f5c3d6c4dcc283768`;
- canonical payload SHA-256: `aa363cd474ae6b846588bb4af2fd235a676e5cefd65441d497addf765a35eb71`;
- current rows: 968, not a permanent universe constant;
- Collector / Pre-Collector / Secret Lair rows: 50 / 131 / 787;
- Secret Lair BUY candidates: 88;
- duplicate governed asset IDs: 0;
- transformations and missing-value imputations: 0;
- execution-ready purchase authority: false;
- cross-asset ranking authority: false;
- automatic purchase execution: false;
- full UIP suite: 1,227 passed, 1 existing warning;
- post-merge UIP CI #487: success;
- post-merge Container Delivery #64: success.

A2 boundary:

A2 must certify the binding between the accepted MTG V1 export and UIP canonical integration/storage while preserving native lane identity, native rank and rank type, native purchase semantics, missingness, dynamic Secret Lair discovery, and full lineage.

The older `uip-mtg-delivery-v1` intake is implementation evidence only and must not be treated as semantic authority for the new MTG V1 export.

Prior state:

`UIP_MTG_A1_EXPORT_ACCEPTANCE_AND_SEMANTIC_PRESERVATION`

New state:

`UIP_MTG_A2_INTEGRATION_CERTIFICATION`

Reversal:

`FULLY_REVERSIBLE`

Next required action:

`CERTIFY_UIP_MTG_A2_INTEGRATION`

---

## UIP-CHG-2026-028 — Certify UIP-MTG-A2 and Activate UIP-METALS-A0/A1

Date: 2026-08-14
Status: ACTIVE
Type: MTG_INTEGRATION, METALS_INTEGRATION, CERTIFICATION, ROADMAP_STATE
Approval authority: Devon Lockard

Decision:

Certify `UIP_MTG_A2_INTEGRATION_CERTIFICATION` complete and activate `UIP_METALS_A0_A1_DOMAIN_BINDING`.

MTG A2 evidence:

- implementation commit: `d5acd3725203a826f5899b5faed9708c6caecafa`;
- pull request: `#36`;
- governed merge commit: `4dfc98df10dcd1cf59db075b41cce95c237956b2`;
- canonical MTG rows: 968;
- 23 native fields preserved;
- lineage-missing rows: 0;
- generic recommendation, forecast, and risk reinterpretation: false;
- cross-asset ranking created: false;
- execution-ready purchase authority created: false;
- automatic purchase execution: false;
- full UIP suite: 1,232 passed, 1 existing warning;
- post-merge UIP CI #491: success;
- post-merge Container Delivery #66: success.

Metals A0/A1 boundary:

Metals is an existing UIP-native domain and must be inspected from current repository authority before any new implementation. Phase 8.8 certification and Phase 8.9.x runtime-independence evidence are implementation authorities to reconcile, not reasons to restart or replace Metals-native models.

A0/A1 must determine current certified Metals ownership, provider and freshness state, canonical asset and vehicle coverage, forecast/recommendation/risk publication surfaces, runtime independence, package/import lineage, and the remaining binding gap into current UIP canonical architecture.

No Metals-native methodology, forecast logic, recommendation semantics, risk semantics, provider authority, or asset-universe rule may be redefined during A0/A1 unless a verified governance defect is found.

Prior state:

`UIP_MTG_A2_INTEGRATION_CERTIFICATION`

New state:

`UIP_METALS_A0_A1_DOMAIN_BINDING`

Reversal:

`FULLY_REVERSIBLE`

Next required action:

`INSPECT_AND_BIND_UIP_METALS_NATIVE_DOMAIN`

---

## UIP-CHG-2026-029 — Certify UIP-METALS-A0/A1 and Activate UIP-CRYPTO-A0/A1

Date: 2026-08-14
Status: ACTIVE
Type: METALS_INTEGRATION, CRYPTO_INTEGRATION, CERTIFICATION, ROADMAP_STATE, GOVERNANCE_CORRECTION
Approval authority: Devon Lockard

Decision:

Certify `UIP_METALS_A0_A1_DOMAIN_BINDING` complete and activate
`UIP_CRYPTO_A0_A1_DOMAIN_BINDING`.

This entry also prospectively corrects a documentary omission in
`UIP-CHG-2026-028`. Entry 028 correctly recorded the MTG A2 implementation,
PR, governed merge, tests, and post-merge CI evidence, but omitted the
separate A2 governance-transition commit:

`1e9c1718f518c20b090a1e8ee7b6a53398de9d86`

Entry 028 remains unchanged as historical ledger evidence. This correction
does not alter MTG A2 implementation semantics, certification results, or
merge authority.

Metals A0/A1 evidence:

- governed main baseline: `4dfc98df10dcd1cf59db075b41cce95c237956b2`;
- governance activation: `13434495ac216e2a71569f92371e62d7c3d7369e`;
- UTF-8 governance correction: `f1a60eeb6d179261b6df57fa461dfd9a6e0bf318`;
- canonical identity binding: `21cf4a7c28c46761a6c57ab28f327fd3b3b9ea03`;
- lossless contract-to-history translation: `a2f0e1939e60f909332b0443db8cb0be5396abf8`;
- native package contract alignment: `ce1339425af63cd2087c66e09e5c7b84945d2b02`;
- certified technical integration: `b9299c0aecbdc4bcb9aee1ea9582022dd36bb0c5`;
- certification status: `UIP_METALS_A1_INTEGRATION_CERTIFICATION_PASS`;
- canonical registry assets: 10;
- governed commodity forecast assets: 9;
- reserve/noncommodity assets: 1;
- published asset / forecast / recommendation / platform-status rows: 9 / 9 / 9 / 1;
- transactional datasets imported: 4;
- imported rows: 28;
- canonical identities preserved: true;
- commodity benchmarks treated as direct investment vehicles: false;
- unsupported liquidity, market/region, or history-start authority synthesized: false;
- forecast semantics preserved: true;
- missing forecast authority preserved as NULL: true;
- native recommendation labels preserved: true;
- universal recommendation vocabulary standardized: true;
- otherwise-unmapped governed contract fields preserved in metadata: true;
- import lineage complete: true;
- duplicate replay rejected: true;
- unknown native asset fails closed: true;
- standalone-free readiness: pass;
- native Metals model changed: false;
- cross-domain allocation policy changed: false;
- cross-asset ranking authority: false;
- automatic purchase execution: false;
- targeted A1 tests: 18 passed;
- MTG A2 regression tests: 5 passed;
- Metals-focused tests: 144 passed;
- full UIP suite: 1,242 passed, 1 existing warning.

Permanent certification evidence:

`docs/project_control/generated/metals_a1_integration/metals_a1_integration_certification.json`

Crypto boundary:

Crypto A0/A1 must begin from current repository and certified source-domain
truth. Existing Crypto branches already contained in UIP main are evidence,
not authorization to rebuild or redefine Crypto-native logic.

A0/A1 must inspect current Crypto ownership, package/export contract,
canonical asset coverage, package-byte integrity, import lineage,
forecast/recommendation/risk semantics, runtime independence, and any
remaining UIP binding gap.

No MTG or Metals work may be reopened during Crypto A0/A1 without a verified
governance defect.

No cross-asset ranking or automatic purchase execution is authorized by this
transition.

Prior state:

`UIP_METALS_A0_A1_DOMAIN_BINDING`

New state:

`UIP_CRYPTO_A0_A1_DOMAIN_BINDING`

Reversal:

`FULLY_REVERSIBLE`

Next required action:

`INSPECT_AND_BIND_UIP_CRYPTO_DOMAIN`

---

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
