# Metals Vehicle Implementation Projection V1

## Purpose

Create a fail-closed presentation projection that turns already-certified Metals vehicle ranking evidence and presentation authorization into commodity-scoped implementation records.

This is the read-model data primitive for the future `Ways to invest in <commodity>` dashboard section. It does not change commodity recommendations and does not publish or activate production state by itself.

## Governing inputs

The projection consumes only committed authorities:

- `config/presentation/metals_vehicle_presentation_authorization_v1.json`
- `config/presentation/metals_vehicle_ranking_evidence_v1.json`
- `config/presentation/metals_vehicle_cost_evidence_snapshot_v1.json`
- `config/metals/vehicles.json`

No network collection is performed.

## Output

The projection emits exactly ten `metals_vehicle_implementation` presentation records, attached to the canonical commodity asset id rather than rewriting vehicle source identities.

Certified commodity ordering is preserved:

- Gold: `GLD > SGOL > IAU`
- Silver: `SLV > SIVR`
- Platinum: `PPLT`
- Copper: `COPX > CPER`
- Uranium: `URA > URNM`

Each record includes governed vehicle identity, exposure type, role, official URL, within-commodity rank, certified implementation score when applicable, certified recurring cost evidence, upstream commodity recommendation/tactical state, and the exact presentation label if authorized.

## Presentation labels

The projection may emit `PREFERRED_IMPLEMENTATION_CANDIDATE` only for:

- Gold / GLD
- Copper / COPX
- Uranium / URA

Platinum / PPLT emits `ONLY_REGISTERED_IMPLEMENTATION`.

Silver is explicitly fail-closed: the certified `SLV > SIVR` ordering remains available as implementation research, but no `PREFERRED_IMPLEMENTATION_CANDIDATE` label is emitted while Silver is `REDUCE` / `TACTICAL_DEFENSIVE`.

## Fail-closed checks

Projection fails if any of the following occurs:

- authority ids do not match expected governed authorities;
- ranking artifact digest no longer matches authorization;
- registered ranked ticker set is not exactly the governed ten;
- cost evidence is incomplete for any ranked vehicle;
- ranking and authorization commodity groups differ;
- certified ordering differs between ranking evidence and presentation authorization;
- an authorized preferred vehicle is not the certified leader;
- an upstream non-actionable commodity attempts to receive a preferred label;
- a vehicle appears in more than one commodity group;
- central publication cron restoration or automatic execution authority appears.

## Non-authorizations

This change does not authorize:

- production publication persistence or activation;
- dashboard code changes yet;
- commodity recommendation changes;
- cross-commodity ranking;
- portfolio allocation;
- position sizing;
- automatic execution;
- source collection schedule changes;
- central publication cron restoration.

The central publication cron remains paused.

## Next gate

After CI and merge, include these ten records in the read-only rich publication candidate rehearsal and verify that commodity asset detail surfaces return the implementation records with exact Gold, Silver, Platinum, Copper, and Uranium semantics. Only after that audit should the dashboard UI render the new implementation section.
