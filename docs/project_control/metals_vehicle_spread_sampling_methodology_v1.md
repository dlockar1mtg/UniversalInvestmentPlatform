# Metals Vehicle Spread Sampling Methodology V1

## Objective

Define a deterministic, session-balanced bid/ask spread methodology for `UIP_NATIVE_METALS_VEHICLE_LIQUIDITY_V1` before any production quote-evidence collection is authorized.

## Problem being resolved

The prior liquidity contract defined the final statistic as the median relative spread across all valid quote observations in the latest 20 trading sessions. That leaves sessions with many more quote updates with more statistical weight than quieter sessions.

The Alpaca SIP suitability rehearsal proved that quote counts vary by ticker and session. UIP therefore requires each trading session to contribute exactly one spread statistic before the 20-session aggregate is computed.

## Governed source

The quote provider is `alpaca_market_data` using the certified `sip` feed only. Silent downgrade to IEX or another feed is prohibited.

## Valid observation rules

A quote observation is valid only when all of the following are true:

- ticker is one of the exact registered Metals implementation vehicles;
- timestamp falls between 15:50:00 and 16:00:00 America/New_York on the governed trading session;
- bid is finite and greater than zero;
- ask is finite and greater than zero;
- ask is greater than or equal to bid;
- source authority and SIP feed provenance are retained.

For each valid quote:

`relative_spread_bps = ((ask - bid) / ((ask + bid) / 2)) * 10000`

## Two-stage session-balanced statistic

For each ticker and each valid trading session:

1. collect all valid SIP quote observations in the fixed 15:50-16:00 America/New_York window;
2. compute the median `relative_spread_bps` across those valid observations;
3. retain that single value as the session spread statistic with its session date, valid quote count, first/last observation timestamps, source authority, feed, and source run provenance.

For the final vehicle spread input:

1. select the latest 20 distinct trading sessions with valid session spread statistics;
2. require 20 valid sessions before the metric is complete;
3. compute the median of the 20 session median spreads;
4. retain the 20 session-level values and window dates in the audit evidence.

This gives each session one equal contribution regardless of raw quote-update frequency.

## Why median-of-medians

A session median is robust to individual quote flickers and transient outliers within the fixed near-close window. Taking the median again across 20 session medians is robust to isolated unusual trading days while preserving equal session weighting.

The fixed 15:50-16:00 ET window is deterministic, occurs during regular-market hours, is close to the end-of-day implementation context, and has already been proven available for the exact 10-ticker universe under the certified Alpaca SIP provider.

## Missing-session and holiday policy

Weekends and exchange holidays are not trading sessions and do not count toward the 20-session requirement. A candidate weekday with no valid SIP quotes is skipped and cannot be replaced with a zero spread or a peer value.

The collector may probe farther backward until it obtains 20 distinct valid trading sessions. If it cannot establish 20 valid sessions within the governed bounded search window, the ticker remains incomplete and ranking readiness fails closed.

## Prohibited alternatives

The following are not authorized by this methodology:

- median across every raw quote from all 20 sessions without equal session weighting;
- last quote only;
- first quote only;
- daily OHLCV or volatility proxy;
- IEX fallback;
- missing-session default;
- synthetic bid/ask reconstruction;
- cross-ticker substitution.

## Authorization boundary

This document authorizes the methodology only. It does **not** authorize production quote collection, ranking activation, publication writes, allocation, execution, or central cron restoration.

The next gate is a bounded read-only spread-evidence rehearsal using the certified Alpaca SIP provider and this exact methodology.
