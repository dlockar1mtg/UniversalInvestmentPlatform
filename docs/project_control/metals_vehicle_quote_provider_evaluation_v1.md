# Metals Vehicle Quote Provider Evaluation V1

## Objective

Evaluate candidate market-data providers against `UIP_NATIVE_METALS_VEHICLE_QUOTE_SOURCE_V1` before any bid/ask collection is authorized.

## Governed requirement

The quote source must support the exact registered implementation universe:

`GLD, IAU, SGOL, SLV, SIVR, PPLT, CPER, COPX, URA, URNM`

For each ticker it must provide actual bid and ask values, a UTC quote timestamp, explicit source/feed provenance, and enough historical quote access to cover at least 20 distinct regular-market trading sessions.

## Candidate evaluation

### Alpaca Market Data — PROVISIONAL_CANDIDATE

Official Alpaca documentation states:

- equities coverage includes US Stocks & ETFs;
- the historical stock quotes endpoint returns quote data over a caller-specified date range;
- quote payloads include timestamped best bid and ask fields;
- SIP and IEX are explicit feed choices;
- historical SIP queries whose end is at least 15 minutes old can be queried without a paid real-time subscription;
- historical data is available back to 2016.

These capabilities satisfy the structural requirements of the UIP quote-source contract in principle.

### Remaining proof required

Alpaca is not yet certified because UIP has not performed a credentialed live rehearsal proving:

1. all 10 UIP tickers resolve under the selected feed;
2. each ticker returns valid positive bid and ask observations;
3. each ticker can provide at least 20 distinct regular-market sessions in the requested historical window;
4. pagination can be completed deterministically without silently truncating symbols;
5. source/feed identity is retained in the evidence output;
6. no ticker is substituted, aliased, or defaulted when missing.

## Feed policy

The intended first rehearsal should request `feed=sip` with an end time safely older than 15 minutes so real-time entitlements are unnecessary. If SIP access is rejected by the connected account, the rehearsal must fail closed rather than silently downgrade to IEX.

A later methodology change would be required to authorize IEX as the production spread authority, because single-exchange quotes are not equivalent to consolidated SIP NBBO evidence.

## Authorization decision

`ALPACA_PROVIDER_STATE = PROVISIONAL_CANDIDATE_PENDING_LIVE_10_TICKER_REHEARSAL`

No quote collection, ranking activation, publication write, schedule restoration, allocation, or execution is authorized by this document.

## Next phase

Create a manual-only, read-only Alpaca suitability rehearsal that accepts credentials only through secrets, queries historical SIP quotes for the exact ten tickers, validates 20-session coverage and bid/ask semantics, emits an evidence artifact, and performs no persistence or ranking writes.
