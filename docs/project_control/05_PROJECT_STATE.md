# Universal Investment Platform — Project State

## Current status

```text
Project:
Universal Investment Platform

Project abbreviation:
UIP

Recovery classification:
RECOVERED_AND_READY_FOR_INTEGRATION

Current execution state:
CERTIFIED_DOMAIN_INTEGRATION_SEQUENCE_ACTIVE

Current roadmap phase:
Certified domain integration

Current milestone:
UIP_MTG_A2_INTEGRATION_CERTIFICATION

Current certification:
BASELINE_TEST_SUITE_PASS
PROJECT_CONTROL_CENTER_COMMITTED
SCHEMA_CONTROL_ARTIFACTS_COMMITTED
SCHEMA_CONTROL_VALIDATION_PASS
MIGRATION_CHAIN_RECONCILIATION_PASS
MIGRATION_CHAIN_REPRODUCES_CURRENT_SCHEMA
MTG_RECONCILIATION_BRANCH_CREATED
OLD_PHASE_10_12_IMPLEMENTATION_EXCLUDED
UIP_A0G_GOVERNANCE_SYNCHRONIZATION_MERGED
UIP_MTG_A1_EXPORT_ACCEPTANCE_PASS
UIP_MTG_A1_MERGED
UIP_MTG_A1_POST_MERGE_CI_PASS

Next authorized action:
UIP_MTG_A2_INTEGRATION_CERTIFICATION
```

## Repository authority

Primary repository:

`dlockar1mtg/UniversalInvestmentPlatform`

Visibility:

`Private`

Local development path:

`C:\Users\DevonLockard\InvestmentPlatform`

Stable branch:

`main`

Current governed main baseline:

`8d414f599684dd9ead27008d821fd2b41d5fd9e7`

Historical recovery baseline:

`7bd8d0e3cb0f8cfa61208a0950cb7c3f51c7b5e8`

Historical recovery baseline evidence:

`1,201 passed, 1 warning`

Active governance branch:

`phase-uip-mtg-a2-integration-certification`

## UIP-MTG-A1 certification transition

Certified A1 implementation commit:

`7b02c11bf30096c37f08eeea02716d7e0cc9d176`

Merged governed main commit:

`8d414f599684dd9ead27008d821fd2b41d5fd9e7`

Pull request:

`#35`

Certification evidence:

- A1 acceptance status: `UIP_MTG_A1_EXPORT_ACCEPTANCE_PASS`;
- current MTG rows: 968;
- Collector rows: 50;
- Pre-Collector rows: 131;
- Secret Lair V1.1 rows: 787;
- Secret Lair BUY candidates: 88;
- duplicate governed MTG asset IDs: 0;
- transformations: 0;
- missing-value imputations: 0;
- current snapshot permanent: false;
- execution-ready purchase authority: false;
- cross-asset ranking authority: false;
- automatic purchase execution: false;
- full UIP suite: 1,227 passed, 1 existing warning;
- post-merge UIP CI #487: success;
- post-merge Container Delivery #64: success.

Disposition:

`UIP_MTG_A1_CERTIFIED_COMPLETE`

Active next milestone:

`UIP_MTG_A2_INTEGRATION_CERTIFICATION`

## Recovered historical-performance work

Branch:

`phase-10.12-mtg-historical-performance-import`

Commit:

`c6606d0b31add9fb356db8c3c15bc44af3b8175f`

Ancestry:

- zero commits behind baseline;
- one commit ahead;
- merge base is the stable baseline.

Changed files:

- `foundation/import_engine/loader.py`
- `foundation/import_engine/sql/001_initialize_universal_database.sql`
- `foundation/integrations/mtg/universal_adapter.py`
- `scripts/run_phase_10_11_mtg_import_reconciliation.py`
- `tests/test_phase_10_11_mtg_import_reconciliation.py`

Targeted-test result:

`4 failed`

Reproduced root cause:

Stale references to removed package-summary fields:

- `summary["forecast_eligible"]`
- `summary["recommendation_eligible"]`

Disposition:

`PRESERVE_AS_EVIDENCE_AND_REIMPLEMENT_SELECTIVELY`

Direct merge is not authorized.

## Additional branch state

### MTG production orchestration

Remote branch:

`origin/phase-10.12-mtg-production-orchestration`

Remote tip:

`b22ccc041d0e31b8681f80265cd5aa3197bd0d56`

Relationship to main:

- 26 commits ahead;
- 50 commits behind;
- diverged.

Disposition:

`VALUABLE_DIVERGED_WORK_REQUIRING_FEATURE_BY_FEATURE_PORT`

The remote tip, not the older local tip, is the complete branch reference.

### Phase 11 automation

Branch:

`origin/phase-11-cross-domain-production-automation`

Relationship to main:

- 5 commits ahead;
- 21 commits behind;
- diverged.

Disposition:

`SELECTIVE_PORT_AFTER_DOMAIN_RECONCILIATION`

### Crypto branches

`origin/phase-9.3-crypto-uip-ingestion` and `origin/hotfix/crypto-package-line-ending-integrity` are fully contained in `main`.

Disposition:

`NO RECOVERY MERGE REQUIRED`

### Metals branches

Phase 8.9.9 Metals work is fully contained in `main`.

Disposition:

`NO RECOVERY MERGE REQUIRED`

## Recovery archive

Path:

`C:\Users\DevonLockard\UIP_Recovery\phase-10.12-20260729-060030.zip`

SHA-256:

`B8C7EB3E46D110EBA420B08D7004AC3BB6E8BE114AC4F1E69D4A96037F6C801D`

Classification:

`RECOVERY_PROTECTED — INTEGRITY_VERIFIED`

The archive must not be deleted or modified until Phase A is certified and all required evidence is stored remotely.

## Protected local resources

Untracked and protected:

- `export_uip_interpretation_data.py`
- `uip_interpretation_export/`
- `uip_interpretation_input/`
- `uip_recovery_inspection/`
- `uip_recovery_inspection_output.txt`

Classifications:

### Export script

`RECOVERY_UTILITY — CODE_REVIEW_REQUIRED_BEFORE_COMMIT`

### Interpretation input

`SENSITIVE_RECOVERY_SNAPSHOT — DO_NOT_COMMIT`

### Interpretation export

`SENSITIVE_GENERATED_RECOVERY_EVIDENCE — DO_NOT_COMMIT`

### Inspection output

`RECOVERY_INSPECTION_EVIDENCE — DO_NOT_COMMIT UNTIL SANITIZED`

## Database state

Likely current local UIP database:

`data\universal\universal_investment.duckdb`

Observed objects:

`23`

Selected row counts:

- asset master current: 1,174
- asset master history: 8,199
- forecasts current: 1,499
- forecasts history: 5,254
- recommendations current: 1,169
- recommendations history: 5,285
- risk metrics current: 1,168
- risk metrics history: 2,439
- portfolio positions current: 12
- portfolio positions history: 66
- platform registry: 3
- universal imports: 25
- universal packages: 24

Historical-performance objects:

`ABSENT`

Current classification:

`LIKELY_CURRENT_LOCAL_UIP_DATABASE — AUTHORITY_NOT_YET_PRODUCTION_CERTIFIED`

Other discovered databases require ownership and lifecycle classification.

## Current approved repository findings

- The stable baseline is reproducible.
- The historical-performance feature is a genuine new universal dataset.
- The recovered schema change improperly edits the original initialization file instead of adding an ordered migration.
- The recovered adapter contains brittle fixed package counts that must be separated from permanent invariants.
- MTG privacy-boundary intent is aligned with UIP ownership.
- Metals is substantially native within UIP.
- MTG and Crypto integrations are advanced, not blank.
- Local production orchestration still contains Windows-path assumptions.
- Final production remains remote and laptop-independent.

## Open risks

1. Historical-performance schema and contract reconstruction.
2. Migration-chain authority.
3. MTG orchestration selective port.
4. Phase 11 selective port.
5. Current database authority and remote migration.
6. Protected personal financial snapshots.
7. Generated package duplication and retention.
8. Render dashboard inventory and hardening.
9. Local-path and laptop dependencies.
10. Completion of remaining asset domains.

## Current permissions

Authorized:

- create and commit approved Project Control Center documents;
- preserve recovery artifacts;
- inspect schemas, branches, tests, workflows, and databases;
- create isolated test worktrees;
- propose controlled reconciliation branches.

Not authorized:

- merge recovered commits;
- delete protected resources;
- force-push or rewrite history;
- modify production databases;
- expose personal financial data;
- provision paid infrastructure without approval;
- declare Phase A certified without evidence.

## Next integration sequence

1. `UIP-MTG-A1` - accept the certified MTG export and prove semantic preservation.
2. `UIP-MTG-A2` - certify MTG integration into UIP.
3. `UIP-METALS-A0/A1` - inspect and bind Metals under Metals-native governance.
4. `UIP-CRYPTO-A0/A1` - inspect and bind Crypto under Crypto-native governance.
5. `UIP-D1` - establish the minimal lossless common domain registry and lineage interface.
6. `UIP-R1` - establish governed refresh and orchestration contracts.
7. `UIP-R2` - perform refreshed-data rehearsals for MTG, Metals, and Crypto.
8. `UIP-E1` - establish the future Stocks/ETF extension boundary.
9. `UIP-DASH-1` and `UIP-DASH-2` - build the dashboard on certified multi-domain inputs.
10. Govern future cross-asset ranking, comparison, or allocation methodology separately.

No universal cross-asset ranking is authorized by this sequence.
Automatic purchase execution remains disabled.

## State principle

> UIP recovery history remains preserved, but current integration proceeds from certified repository and domain-package authority. Each domain retains its native semantics; UIP may accept certified outputs, preserve lineage, orchestrate governed refreshes, and present evidence without silently redefining native models, ranks, recommendations, or execution authority.
