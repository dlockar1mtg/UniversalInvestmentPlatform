# UIP DASH-READ-1 Certification

Status: `PASS_FOR_PR_REVIEW`

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

The publication was built from the certified R3 DuckDB authority, staged in PostgreSQL/Neon, validated, and activated through an atomic active-publication pointer.

An intentionally invalid replacement missing Metals domain health was rejected before staging. The existing active publication remained unchanged. Existing non-presentation application tables remained preserved.

## Certified presentation populations

| Domain | Asset | Health | Forecast | Recommendation | Risk | Native authority |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Crypto | 6 | 1 | 120 | 6 | 6 | — |
| Metals | 16 | 1 | 16 | 12 | 11 | — |
| MTG | 968 | 1 | 931 | 968 | — | 968 |

MTG remains native-authority driven. The presentation layer does not repopulate generic MTG analytical authority.

## Render presentation read API

The implemented hosted read boundary exposes the active presentation publication through authenticated viewer/operator access:

- `GET /v1/presentation/status`
- `GET /v1/presentation/domain-health`
- `GET /v1/presentation/recommendations`
- `GET /v1/presentation/assets/{domain_id}/{asset_id}`
- `GET /v1/presentation/lineage/{domain_id}/{asset_id}`

The real Neon rehearsal proved that the read repository returns:

- exactly three certified domain-health records: Crypto, Metals, MTG;
- 6 Crypto recommendations;
- 12 Metals recommendations;
- 968 MTG recommendations;
- MTG native rank/status semantics;
- asset detail from the active publication;
- lineage/provenance from the active publication.

## Governance invariants preserved

DASH-READ-1 does not authorize or create:

- universal cross-domain ranking;
- cross-domain investment weights;
- automatic purchase or sale execution;
- synthesized Crypto or Metals current prices;
- replacement of missing authority with zero, WAIT, HOLD, worst rank, or other fabricated values;
- independent analytical recomputation in Render.

The PostgreSQL presentation store is a versioned projection only. Certified UIP/domain outputs remain analytical authority.

## Focused regression

The final local regression gate passed:

`28 passed`

One non-blocking `StarletteDeprecationWarning` was observed for the current FastAPI/Starlette TestClient dependency. It does not change DASH-READ-1 semantic or authority certification.

## Repository state at rehearsal

Certified implementation HEAD before permanent evidence commits:

`350ef7e7fba3c9493484e7ce61b95acadf7b44a7`

Main merge base:

`bb26db207b717ccaae44937c7d8b22cea4f8f6b5`

The branch was 15 commits ahead and 0 behind main before certification evidence was added.

## Disposition

DASH-READ-1 implementation is certified for pull-request review.

Final milestone closure still requires:

1. PR CI PASS;
2. merge to `main`;
3. post-merge Render deployment;
4. authenticated hosted endpoint certification against the active Neon publication.

Next gate:

`PR_CI_AND_POST_MERGE_RENDER_ENDPOINT_CERTIFICATION`
