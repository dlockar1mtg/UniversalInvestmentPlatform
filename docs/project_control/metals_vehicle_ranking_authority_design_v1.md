# Metals Vehicle Ranking Authority Design V1

## Objective

Create a bounded, vehicle-specific implementation authority that can answer a question such as:

> Gold is attractive. Of the registered Gold vehicles, which exact instrument is the strongest implementation candidate, and why?

The commodity thesis remains the upstream investment authority. This ranking is downstream implementation research only. It may compare vehicles that are already registered to the same commodity, but it may not create, replace, strengthen, weaken, or override the commodity recommendation.

## Authority identity

- authority id: `UIP_NATIVE_METALS_VEHICLE_RANKING_V1`
- schema version: `1.0.0`
- methodology version: `1.0.0`
- scope: `REGISTERED_METALS_IMPLEMENTATION_VEHICLES_ONLY`
- ranking grain: one row per registered enabled vehicle, grouped within one underlying commodity
- cross-domain ranking: prohibited
- automatic execution: prohibited
- position sizing / portfolio allocation: prohibited

## Eligible universe

Only enabled vehicles in `config/metals/vehicles.json` may enter the ranking.

Current registered commodity mappings are:

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

4. **Tracking quality**
   - certified tracking-error or equivalent benchmark-fidelity measure against the governed underlying commodity benchmark where such a comparison is methodologically valid;
   - miners/thematic equity vehicles must not receive a synthetic commodity tracking score if the relationship is not directly comparable.

5. **Risk efficiency**
   - current certified vehicle Risk V1 evidence;
   - annualized volatility;
   - downside volatility;
   - maximum drawdown;
   - value at risk;
   - lookback count and methodology version retained.

## Score design

When all required evidence is present, the bounded implementation score is 0-100 with these weights:

- exposure fidelity: **30%**
- cost efficiency: **20%**
- liquidity / implementation friction: **20%**
- tracking quality: **15%**
- risk efficiency: **15%**

The five component scores must be independently visible in the presentation. UIP must never expose only an opaque total score.

### Exposure fidelity

Exposure fidelity is categorical and must reflect the registered vehicle structure rather than recent performance:

- physical-backed ETF: highest direct-fidelity class for precious metals;
- futures fund: direct commodity implementation class, with explicit futures-roll caveat;
- miners ETF / thematic equity ETF: indirect equity implementation class;
- cash proxy: excluded from commodity ranking.

The exact numeric mapping for this component must be versioned in the ranking configuration and cannot be changed without methodology-version change.

### Cost efficiency

Lower certified recurring cost is better within the compared commodity group. Missing cost fails the preferred-vehicle gate; it is not treated as zero.

### Liquidity / implementation friction

Higher average dollar volume and lower certified bid/ask spread are better. Missing liquidity or spread fails the preferred-vehicle gate.

### Tracking quality

Lower valid tracking error is better. If a vehicle type is structurally indirect and no valid commodity tracking measure exists, the method must represent that distinction explicitly rather than manufacturing a tracking value.

### Risk efficiency

Lower vehicle-specific volatility, downside volatility, drawdown magnitude, and VaR are better, using only current certified Risk V1 evidence. Vehicle risk never becomes commodity risk.

## Preferred-vehicle gate

UIP may label one vehicle `PREFERRED IMPLEMENTATION CANDIDATE` only when:

- the upstream commodity recommendation is actionable under its own authority;
- at least two registered vehicles exist for the commodity, unless the single-vehicle case is explicitly labeled `ONLY REGISTERED IMPLEMENTATION` rather than ranked;
- all required evidence families are complete and current for every compared vehicle;
- every component can be scored under this methodology without synthetic missing values;
- no tied total score remains after deterministic tie-break rules;
- the ranking audit status is PASS.

If any required evidence is missing, the commodity page may still list registered vehicles, but the result must be `PREFERRED_VEHICLE_NOT_CERTIFIED` and show the missing evidence categories.

## Tie-break policy

For an exact total-score tie, apply in order:

1. higher exposure-fidelity component;
2. lower certified bid/ask spread;
3. lower certified recurring cost;
4. lower maximum drawdown magnitude;
5. lexical ticker order only as a deterministic display fallback, never as an economic claim.

## Current evidence audit — 2026-09-14 source set

Using the current certified Metals production source set associated with run `34849676771`:

- current price coverage: present for all 10 registered commodity implementation vehicles;
- Risk V1 coverage: present for all 10 registered commodity implementation vehicles;
- Risk V1 lookback: 252 observations for all 10;
- certified expense-ratio coverage in the registry: **0/10**;
- certified average-dollar-volume field: **not currently published**;
- certified bid/ask-spread field: **not currently published**;
- certified tracking-quality field: **not currently published**.

Therefore the current authorization decision is:

`PREFERRED_VEHICLE_RANKING = FAIL_CLOSED_INSUFFICIENT_EVIDENCE`

This is expected. Risk alone is not enough to make a defensible purchase-vehicle recommendation. For Gold specifically, GLD, IAU, and SGOL have very similar Risk V1 values, so a risk-only ranking would create false precision.

## Next evidence work

Before a ranking rehearsal can be authorized, UIP must add governed vehicle evidence for:

- expense ratio / recurring cost;
- average dollar volume;
- bid/ask spread;
- tracking-quality or a versioned explicit `NOT_APPLICABLE_INDIRECT_EXPOSURE` state where appropriate.

Sources and collection policy must be separately certified. Static fund facts should come from authoritative issuer documentation when practical; market-derived liquidity evidence should come from a governed market-data source with explicit windows and as-of dates.

## Presentation contract

Once certified, a commodity detail page should present:

- commodity thesis and rich commodity evidence first;
- `Ways to invest in <commodity>` second;
- each vehicle's ticker, name, exposure type, current price, cost, liquidity, tracking, and Risk V1 evidence;
- component scores and total implementation score where authorized;
- one `PREFERRED IMPLEMENTATION CANDIDATE` only when the gate passes;
- rationale explaining why the preferred vehicle leads;
- caveats for indirect exposure such as miners/thematic equity vehicles.

## Forbidden behavior

This authority explicitly prohibits:

- copying the representative test scores currently used in vehicle-constraint tests into live ranking authority;
- using vehicle returns to manufacture commodity forecasts;
- using vehicle Risk V1 as commodity risk;
- projecting commodity expected return onto a vehicle as a vehicle-specific forecast;
- filling missing cost, liquidity, spread, or tracking evidence with zero/default values;
- ranking vehicles across different commodities;
- automatic execution, position sizing, or portfolio allocation;
- restoring the central publication cron solely because this design exists.