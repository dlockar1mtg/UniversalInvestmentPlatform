# R4 Refresh Operations

Status: refresh rehearsals certified for Crypto, Metals, and MTG.

## Production refresh authority

Recurring domain refresh is owned by GitHub Actions. A local workstation is not required for scheduled production refreshes.

Refresh is not retraining. Scheduled refreshes may collect current source data, append governed history, rerun already-certified forecast/recommendation logic, produce certified delivery packages, and publish evidence. Model retraining or methodology changes require separate authorization.

## Locked cadence

| Domain | Workflow | Cadence |
| --- | --- | --- |
| Crypto | `Crypto Production Cycle` | Mon-Sat 11:15 UTC normal refresh; Sunday 10:45 UTC full provider refresh |
| Metals | `Metals Production Cycle` | Daily 12:23 UTC |
| MTG | `MTG Marketplace Production` | Daily 12:15 UTC bounded live marketplace refresh |
| MTG | `MTG Full Marketplace Universe` | Sunday 11:30 UTC full marketplace-universe refresh |

Schedule changes require a governed pull request.

## R4 rehearsal evidence

- Crypto: GitHub Actions run `34247105467`, `main` SHA `1bdbeb1b57087b25b0e7004945585e352be14f0c`, success.
- Metals: GitHub Actions run `34255762792`, `main` SHA `6ca4427d756a8b6df458c69f4bb049e3bdd90101`, success.
- MTG daily marketplace: GitHub Actions run `34256278555`, `main` SHA `cc7a78f2fc222ef1dadd769e5477896dda950819`, success.

The machine-readable operating authority is `config/orchestration/r4_refresh_operations_registry.json`.

## Observability requirement

R4-E must make operational health visible without requiring routine log inspection. At minimum, each completed domain must expose:

- last run status;
- last run start/completion time;
- last successful refresh time;
- freshness state;
- artifact/package reference;
- concise failure summary when unhealthy;
- next scheduled run time.

Domain-specific health must also remain visible: provider health for Crypto, source/forecast/package readiness for Metals, and marketplace/certification/delivery coverage for MTG.

A failed or stale domain must be visibly marked as failed or stale. Silent fallback that makes stale data appear current is forbidden.

## Remaining gate

R4-D is complete when this cadence registry is merged. R4-E remains open until the dashboard/read model exposes the required operational health fields.

Cross-asset ranking, allocation policy, and automatic purchase execution remain outside this milestone and are not authorized by refresh operations.
