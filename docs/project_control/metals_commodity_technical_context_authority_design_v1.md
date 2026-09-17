# Metals Commodity Technical Context V1 — Authority Design

## Purpose

Define the first governed commodity-level technical-context authority for the Metals research surface without inventing data, projecting vehicle behavior onto commodities, or relabeling monthly evidence as daily technical analysis.

## Read-only source audit

The production artifact from Metals Production Cycle run `34999326079` was inspected before this design was created.

Observed source boundaries:

- `operations/metals/native_rich_history/metals_price_history.csv` is vehicle-only history. It contains BIL, COPX, CPER, GLD, IAU, PPLT, SGOL, SIVR, SLV, URA, and URNM. It is not commodity benchmark history.
- `operations/metals/benchmark_input.csv` contains one current official benchmark observation per governed commodity, not history.
- `operations/metals/daily_market_input.csv` contains current and previous benchmark closes only for the investable vehicle groups.
- `WorldBankCommodityProvider` already downloads the full World Bank Pink Sheet monthly workbook for Aluminum, Copper, Gold, Nickel, Platinum, Silver, Tin, and Zinc, but its current `latest()` path retains only the latest usable row for each requested commodity.
- `EIAUraniumProvider` is annual. That source cadence cannot support honest 1M/3M/6M commodity technical context or 50-day/200-day moving averages.

## Authorized V1 source

V1 may preserve the historical monthly rows already present in the World Bank Pink Sheet workbook for these eight commodity benchmarks:

- Aluminum
- Copper
- Gold
- Nickel
- Platinum
- Silver
- Tin
- Zinc

This is a direct commodity benchmark source. No vehicle proxy is required or authorized.

Uranium is explicitly unsupported in V1 because the current certified EIA authority is annual.

## Authorized calculations

For each supported commodity, using only exact monthly observations from the same World Bank series:

- **1M return** = latest value / value exactly one calendar month earlier - 1.
- **3M return** = latest value / value exactly three calendar months earlier - 1.
- **6M return** = latest value / value exactly six calendar months earlier - 1.
- **Current drawdown** = latest value / highest available official monthly observation through the latest observation - 1.

No interpolation, forward fill, nearest-date substitution, or cross-provider imputation is allowed. If an exact required prior month is missing, that metric is unavailable.

## Moving-average boundary

V1 does **not** authorize a 50-day or 200-day moving average from World Bank monthly data.

The existing hosted research page currently contains `vs MA50` and `vs MA200` placeholders. Those fields must remain nonnumeric or be relabeled/hidden until a separately governed daily commodity benchmark source exists.

It is specifically forbidden to calculate a 50-observation or 200-observation average from monthly World Bank data and present it as MA50/MA200, because that would change the implied cadence from days to months.

## Uranium boundary

URA or URNM price history may not silently stand in for the uranium commodity benchmark. A vehicle proxy could be considered only under a separate explicit authority that identifies it as proxy evidence. This V1 authority does not authorize that mapping.

## Presentation semantics

Technical context is descriptive timing evidence only. It may not:

- override the certified long-term commodity recommendation;
- create a new recommendation;
- modify tactical-state authority;
- create cross-asset ranking;
- create portfolio allocation or position sizing;
- authorize execution; or
- restore the central publication cron.

## Implementation sequence after design certification

1. Extend the World Bank provider/collector with a bounded history-preservation path while leaving the current latest-observation contract intact.
2. Build a read-only sidecar that emits one commodity technical-context row for each supported commodity and records unavailable reasons explicitly.
3. Rehearse and certify the sidecar without publication writes.
4. Wire the new family into the Metals production artifact only after exact evidence review.
5. Wire it into the rich publication candidate and rehearse again before any production activation.
6. Update the dashboard to consume the governed fields and replace generic dashes with either real values or explicit unsupported-source-cadence messaging.

No production publication or schedule change is authorized by this design document.
