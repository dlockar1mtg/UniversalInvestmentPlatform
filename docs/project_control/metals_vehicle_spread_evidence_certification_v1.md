# Metals Vehicle Spread Evidence Certification V1

## Decision

The bounded Alpaca SIP spread-evidence rehearsal is certified as the current governed quoted-spread evidence for the exact ten registered Metals implementation vehicles.

## Exact evidence

- workflow run: `34968921414`
- source head: `c06ef0461e00562ab63261439b9025463d487140`
- artifact: `10395879669`
- artifact digest: `sha256:15ed4d1bdd06cee6e9e50eadced3f332dc21be6144b6a58f2ce932366820db6d`
- provider: `alpaca_market_data`
- feed: `sip`
- methodology: `UIP_NATIVE_METALS_VEHICLE_LIQUIDITY_V1` version `1.1.0`
- session window: 15:50:00–16:00:00 America/New_York
- per-session statistic: median relative bid/ask spread
- cross-session statistic: median of the latest 20 session medians
- evidence window: 2026-08-17 through 2026-09-14
- exact ticker coverage: 10/10

## Certified spread values

| Ticker | Median spread (bps) |
| --- | ---: |
| GLD | 0.4896385164486847 |
| IAU | 1.1973211358820681 |
| SGOL | 2.3646307930811252 |
| SLV | 1.6668056134387286 |
| SIVR | 1.607349520749425 |
| PPLT | 6.06428194019866 |
| CPER | 2.504696305572451 |
| COPX | 2.170928037276172 |
| URA | 2.19491228149447 |
| URNM | 13.918695866057366 |

## Boundary

This certification establishes the quoted-spread evidence values only. It does not authorize persistent production quote collection, preferred-vehicle ranking, publication writes, portfolio allocation, position sizing, trade execution, source-schedule modification, or restoration of the central publication cron.

Preferred implementation labels remain fail-closed until all other required evidence families are complete and separately audited.
