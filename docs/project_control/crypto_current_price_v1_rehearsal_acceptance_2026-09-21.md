# Crypto Current Price V1 — complete candidate acceptance

- Rehearsal: https://github.com/dlockar1mtg/UniversalInvestmentPlatform/actions/runs/35645958756 (run 6, workflow_dispatch, success).
- Rehearsed UIP head: `eecf7a98056e0f03c582328229b9b7cb64b5d1f9`.
- Evidence artifact: `10660093181`, SHA-256 `1774b48586c4eb72c13871148260bf1b1a63fe783e599933c15a276ee9556221`.
- Verified record count: **14,309**. This count is taken from the full rehearsal, not inferred from the prior publication.
- Crypto current-price records: 6; Metals rich families: 11; Metals implementation records: 10; all five MTG research family counts passed.
- Source contract status: PASS for both Metals and MTG. No PostgreSQL connection, staging, persistence, activation, schedule change, or cron restoration occurred.

## Exact production inputs

| Domain | Source run | Source head |
| --- | --- | --- |
| Crypto | 35628894423 | 924c675bcebe1b7a6f14477a0a432fe43255e6b0 |
| Metals | 35637019717 | 6b6d3f30df8739967c91de226b57c98a77fd4e91 |
| MTG | 35637210918 | 2e8b1a77c1bdd3b79141fffc94f84d91222e4266 |

MTG research checkout was `2e8b1a77c1bdd3b79141fffc94f84d91222e4266`, confirmed in the rehearsal checkout log. Source run identities were confirmed in the download log. Crypto artifact ID/digest and its six-row CSV hash remain pinned by the workflow and projection validator.

## Publication boundary

This change updates only the manual publication source-run/count pins and their existing tests. The shared candidate composition and semantic validation code are unchanged from the successful rehearsal. Exact-head CI must pass before merge. Manual production publication must then pass its preactivation gates; hosted Portfolio acceptance remains outstanding until Bitcoin pricing, 24/24 coverage, complete market value, and total-return availability are verified.

Central publication cron remains paused. No execution, trade sizing, allocation, or cross-domain ranking authority is granted.
