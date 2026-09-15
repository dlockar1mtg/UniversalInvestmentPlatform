# Metals Vehicle Ranking Authority Design V1

## Objective

Create a bounded, vehicle-specific implementation authority that can answer:

> The upstream commodity thesis is actionable. Of the registered vehicles for that commodity, which exact instrument is the strongest implementation candidate, and why?

The commodity thesis remains the upstream investment authority. Vehicle ranking is downstream implementation research only and may not create, replace, strengthen, weaken, or override the commodity recommendation.

## Authority identity

- authority id: `UIP_NATIVE_METALS_VEHICLE_RANKING_V1`
- schema version: `1.0.0`
- methodology version: `1.2.0`
- scope: `REGISTERED_METALS_IMPLEMENTATION_VEHICLES_ONLY`
- ranking grain: one row per registered enabled vehicle, grouped within one underlying commodity
- cross-domain ranking: prohibited
- automatic execution: prohibited
- position sizing / portfolio allocation: prohibited

## Eligible universe

Only enabled commodity implementation vehicles in `config/metals/vehicles.json` may enter the ranking. `BIL` is excluded as a reserve vehicle.

Current groups are Gold (GLD, IAU, SGOL), Silver (SLV, SIVR), Platinum (PPLT), Copper (CPER, COPX), and Uranium (URA, URNM). Aluminum, Nickel, Zinc, and Tin remain `IMPLEMENTATION_UNAVAILABLE` because no enabled implementation vehicle is registered.

## Required evidence

Every compared vehicle must have current certified evidence for:

1. registered exposure type;
2. recurring cost / expense ratio;
3. 30-session average dollar volume;
4. 20-session quoted bid/ask spread;
5. vehicle Risk V1.

Missing required evidence fails closed. No missing value may default to zero, a peer value, or another synthetic value.

Tracking quality is not a required scoring input. Exact benchmark identities remain governed and tracking may be displayed later only if exact authorized benchmark histories become available. Unauthorized tracking proxies remain forbidden.

## Four-factor score

The score is 0-100 and uses:

- exposure fidelity: **35%**
- cost efficiency: **25%**
- liquidity / implementation friction: **25%**
- risk efficiency: **15%**

All component scores must be visible independently from the total.

### Exposure fidelity

The registered structural score is used directly:

- physical-backed ETF: 100
- futures fund: 90
- miners ETF: 60
- thematic equity ETF: 55

No vehicle type may be relabeled as direct commodity exposure.

### Cost efficiency

Within a commodity group, lower certified recurring cost is better.

`cost_score = 100 * group_min_expense_ratio / vehicle_expense_ratio`

All required cost inputs must be positive. Zero, negative, or missing values fail closed.

### Liquidity / implementation friction

Liquidity is an equal-weight blend of ADV and quoted spread.

`adv_score = 100 * vehicle_ADV / group_max_ADV`

`spread_score = 100 * group_min_spread / vehicle_spread`

`liquidity_score = 0.50 * adv_score + 0.50 * spread_score`

ADV and spread must be strictly positive and come from their governed windows and authorities. Volume is never used as a quoted-spread proxy.

### Risk efficiency

Risk efficiency uses four equally weighted current Vehicle Risk V1 submetrics:

- annualized volatility;
- downside volatility;
- absolute maximum drawdown magnitude;
- value at risk.

For each positive risk magnitude:

`risk_submetric_score = 100 * group_min_positive_value / vehicle_positive_value`

`risk_score` is the arithmetic mean of the four submetric scores.

Vehicle Risk V1 as commodity risk is forbidden. Risk values remain vehicle-specific implementation evidence only.

### Total score

`total_score = 0.35*exposure + 0.25*cost + 0.25*liquidity + 0.15*risk`

Full precision is retained for ordering. Rounding is display-only.

The ratio formulas intentionally avoid forcing the weakest vehicle in a two-vehicle group to zero merely because another vehicle is better. Each score remains anchored to an observed best value within the exact same commodity group.

## Single-vehicle groups

A commodity with only one registered implementation vehicle is not ranked against itself. It receives the governed label `ONLY_REGISTERED_IMPLEMENTATION` only when the upstream commodity and evidence gates permit it. PPLT therefore remains a single-vehicle implementation state rather than a fabricated ranking win.

## Preferred-vehicle gate

`PREFERRED_IMPLEMENTATION_CANDIDATE` is authorized only when:

- the upstream commodity recommendation is actionable under its own authority;
- at least two registered vehicles exist in the commodity group;
- all required evidence is complete/current for every compared vehicle;
- every score is calculable without defaults or proxies;
- deterministic tie-break rules resolve any exact total tie;
- the ranking audit is PASS.

Before separate certification, rehearsal output may identify ordering/candidate results for audit but must set preferred-label authorization to false and must not write production publication state.

## Tie-break policy

For an exact full-precision total-score tie, apply in order:

1. higher exposure-fidelity score;
2. lower certified bid/ask spread;
3. lower certified recurring cost;
4. lower maximum drawdown magnitude;
5. lexical ticker order only as deterministic display fallback.

## Certified input state entering the rehearsal

The current governed source set has:

- registered exposure type: complete for all 10 implementation vehicles;
- recurring cost: complete for all 10;
- 30-session ADV: complete for all 10;
- 20-session Alpaca SIP quoted spread: complete for all 10;
- Vehicle Risk V1: complete for all 10.

Tracking benchmark history is optional and non-scoring under this methodology.

## Forbidden behavior

This authority explicitly prohibits:

- representative test scores as live ranking authority;
- cross-commodity vehicle ranking;
- vehicle returns as commodity forecasts;
- Vehicle Risk V1 as commodity risk;
- commodity expected return as a vehicle-specific forecast;
- missing evidence defaults;
- unauthorized tracking proxies;
- automatic execution;
- position sizing;
- portfolio allocation;
- restoring the central publication cron solely because ranking research succeeds.

## Next gate

Run a bounded read-only four-factor ranking rehearsal against the certified input authorities. The rehearsal must emit all raw inputs, component/subcomponent calculations, full-precision ordering, deterministic tie-break evidence, provenance, and fail-closed authorization flags. No preferred label is production-authorized until the rehearsal artifact is separately audited and certified.
