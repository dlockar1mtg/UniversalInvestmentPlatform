# UIP R2 Refreshed-Data Rehearsal Closeout

Status: `UIP_R2_REFRESHED_DATA_REHEARSAL_PASS`

R2 executed real refreshed-data rehearsals for MTG, Metals, and Crypto, normalized all 19 governed R1 cycle-evidence fields for each domain, used disposable UIP state for compatibility/import proof, preserved native semantics and lineage, and did not activate production UIP state.

## Domain dispositions

- MTG: fresh marketplace production evidence reconciled to 968-row certified native authority; 161/161 certified live prices and 49/49 certified live decisions applied in governed replay; no execution authority created.
- Metals: canonical production cycle PASS; 62 rows imported; 10 registry assets / 11 vehicles; all 11 daily-market vehicles current; official provider/readiness evidence PASS.
- Crypto: recovered historical foundation plus supported incremental refresh completed all 43 active modules; fresh universal export and delivery PASS; disposable UIP import reconciled 151 rows; no paid CoinGecko key required.

## Governance correction recorded at closeout

The original R2 plan specified Crypto `full_refresh=true`. Recovery testing proved that an empty-state full refresh was not the supported durable path for the existing Crypto architecture. R2 therefore used the previously successful populated-database incremental path with `full_refresh=false`, preserving the historical foundation and refreshing current market, exchange, ecosystem, and FRED data. This is recorded as a governed execution correction, not a change to Crypto-native model semantics.

The exact Crypto producer completion timestamp was not retained by the disposable producer summary. The normalized record therefore uses the committed R2 evidence timestamp as a conservative upper bound and records that limitation as a warning. No freshness or semantic authority is synthesized from that timestamp.

## Prohibited effects

- production UIP activation: false
- native semantic reinterpretation: false
- cross-asset ranking: false
- allocation policy: false
- automatic purchase/trade execution: false

## Permanent evidence

- `docs/project_control/generated/r2_refreshed_data_rehearsal/mtg_r2_rehearsal_evidence.json`
- `docs/project_control/generated/r2_refreshed_data_rehearsal/metals_r2_rehearsal_evidence.json`
- `docs/project_control/generated/r2_refreshed_data_rehearsal/crypto_r2_rehearsal_evidence.json`
- `docs/project_control/generated/r2_refreshed_data_rehearsal/r2_refresh_rehearsal_certification.json`

Next gate: `UIP_R3_OUTPUT_RATIONALITY_AND_DOMAIN_HEALTH_REVIEW`
