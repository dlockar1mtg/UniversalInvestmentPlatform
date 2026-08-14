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
UIP_R2_REFRESHED_DATA_REHEARSAL

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
UIP_MTG_A2_INTEGRATION_CERTIFICATION_PASS
UIP_MTG_A2_MERGED
UIP_MTG_A2_POST_MERGE_CI_PASS
UIP_MTG_A2_POST_MERGE_CONTAINER_PASS

UIP_METALS_A1_INTEGRATION_CERTIFICATION_PASS
UIP_CRYPTO_A1_INTEGRATION_CERTIFICATION_PASS

Next authorized action:
UIP_R2_REFRESHED_DATA_REHEARSAL
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

`55d5c72582bf70aff21a30b69edadab9ea9e8553`

Historical recovery baseline:

`7bd8d0e3cb0f8cfa61208a0950cb7c3f51c7b5e8`

Historical recovery baseline evidence:

`1,201 passed, 1 warning`

Active governance branch:

`phase-uip-r1-refresh-orchestration`

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

## UIP-MTG-A2 certification closeout

A2 governance transition commit:

`1e9c1718f518c20b090a1e8ee7b6a53398de9d86`

A2 implementation commit:

`d5acd3725203a826f5899b5faed9708c6caecafa`

Merged governed main commit:

`4dfc98df10dcd1cf59db075b41cce95c237956b2`

Pull request:

`#36`

Certification evidence:

- status: `UIP_MTG_A2_INTEGRATION_CERTIFICATION_PASS`;
- canonical MTG rows: 968;
- Collector / Pre-Collector / Secret Lair rows: 50 / 131 / 787;
- Secret Lair BUY candidates: 88;
- all 23 native MTG fields preserved;
- missing values preserved as NULL;
- lineage-missing rows: 0;
- generic UIP recommendations created: false;
- generic UIP forecasts created: false;
- generic UIP risk records created: false;
- cross-asset rank created: false;
- execution-ready purchase authority created: false;
- automatic purchase execution: false;
- full UIP suite: 1,232 passed, 1 existing warning;
- post-merge UIP CI #491: success;
- post-merge Container Delivery #66: success.

Disposition:

`UIP_MTG_A2_CERTIFIED_COMPLETE`

Active next milestone:

`UIP_METALS_A0_A1_DOMAIN_BINDING`

## UIP-METALS-A0/A1 certification closeout

Certified technical integration commit:

`b9299c0aecbdc4bcb9aee1ea9582022dd36bb0c5`

Supporting implementation commits:

- governance activation: `13434495ac216e2a71569f92371e62d7c3d7369e`;
- UTF-8 governance correction: `f1a60eeb6d179261b6df57fa461dfd9a6e0bf318`;
- canonical identity binding: `21cf4a7c28c46761a6c57ab28f327fd3b3b9ea03`;
- lossless universal-contract import translation: `a2f0e1939e60f909332b0443db8cb0be5396abf8`;
- native package contract alignment: `ce1339425af63cd2087c66e09e5c7b84945d2b02`.

Certification evidence:

- status: `UIP_METALS_A1_INTEGRATION_CERTIFICATION_PASS`;
- canonical Metals registry assets: 10;
- governed commodity forecast assets: 9;
- governed noncommodity reserve assets: 1;
- published asset / forecast / recommendation / platform-status rows: 9 / 9 / 9 / 1;
- transactional datasets imported: 4;
- imported rows: 28;
- canonical asset identities preserved: true;
- commodity benchmarks marked investable: false;
- unsupported liquidity authority synthesized: false;
- unsupported market/region authority synthesized: false;
- fabricated first-history date synthesized: false;
- forecast semantics preserved: true;
- missing forecast authority preserved as NULL: true;
- native recommendation labels preserved: true;
- universal recommendation vocabulary standardized: true;
- otherwise-unmapped governed contract fields preserved in metadata: true;
- platform status preserved: true;
- lineage complete: true;
- duplicate package replay rejected: true;
- unknown native asset fails closed: true;
- standalone-free readiness: pass;
- Metals native model changed: false;
- cross-domain allocation policy changed: false;
- cross-asset ranking authority created: false;
- automatic purchase execution created: false;
- targeted A1 tests: 18 passed;
- MTG A2 regression tests: 5 passed;
- Metals-focused tests: 144 passed;
- full UIP suite: 1,242 passed, 1 existing warning.

Permanent evidence:

`docs/project_control/generated/metals_a1_integration/metals_a1_integration_certification.json`

Disposition:

`UIP_METALS_A0_A1_CERTIFIED_COMPLETE`

Active next milestone:

`UIP_CRYPTO_A0_A1_DOMAIN_BINDING`

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
7. `UIP-R2` - perform real refreshed-data rehearsals for MTG, Metals, and Crypto.
8. `UIP-R3` - certify output rationality, domain health, anomaly routing, and decision readiness without creating cross-asset ranking or allocation policy.
9. `UIP-E1` - establish the future Stocks/ETF extension boundary.
10. `UIP-DASH-1` and `UIP-DASH-2` - build the dashboard on certified multi-domain inputs.
11. Govern future cross-asset ranking, comparison, or allocation methodology separately.

No universal cross-asset ranking is authorized by this sequence.
Automatic purchase execution remains disabled.

## State principle

> UIP recovery history remains preserved, but current integration proceeds from certified repository and domain-package authority. Each domain retains its native semantics; UIP may accept certified outputs, preserve lineage, orchestrate governed refreshes, and present evidence without silently redefining native models, ranks, recommendations, or execution authority.

## UIP-CRYPTO-A0/A1 certification closeout

Crypto source authority:

`951ca1111ef844a651eb6e12299441252ef5f56b`

UIP integration base:

`398f949dee1f6af76d7823f07f61c628fab1ca57`

Certification evidence:

- status: `UIP_CRYPTO_A1_INTEGRATION_CERTIFICATION_PASS`;
- contract version: `1.0.0`;
- adapter version: `1.0.0`;
- observed current assets: 6;
- forecasts: 132;
- platform-status rows: 1;
- portfolio-position rows: 0;
- recommendations: 6;
- risk metrics: 6;
- total imported rows: 151;
- package population treated as permanent: false;
- package integrity and manifest SHA-256 validation: pass;
- canonical Crypto identities preserved: true;
- native recommendation labels preserved: true;
- `WAIT` normalized to universal `watch`: true;
- `AVOID` normalized to universal `sell`: true;
- missing holdings preserved as absent: true;
- holdings synthesized: false;
- lineage complete: true;
- duplicate replay rejected: true;
- Crypto source database remained read-only: true;
- Crypto native model changed: false;
- cross-asset ranking created: false;
- automatic purchase execution created: false;
- focused Crypto A1 tests: 4 passed;
- full UIP suite: 1,246 passed, 1 existing warning.

Permanent evidence:

`docs/project_control/generated/crypto_a1_integration/crypto_a1_integration_certification.json`

Regression protection:

`tests/test_crypto_a1_certification_evidence.py`

Disposition:

`UIP_CRYPTO_A0_A1_CERTIFIED_COMPLETE`

Active next milestone:

`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`

## UIP-D1 certification closeout

D1 status:

`UIP_D1_COMMON_DOMAIN_REGISTRY_AND_LINEAGE_CERTIFICATION_PASS`

Certified implementation commit:

`9a1f011cb92069069f54967442bbf3d6d0ea281c`

Certified authority and controls:

- canonical registry authority: `foundation/import_engine/sql/006_common_domain_registry_lineage.sql`;
- certified domains: MTG, Metals, Crypto;
- fresh canonical databases initialize the registry automatically;
- Python domain-registry access is read-only and unknown domains fail closed;
- native domain semantics remain authoritative;
- permanent asset-population counts are not stored;
- common lineage preserves import, package, source-file, source-row, manifest, and import-time evidence;
- MTG native authority is included without flattening native ranking or purchase semantics;
- canonical migrations: 001 through 006;
- canonical database objects: 31;
- D1 schema objects: 4;
- focused D1 tests: 5 passed;
- migration tests: 5 passed;
- combined D1/schema tests: 10 passed;
- full UIP suite: 1,251 passed, 1 existing warning;
- production UIP database modified: false;
- native domain databases modified: false;
- cross-asset ranking created: false;
- allocation policy created: false;
- automatic purchase execution created: false.

Permanent evidence:

`docs/project_control/generated/d1_common_domain_registry/d1_common_domain_registry_certification.json`

Regression protection:

`tests/test_d1_certification_evidence.py`

Disposition:

`UIP_D1_CERTIFIED_COMPLETE`

Active next milestone:

`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACTS`

## UIP-R1 certification closeout

R1 status:

`UIP_R1_REFRESH_AND_ORCHESTRATION_CONTRACT_CERTIFICATION_PASS`

Governed main base:

`55d5c72582bf70aff21a30b69edadab9ea9e8553`

Technical contract head before certification evidence:

`026169f85f411c4b76061a5c9e4b42de944efba4`

Certified authority and controls:

- machine-readable contract: `config/orchestration/r1_domain_refresh_contracts.json`;
- typed fail-closed interface: `foundation/orchestration/refresh_contracts.py`;
- human-readable contract: `docs/project_control/R1_REFRESH_ORCHESTRATION_CONTRACT.md`;
- certified domains: MTG, Metals, Crypto;
- required cycle evidence fields: 19;
- external domains use source-owned GitHub workflow dispatch;
- UIP direct invocation of external collectors remains prohibited;
- Metals remains UIP-native and uses its canonical production entrypoint;
- failed refresh cycles preserve the latest certified UIP state;
- partial activation is prohibited;
- missing authority may not be synthesized;
- current asset populations are not permanent constants;
- MTG refreshed-delivery compatibility remains an explicit R2 proof requirement;
- R1 focused tests: 5 passed;
- certified-domain regression tests: 18 passed;
- pre-certification full UIP suite: 1,260 passed, 1 existing warning;
- validation left the R1 worktree clean;
- fresh domain outputs certified by R1: false;
- real refreshed-data rehearsal performed by R1: false;
- production UIP database activation performed by R1: false;
- native domain models changed: false;
- cross-asset ranking authorized: false;
- allocation policy authorized: false;
- automatic execution authorized: false.

Permanent evidence:

`docs/project_control/generated/r1_refresh_orchestration/r1_refresh_orchestration_certification.json`

Regression protection:

`tests/test_r1_certification_evidence.py`

Disposition:

`UIP_R1_CERTIFIED_COMPLETE`

Active next milestone:

`UIP_R2_REFRESHED_DATA_REHEARSAL`

Expected following milestone:

`UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW`

R3 is a hard gate before E1 or dashboard decision logic. It evaluates fresh-output freshness/completeness, native self-consistency, distributions/outliers, change-from-prior plausibility, UIP semantic preservation, decision readiness, and investigation routing. R3 does not authorize cross-asset ranking or allocation.
