# Universal Investment Platform — Active Roadmap

## Priority sequence

1. Preserve the certified R3 multi-domain analytical foundation.
2. Preserve the approved Dashboard Product Specification V1 and V7 visual target.
3. Build the dashboard product on the certified hosted presentation/read-model boundary.
4. Complete transaction, portfolio, recommendation, refresh, and operations workflows.
5. Add Stocks/ETF through the approved domain-neutral contracts.
6. Complete end-to-end dashboard certification.
7. Finalize remote production infrastructure and laptop-independent operation.

## Dashboard-first product interlock

Approved product specification:

`docs/project_control/UIP_DASHBOARD_PRODUCT_SPEC_V1.md`

Approved V7 visual acceptance record:

`docs/project_control/UIP_DASHBOARD_V7_VISUAL_ACCEPTANCE.md`

Approved primary navigation:

`Home | Recommendations | Portfolio | Transactions | Refresh | Operations`

Mandatory product constraints:

- domain-native recommendation, rank, forecast, and risk semantics;
- missing stays missing;
- no universal cross-domain ranking or allocation policy;
- no automatic trading;
- append-only transaction corrections;
- pricing and basis coverage visibility;
- fail-closed refresh with last-good-state preservation;
- future Stocks/ETF extensibility without redesigning the shell.

## Dashboard implementation sequence

1. `DASH-READ-1` — certified presentation/read-model publication contract — **CERTIFIED COMPLETE**.
2. `DASH-SHELL-1` — application shell, authentication, six-screen navigation, persistent status — **CURRENT**.
3. `TXN-1` — append-only user transaction ledger.
4. `PORT-1` — holdings, basis, P/L, pricing coverage, portfolio history.
5. `REC-UI-1` — domain-native recommendation and asset-detail experience.
6. `REFRESH-UI-1` — refresh/data-health orchestration experience.
7. `OPS-1` — preserve and move existing Render technical dashboard capability under Operations.
8. `UIP_E1_STOCKS_ETF_EXTENSION_BOUNDARY` — integrate Stocks/ETF against the approved contracts.
9. `DASH-CERT-1` — end-to-end Render usability and authority certification.

## Completed foundation

The following milestones are complete and must not be reopened without a new governed reason:

- project-control/recovery stabilization;
- UIP universal-core stabilization;
- MTG A1/A2 integration certification;
- Metals A0/A1 integration certification;
- Crypto A0/A1 integration certification;
- D1 common domain registry and lineage;
- R1 refresh/orchestration contracts;
- R2 refreshed-data rehearsal;
- R3 Metals rationality/domain health;
- R3 MTG rationality/domain health;
- R3 cross-domain reconciliation and closeout;
- Dashboard Product Specification V1 approval;
- Dashboard V7 visual acceptance approval;
- DASH-READ-1 hosted presentation/read-model certification.

## DASH-READ-1 permanent authority

Status:

`DASH_READ_1_CERTIFIED_COMPLETE`

Permanent evidence:

- `docs/project_control/DASH_READ_1_CERTIFICATION.md`
- `docs/project_control/generated/dash_read_1/dash_read_1_certification.json`

Merged production commit:

`497e92f4c49b2ce84413035840e74305e92bbaed`

Active hosted publication:

- ID: `dash-read-1-r3-certified-postgres-9af5e52882bd`
- version: `1.0.0`
- fingerprint: `cc3ab02cf9e7411641e384d27fd2ec48bf687ec98d7fa191ddcc6ff3b768bd3f`
- records: `4031`
- source authority SHA-256: `9af5e52882bdf61fed550a2ced9bc83ba1529c422633a7817660cf61d0e15a98`

Hosted Render certification proved `LIVE`, `READY`, authenticated active-publication reads, certified three-domain health, expected recommendation populations, asset detail, lineage, native MTG semantics, fail-closed unauthenticated access, and rejection of the uncertified Stocks domain.

## Current milestone — DASH-SHELL-1

Milestone:

`DASH_SHELL_1_APPROVED_V7_APPLICATION_SHELL`

Authorized objective:

Implement the approved V7 application shell on Render using the certified DASH-READ-1 presentation boundary.

Authorized scope:

- replace the current `/dashboard` landing experience with the approved V7 application shell;
- preserve the approved six-screen navigation;
- implement persistent global UIP health/freshness status;
- preserve viewer/operator authentication boundaries;
- implement responsive desktop/mobile shell behavior;
- use real DASH-READ-1 status/domain-health data where already supported;
- use explicit empty or future-work states for TXN-1, PORT-1, REC-UI-1, REFRESH-UI-1, and E1-owned features rather than fabricating values;
- preserve existing technical operational functionality for later placement under Operations.

DASH-SHELL-1 does **not** authorize:

- transaction-ledger accounting;
- cost-basis/P&L derivation;
- universal recommendation normalization;
- refresh execution changes;
- ETF/Stocks analytical authority;
- synthetic Crypto/Metals current prices;
- automatic purchases or sales.

Completion gate:

`DASH_SHELL_1_CERTIFIED`

## Remaining domain work

Stocks/ETF remains the next new analytical domain after the core dashboard workflow milestones. It must register through the approved read-model/dashboard contracts and may not redefine the application shell.

Other possible later domains remain Acorns, Housing, Macro, and cash/cash equivalents, each subject to separate authority, contract, lineage, and certification.

## Final infrastructure sequence

Only after the dashboard is a known functioning, certified product should final infrastructure selection/hardening be completed. Final certification must prove source refresh, publication, imports, analytics, recommendations, dashboard, transactions, lineage, roles, backups, recovery, failure handling, remote operation, and laptop independence.

Final gate:

`UIP_REMOTE_PRODUCTION_CERTIFIED`

## Current position

Active phase:

`Dashboard product implementation on certified hosted authority`

Current milestone:

`DASH_SHELL_1_APPROVED_V7_APPLICATION_SHELL`

Current certified multi-domain production baseline:

`9af5e52882bdf61fed550a2ced9bc83ba1529c422633a7817660cf61d0e15a98`

Current implementation branch:

`phase-uip-dash-shell-1`

Next authorized action:

`IMPLEMENT_DASH_SHELL_1_APPROVED_V7_APPLICATION_SHELL`

## Recovery restriction

No recovered branch may be merged wholesale solely to accelerate the roadmap. No destructive recovery cleanup is authorized by dashboard work. Protected local recovery resources remain untouched.
