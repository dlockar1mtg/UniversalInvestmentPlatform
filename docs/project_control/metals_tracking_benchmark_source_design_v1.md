# Metals Tracking Benchmark Source Design V1

## Objective

Identify the exact benchmark authority required for every registered Metals implementation vehicle whose tracking state must be `AVAILABLE`, without substituting a convenient proxy for the true benchmark.

## Exact benchmark mapping

- GLD, IAU, SGOL -> LBMA Gold Price PM.
- SLV, SIVR -> LBMA Silver Price.
- PPLT -> LBMA Platinum Price PM.
- CPER -> SummerHaven Copper Index Total Return.

These identities are based on current issuer/fund documentation and the CPER index definition.

## Historical-data access boundary

Benchmark identity and benchmark-history access are separate certification questions.

LBMA states that historical Gold, Silver, Platinum and Palladium benchmark tables require the relevant authorized/licensed access through the LBMA/ICE Benchmark Administration channel. UIP therefore must not scrape, redistribute, or silently replace those histories with generic spot, futures, ETF, or secondary-price proxies.

CPER requires the exact SummerHaven Copper Index Total Return history. A generic copper spot series, front-month COMEX contract, or another copper ETF is not equivalent.

## Tracking calculation requirements

A future tracking-quality rehearsal must use at least 252 aligned return observations between each vehicle and its exact benchmark, with date alignment and currency consistency explicit. Missing benchmark dates remain missing. No peer or proxy substitution is permitted.

The vehicle side must use governed NAV or equivalent governed vehicle total-return history appropriate to measuring tracking quality, not an unrelated commodity forecast or commodity-level recommendation series.

## Current authorization state

- benchmark identities: **DEFINED**;
- benchmark historical-data access: **NOT YET CERTIFIED**;
- benchmark history collection: **NOT AUTHORIZED**;
- tracking-quality calculation: **NOT AUTHORIZED**;
- preferred vehicle ranking: **FAIL-CLOSED**.

## Next gate

Determine an authorized 252-session historical data path for LBMA Gold Price PM, LBMA Silver Price, LBMA Platinum Price PM, and SummerHaven Copper Index Total Return. Only after that path is proven should UIP authorize a bounded read-only tracking-quality rehearsal.

## Governance boundary

This design does not publish tracking values, create preferred implementation labels, modify source schedules, allocate capital, execute trades, or restore the central publication cron.
