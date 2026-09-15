# Metals Vehicle Ranking Authority Design V1

## Objective

Create a bounded, vehicle-specific implementation authority that can answer:

> The upstream commodity thesis is actionable. Of the registered vehicles for that commodity, which exact instrument is the strongest implementation candidate, and why?

The commodity thesis remains the upstream investment authority. Vehicle ranking is downstream implementation research only and may not create, replace, strengthen, weaken, or override the commodity recommendation.

## Authority identity

- authority id: `UIP_NATIVE_METALS_VEHICLE_RANKING_V1`
- schema version: `1.0.0`
- methodology version: `1.1.0`
- scope: `REGISTERED_METALS_IMPLEMENTATION_VEHICLES_ONLY`
- ranking grain: one row per registered enabled vehicle, grouped within one underlying commodity
- cross-domain ranking: prohibited
- automatic execution: prohibited
- position sizing / portfolio allocation: prohibited

## Eligible universe

Only enabled vehicles in `config/metals/vehicles.json` may enter the ranking.

Current registered commodity mappings:

| Commodity | Vehicles | Exposure form |
| --- | --- | --- |
| Gold | GLD, IAU, SGOL | physical-backed ETF |
| Silver | SLV, SIVR | physical-backed ETF |
| Platinum | PPLT | physical-backed ETF |
| Copper | CPER, COPX | futures fund; miners ETF |
| Uranium | URA, URNM | thematic/miners equity ETF |

Aluminum, Nickel, Zinc, and Tin currently have no registered implementation vehicle and therefore remain `IMPLEMENTATION_UNAVAILABLE`.

`BIL` is the tactical-reserve reference and is excluded from commodity implementation ranking.

## Required evidence families

A preferred-vehicle result is authorized only when all required evidence is present for every compared vehicle in that commodity group.

1. **Exposure fidelity**
   - authoritative registry vehicle type and underlying commodity mapping;
   - direct physical/futures exposure is distinguished from miners/thematic equity exposure;
   - no vehicle type is relabeled as direct commodity exposure.

2. **Cost**
   - current certified expense ratio or equivalent recurring fund cost;
   - source and as-of date required.

3. **Liquidity / implementation friction**
   - current certified average dollar volume;
   - current certified bid/ask spread measure;
   - observation window and as-of date required.

4. **Risk efficiency**
   - current certified vehicle Risk V1 evidence;
   - annualized volatility;
   - downside volatility;
   - maximum drawdown;
   - value at risk;
   - lookback count and methodology version retained.

## Tracking-quality treatment

Tracking quality is no longer a required ranking component in methodology version `1.1.0`.

Reason: the exact benchmark identities are governed, but the historical LBMA and SummerHaven benchmark series needed for defensible 252-session calculations require separate authorized/licensed access that is not part of the UIP data path. UIP will not weaken the standard by substituting spot prices, front-month futures, peer ETFs, or scraped secondary proxies.

If exact authorized benchmark histories become available later, tracking-quality evidence may be displayed as an **optional informational field** under its separately governed methodology. It may not silently change a live ranking score without a future methodology-version change and audit.

## Score design

When all required evidence is present, the bounded implementation score is 0-100 with these weights:

- exposure fidelity: **35%**
- cost efficiency: **25%**
- liquidity / implementation friction: **25%**
- risk efficiency: **15%**

The four component scores must be independently visible in the presentation. UIP must never expose only an opaque total score.

### Exposure fidelity

Exposure fidelity is categorical and reflects registered vehicle structure rather than recent performance:

- physical-backed ETF: highest direct-fidelity class for precious metals;
- futures fund: direct commodity implementation class, with explicit futures-roll caveat;
- miners ETF / thematic equity ETF: indirect equity implementation class;
- cash proxy: excluded from commodity ranking.

The exact numeric mapping is versioned in the ranking configuration and cannot change without a methodology-version change.

### Cost efficiency

Lower certified recurring cost is better within the compared commodity group. Missing cost fails the preferred-vehicle gate; it is not treated as zero.

### Liquidity / implementation friction

Higher average dollar volume and lower certified bid/ask spread are better. Missing ADV or spread fails the preferred-vehicle gate.

### Risk efficiency

Lower vehicle-specific volatility, downside volatility, drawdown magnitude, and VaR are better, using only current certified Risk V1 evidence. Vehicle risk never becomes commodity risk.

## Preferred-vehicle gate

UIP may label one vehicle `PREFERRED IMPLEMENTATION CANDIDATE` only when:

- the upstream commodity recommendation is actionable under its own authority;
- at least two registered vehicles exist for the commodity, unless the single-vehicle case is explicitly labeled `ONLY_REGISTERED_IMPLEMENTATION` rather than ranked;
- all required four-factor evidence is complete and current for every compared vehicle;
- every required component can be scored without synthetic missing values;
- no tied total score remains after deterministic tie-break rules;
- the ranking audit status is PASS.

If required evidence is missing, the commodity page may still list registered vehicles, but the result must be `PREFERRED_VEHICLE_NOT_CERTIFIED` and show the missing evidence categories.

## Tie-break policy

For an exact total-score tie, apply in order:

1. higher exposure-fidelity component;
2. lower certified bid/ask spread;
3. lower certified recurring cost;
4. lower maximum drawdown magnitude;
5. lexical ticker order only as a deterministic display fallback, never as an economic claim.

## Current evidence state

As of the post-PR-142 source set:

- registered exposure type: complete for all 10 implementation vehicles;
- certified recurring cost: complete for all 10;
- certified 30-session average dollar volume: complete for all 10;
- certified 20-session Alpaca SIP quoted spread: complete for all 10;
- certified vehicle Risk V1: complete for all 10;
- exact tracking benchmark identities: governed, but benchmark history access is not certified and is therefore optional / non-scoring under methodology v1.1.0.

This methodology change does **not** itself authorize a live preferred-vehicle result. A separate bounded ranking rehearsal and audit must prove the four-factor calculations before any preferred label can be published.

## Presentation contract

Once separately certified, a commodity detail page should present:

- commodity thesis and rich commodity evidence first;
- `Ways to invest in <commodity>` second;
- each vehicle's ticker, name, exposure type, current price, cost, liquidity, and Risk V1 evidence;
- optional tracking information only if exact authorized benchmark evidence is available;
- component scores and total implementation score where authorized;
- one `PREFERRED IMPLEMENTATION CANDIDATE` only when the gate passes;
- rationale explaining why the preferred vehicle leads;
- caveats for indirect exposure such as miners/thematic equity vehicles.

## Forbidden behavior

This authority explicitly prohibits:

- copying representative test scores into live ranking authority;
- using vehicle returns to manufacture commodity forecasts;
- using vehicle Risk V1 as commodity risk;
- projecting commodity expected return onto a vehicle as a vehicle-specific forecast;
- filling missing required cost, liquidity, spread, or risk evidence with zero/default values;
- substituting unauthorized tracking proxies into either the score or presentation as if they were exact benchmark tracking;
- ranking vehicles across different commodities;
- automatic execution, position sizing, or portfolio allocation;
- restoring the central publication cron solely because this design exists.

## Next gate

Implement a bounded read-only four-factor ranking rehearsal using only certified evidence already present in UIP. The rehearsal must emit full component calculations, deterministic tie-break evidence, provenance, and a fail-closed audit. It must not publish preferred labels or modify production state until separately certified.