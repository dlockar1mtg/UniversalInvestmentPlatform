# Metals Vehicle Evidence Authority Design V1

## Objective

Create the governed evidence layer required by `UIP_NATIVE_METALS_VEHICLE_RANKING_V1` before UIP may identify a preferred implementation vehicle for an attractive commodity thesis.

The commodity thesis remains upstream authority. This evidence layer is vehicle-specific implementation research only.

## Eligible universe

Only enabled commodity implementation vehicles in `config/metals/vehicles.json` are in scope:

- Gold: GLD, IAU, SGOL
- Silver: SLV, SIVR
- Platinum: PPLT
- Copper: CPER, COPX
- Uranium: URA, URNM

BIL remains a reserve reference and is excluded from commodity implementation ranking.

## Evidence family 1 — registered exposure

Registry identity and structure are authoritative for vehicle mapping. Required fields are vehicle id, ticker, underlying commodity, vehicle type, role, and enabled state.

No miner or thematic-equity vehicle may be relabeled as direct commodity exposure.

## Evidence family 2 — recurring cost

Expense ratio or equivalent recurring fund cost must come from authoritative issuer documentation when practical.

Required provenance:

- expense ratio percentage;
- effective/as-of date;
- exact source URL;
- retrieval timestamp;
- source-document hash.

A missing or stale cost value remains missing. UIP may not infer cost from another share class or substitute a third-party estimate when issuer authority is required.

## Evidence family 3 — liquidity and implementation friction

Liquidity evidence must come from a governed market-data source.

V1 requires:

- 30-session average dollar volume;
- 20-session median quoted bid/ask spread in basis points;
- as-of date;
- source authority;
- observation count.

Daily trading volume is not a substitute for quoted bid/ask spread. A missing spread remains missing.

## Evidence family 4 — tracking quality

Tracking evidence is exposure-structure aware.

- physical-backed ETFs may be compared with the governed commodity benchmark when histories are methodologically compatible;
- futures funds require a governed futures-index benchmark rather than spot being silently substituted;
- miners ETFs and thematic equity ETFs are structurally indirect and receive `NOT_APPLICABLE_INDIRECT_EXPOSURE`, not a synthetic commodity tracking score;
- if the required benchmark is unavailable, use `UNAVAILABLE_MISSING_BENCHMARK`.

When available, V1 uses a 252-session window and retains annualized tracking error, return correlation, observation count, benchmark identity, and as-of date.

## Evidence family 5 — vehicle Risk V1

Existing `UIP_NATIVE_METALS_RISK_V1` remains the vehicle risk authority. Required fields are volatility, downside volatility, maximum drawdown, value at risk, lookback observations, and methodology version.

Vehicle risk never becomes commodity risk.

## Freshness

- recurring cost: no more than 120 days old;
- liquidity and spread: no more than 7 days old;
- tracking quality: no more than 7 days old;
- vehicle Risk V1: no more than 14 days old.

Stale evidence fails closed and must be surfaced as stale rather than silently reused.

## Ranking-readiness gate

`VEHICLE_RANKING_EVIDENCE_READY` requires complete, current required evidence for every enabled vehicle being compared inside one commodity group.

Otherwise the state is `VEHICLE_RANKING_EVIDENCE_INCOMPLETE` and the dashboard may list implementation options but may not name a preferred vehicle.

For single-vehicle Platinum, PPLT may be shown as `ONLY_REGISTERED_IMPLEMENTATION` once its required evidence is complete; this is not a comparative ranking claim.

## Current source-state decision

The current source set already provides registry identity, current price/history, and Risk V1. It does not yet provide certified issuer cost evidence, governed bid/ask spread evidence, or complete governed tracking-quality evidence.

Therefore preferred vehicle ranking remains fail-closed until those evidence families are collected and certified.

## Next governed execution sequence

1. Build a read-only issuer-cost collection rehearsal for the registered vehicle universe.
2. Build a read-only liquidity/spread source rehearsal with explicit source authority and windows.
3. Build tracking-quality evidence only where the exposure structure permits it; retain explicit N/A states for indirect equity vehicles.
4. Audit freshness, completeness, provenance, and exact vehicle coverage.
5. Only after all evidence gates pass, run a read-only `UIP_NATIVE_METALS_VEHICLE_RANKING_V1` rehearsal.
6. Only after ranking rehearsal passes may the dashboard display `PREFERRED IMPLEMENTATION CANDIDATE`.

## Forbidden behavior

This authority prohibits:

- using representative test scores as live evidence;
- inventing missing issuer cost;
- treating volume as a bid/ask spread proxy;
- comparing CPER to spot copper when its governed futures benchmark is unavailable;
- manufacturing tracking scores for COPX, URA, or URNM as if they were direct commodity vehicles;
- projecting vehicle risk to the commodity;
- projecting commodity expected return to a vehicle as a vehicle-specific forecast;
- automatic execution, position sizing, or portfolio allocation;
- restoring publication automation solely because this design exists.
