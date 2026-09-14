# Metals Commodity → Vehicle Implementation Design V1

## Objective

Preserve the governed commodity thesis as the primary Metals investment authority while restoring an explicit implementation layer that answers a separate question: **which registered investable vehicles can express that commodity thesis?**

This design does not authorize automatic execution, position sizing, portfolio allocation, or cross-domain ranking.

## Decision separation

1. **Commodity thesis** answers what underlying commodity is attractive.
2. **Vehicle implementation** answers what registered instrument can provide exposure to that commodity.
3. Vehicle evidence must never create, replace, or override the commodity recommendation, forecast, regime, uncertainty, or tactical state.
4. Commodity evidence must never be copied into a vehicle as if it were vehicle-specific risk or return evidence.

## Canonical commodity identities

The presentation layer uses the canonical registry identities:

- `metals:commodity:gold`
- `metals:commodity:silver`
- `metals:commodity:platinum`
- `metals:commodity:copper`
- `metals:commodity:uranium`
- `metals:commodity:aluminum`
- `metals:commodity:nickel`
- `metals:commodity:zinc`
- `metals:commodity:tin`

Known certified sidecar identity variants may be bridged **only at the presentation boundary**. The source artifact is immutable and its original identity must remain retained in provenance.

## Registered investable vehicles

Current enabled registry mappings are:

| Commodity | Registered vehicles | Exposure type |
| --- | --- | --- |
| Gold | GLD, IAU, SGOL | physical-backed ETF |
| Silver | SLV, SIVR | physical-backed ETF |
| Platinum | PPLT | physical-backed ETF |
| Copper | CPER, COPX | futures fund; miners ETF |
| Uranium | URA, URNM | thematic/miners equity ETF |
| Aluminum | none | unavailable |
| Nickel | none | unavailable |
| Zinc | none | unavailable |
| Tin | none | unavailable |

`BIL` remains the governed tactical-reserve reference and is not a commodity implementation vehicle.

## Current certified vehicle evidence

The rich Metals publication currently contains vehicle-level:

- current price;
- price history;
- Risk V1 metrics including volatility, downside volatility, maximum drawdown, and value at risk.

These records are vehicle evidence only. They must not be projected onto the commodity itself.

## Presentation behavior authorized by this design

A commodity research page may show a section such as **Ways to invest in Gold** listing the exact enabled registered vehicles and their independently available vehicle evidence.

The page may label a vehicle as:

- `REGISTERED IMPLEMENTATION CANDIDATE` when it is enabled and mapped to the commodity;
- `VEHICLE EVIDENCE AVAILABLE` when current certified vehicle evidence exists;
- `VEHICLE EVIDENCE INCOMPLETE` when some expected evidence is absent.

The page must remain fail-closed for commodities with no enabled registered vehicle.

## Preferred-vehicle ranking is NOT YET AUTHORIZED

The repository contains deterministic vehicle-allocation constraint code and representative test scores, but those representative scores are not certified live investment authority.

Until a separate versioned vehicle-ranking methodology is designed, audited, rehearsed, and certified, UIP must not label GLD, IAU, SGOL, SLV, SIVR, CPER, COPX, URA, URNM, or PPLT as:

- best;
- preferred;
- top-ranked;
- recommended purchase;
- superior implementation;
- target allocation.

The next governed phase will define how vehicle-specific evidence such as tracking/exposure type, cost, liquidity, risk, and other certified measures can create a bounded implementation ranking without contaminating the commodity thesis.

## Governance boundary

This design explicitly prohibits:

- using vehicle returns to manufacture commodity forecasts;
- using vehicle Risk V1 as commodity risk;
- copying old demonstration/test scores into production authority;
- silently converting missing vehicle coverage into a HOLD/WAIT/avoid signal;
- automatic execution;
- position sizing or portfolio allocation;
- cross-domain comparison.
