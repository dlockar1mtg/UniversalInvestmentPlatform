# UIP DASH-READ-1 Certification

Status: `CERTIFIED_COMPLETE`

Milestone:

`DASH_READ_1_CERTIFIED_PRESENTATION_READ_MODEL_PUBLICATION_CONTRACT`

## Certified source authority

Authoritative UIP database classification:

`AUTHORITATIVE_MULTI_DOMAIN_PRODUCTION_STATE_R3_CERTIFIED`

Authoritative database SHA-256:

`9af5e52882bdf61fed550a2ced9bc83ba1529c422633a7817660cf61d0e15a98`

DASH-READ-1 modified the analytical database:

`FALSE`

## Certified presentation publication

Active publication ID:

`dash-read-1-r3-certified-postgres-9af5e52882bd`

Publication version:

`1.0.0`

Content fingerprint:

`cc3ab02cf9e7411641e384d27fd2ec48bf687ec98d7fa191ddcc6ff3b768bd3f`

Active record count:

`4031`

The publication was built from the certified R3 DuckDB authority, staged in PostgreSQL/Neon, validated, and activated through an atomic active-publication pointer. An intentionally invalid replacement was rejected without displacing the last-good active publication. Existing non-presentation application tables remained preserved.

## Certified presentation populations

| Domain | Asset | Health | Forecast | Recommendation | Risk | Native authority |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Crypto | 6 | 1 | 120 | 6 | 6 | — |
| Metals | 16 | 1 | 16 | 12 | 11 | — |
| MTG | 968 | 1 | 931 | 968 | — | 968 |

MTG remains native-authority driven. Generic MTG analytical current authority remains suppressed.

## Render presentation read API

Authenticated active-publication-only endpoints:

- `GET /v1/presentation/status`
- `GET /v1/presentation/domain-health`
- `GET /v1/presentation/recommendations`
- `GET /v1/presentation/assets/{domain_id}/{asset_id}`
- `GET /v1/presentation/lineage/{domain_id}/{asset_id}`

## Final closure evidence

PR #46 merged to `main` at:

`497e92f4c49b2ce84413035840e74305e92bbaed`

Post-merge GitHub CI and Container Delivery passed. Render deployed the merged commit successfully.

Hosted Render certification then proved:

- `/health/live` returned `LIVE`;
- `/health/ready` returned `READY`;
- unauthenticated presentation access returned the governed `UNAUTHENTICATED` error;
- the active publication ID, source SHA, fingerprint, status, and 4,031 record count matched certified authority;
- Crypto, Metals, and MTG domain-health surfaces were readable and certified;
- recommendation counts were Crypto `6`, Metals `12`, MTG `968`;
- no Crypto/Metals cross-domain rank was exposed;
- MTG native ranks remained available;
- MTG automatic purchase execution remained `FALSE`;
- MTG asset detail and lineage were readable through the hosted Render endpoints;
- the uncertified future `stocks` domain failed closed with `INVALID_DOMAIN`;
- the authoritative DuckDB remained byte-identical after hosted certification.

## Governance invariants preserved

DASH-READ-1 does not authorize or create:

- universal cross-domain ranking;
- cross-domain investment weights;
- automatic purchase or sale execution;
- synthesized Crypto or Metals current prices;
- replacement of missing authority with zero, WAIT, HOLD, worst rank, or other fabricated values;
- independent analytical recomputation in Render.

The PostgreSQL presentation store is a versioned projection only. Certified UIP/domain outputs remain analytical authority.

## Regression evidence

Focused final regression before PR review:

`28 passed`

One non-blocking `StarletteDeprecationWarning` was observed for the current FastAPI/Starlette TestClient dependency. It does not affect semantic or authority certification.

## Disposition

`DASH_READ_1_CERTIFIED_COMPLETE`

DASH-READ-1 is closed. The next governed milestone is:

`DASH_SHELL_1_APPROVED_V7_APPLICATION_SHELL`
