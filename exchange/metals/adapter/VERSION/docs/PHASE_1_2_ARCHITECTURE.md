# Phase 1.2 — Metals Universal Export Adapter

## Integration path

```text
Metals v8 native CSV exports
                   ┐
Metals DuckDB read-only views ──> deterministic adapter ──> Universal v1 package
                   ┘                                      ├─ canonical CSVs
                                                          ├─ manifest/checksums
                                                          ├─ validation summary
                                                          └─ supporting native evidence
```

The adapter does not import Metals analytics engines, recompute scores, or write to the Metals database. DuckDB is opened with `read_only=True` and only the certified latest views are queried.

## Canonical outputs

- `asset_master.csv`
- `forecasts.csv`
- `recommendations.csv`
- `risk_metrics.csv`
- `portfolio_positions.csv`
- `platform_status.csv`
- `export_manifest.csv`

The adapter loads the Phase 0 contract definitions directly from `schemas/v1/csv`. Missing columns are added only to align the frame to the existing contract; required nulls cause validation failure.

## Read-only views

- `latest_vehicle_recommendations`
- `latest_recommendation_history`
- `latest_portfolio_positions`
- `latest_portfolio_risk_metrics`
- `latest_risk_contributions`

## Version boundary

- Native interface: `metals-native-v8`
- Universal contract: `v1`
- Adapter package: Phase 1.2
