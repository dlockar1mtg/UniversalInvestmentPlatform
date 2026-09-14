# Metals Vehicle Quote Source Design V1

## Objective

Define the minimum governed source contract required to collect actual quoted bid/ask evidence for the registered Metals implementation vehicles. This authority exists only to support the liquidity / implementation-friction component of `UIP_NATIVE_METALS_VEHICLE_RANKING_V1`.

No provider is selected by this design. Provider selection must be based on documented coverage and reproducible quote semantics rather than convenience or prior use elsewhere in UIP.

## Eligible universe

The exact registered implementation vehicle universe is:

- GLD
- IAU
- SGOL
- SLV
- SIVR
- PPLT
- CPER
- COPX
- URA
- URNM

The quote source must support all ten tickers. Partial coverage does not authorize preferred-vehicle ranking for any multi-vehicle commodity group unless the ranking gate separately proves complete evidence for every compared vehicle.

## Required quote semantics

Each governed quote observation must contain:

- ticker;
- observation date;
- bid;
- ask;
- UTC observation timestamp;
- source authority;
- source run id.

Both bid and ask must be positive, and ask must be greater than or equal to bid. Missing bid or ask fails the observation. Missing values may not be replaced with last trade, midpoint, high/low range, volatility, volume, or another proxy.

## Session policy

The preferred observation window is regular U.S. market hours so the spread represents normal implementability rather than overnight or closed-market artifacts.

The evidence contract requires 20 distinct trading sessions per ticker. One valid governed quote observation per session is sufficient for V1. If multiple governed observations exist for the same ticker/session, the latest `observed_at_utc` is used; `source_run_id` is the deterministic provenance tie-break only.

This same-date selection applies only to the derived spread evidence. Raw source observations remain immutable.

## Spread formula

For each valid observation:

`relative_spread_bps = ((ask - bid) / ((ask + bid) / 2)) * 10000`

For each ticker, the V1 spread evidence is:

`median_relative_bid_ask_spread_bps`

calculated across the latest 20 valid distinct trading sessions.

## Provider acceptance gate

A provider may be certified only if it can demonstrate:

1. documented U.S.-listed ETF/fund quote coverage for all ten registered tickers;
2. actual bid and ask fields, not reconstructed estimates;
3. timestamped quote observations;
4. stable ticker identity and source provenance;
5. reproducible collection suitable for a bounded read-only rehearsal;
6. terms / access conditions compatible with the intended non-execution research use;
7. no requirement to infer spread from OHLCV.

A provider name, API key, connector, or historical familiarity is not itself evidence of suitability.

## Current repository finding

As of this design, UIP has governed daily close/volume history sufficient for 30-session average dollar volume, but no existing certified quote-capable provider contract was found for these ten vehicles.

Therefore:

`METALS_VEHICLE_QUOTE_SOURCE_STATE = PROVIDER_NOT_YET_CERTIFIED`

and:

`PREFERRED_VEHICLE_RANKING = FAIL_CLOSED_INSUFFICIENT_QUOTE_EVIDENCE`

## Read-only rehearsal sequence

After a provider is selected and separately authorized:

1. collect bounded quote observations for the exact ten tickers only;
2. retain raw provider payload / normalized evidence with provenance;
3. validate bid/ask and timestamps;
4. require 20 distinct sessions per ticker;
5. derive relative spread per session;
6. compute the 20-session median per ticker;
7. emit an audit artifact;
8. perform no presentation publication, ranking activation, allocation, sizing, or execution.

## Forbidden behavior

This design explicitly prohibits:

- high-low range as bid/ask spread;
- volatility or ATR as bid/ask spread;
- volume as bid/ask spread;
- last trade as a substitute for bid or ask;
- stale or undated quote snapshots;
- secondary unverified quote values;
- missing-value defaults;
- broadening the collection universe without a methodology change;
- automatic execution;
- position sizing;
- portfolio allocation;
- restoring the central publication cron solely because a quote-source design exists.
