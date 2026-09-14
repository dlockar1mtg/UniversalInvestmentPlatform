# Metals Alpaca SIP Provider Certification V1

## Decision

Alpaca Market Data is certified as the governed provider for the UIP Metals vehicle quote-source suitability layer, using the SIP feed only.

This certification establishes provider suitability. It does not authorize production quote collection, spread publication, preferred vehicle ranking, allocation, execution, or schedule restoration.

## Exact evidence

- Workflow: `Metals Alpaca Quote Suitability V1 Rehearsal`
- Workflow run: `34904378863`
- Source head: `acfb831b325d262ed5e7662674c6be599c030cc4`
- Artifact: `10372366176`
- Artifact digest: `sha256:772f903988a7f8ea94dd2e013f59c96f8eb04ad025231832199cf9f11a7425bd`
- Rehearsal status: `METALS_ALPACA_QUOTE_SUITABILITY_REHEARSAL_PASS`
- Provider: `alpaca_market_data`
- Feed: `sip`
- Required tickers: 10
- Resolved tickers: 10
- Minimum distinct regular-market sessions per ticker: 20
- Observed session window: `2026-08-14` through `2026-09-11`

Exact governed universe:

`GLD, IAU, SGOL, SLV, SIVR, PPLT, CPER, COPX, URA, URNM`

For every ticker, the rehearsal proved:

- at least 20 distinct regular-market sessions;
- positive bid and ask values;
- `ask >= bid`;
- SIP feed identity;
- Alpaca Market Data source authority;
- complete deterministic pagination.

## Boundaries that remain closed

`provider_certified = true`

`quote_collection_authorized = false`

`preferred_vehicle_ranking_ready = false`

No IEX downgrade is authorized. No OHLCV, ATR, volatility, volume, or last-trade proxy may substitute for bid/ask evidence.

## Required next methodology gate

Before production spread evidence is collected, UIP must explicitly govern how many quote observations represent each trading session. The existing V1 liquidity formula describes a median relative spread across quote observations in the latest 20 sessions, but a full SIP quote stream can contain materially different numbers of observations by ticker and session.

A separate bounded methodology decision must define a deterministic per-session sampling or aggregation rule so highly active sessions cannot receive accidental disproportionate weight merely because they emitted more quote updates.

Until that rule is certified, production quote collection remains unauthorized.
