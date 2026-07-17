# Phase 1.2 — Metals Universal Export Adapter Certification

## Certification Status

PASS

## Platform

Metals Investment Intelligence Platform

## Universal Platform

Universal Investment Intelligence Platform

## Integration Type

Non-destructive file-based export adapter

## Certified Adapter Release

Phase 1.2.2

## Integration Boundary

The Universal Investment Platform does not import Metals source code,
call internal Metals modules, or modify the Metals DuckDB database.

The integration uses:

1. Metals native v8 CSV exports
2. Narrowly scoped read-only DuckDB access where required
3. Universal CSV contract definitions
4. Timestamped Universal integration packages
5. Strict contract validation

## Universal Outputs

The adapter publishes:

- asset_master.csv
- forecasts.csv
- recommendations.csv
- risk_metrics.csv
- portfolio_positions.csv
- platform_status.csv
- export_manifest.csv

## Contract Location

schemas/v1/csv

## Contract Filename Convention

- asset_master_columns.csv
- export_manifest_columns.csv
- forecasts_columns.csv
- platform_status_columns.csv
- portfolio_positions_columns.csv
- recommendations_columns.csv
- risk_metrics_columns.csv

## Canonical Field Alignment

The adapter populates the Universal canonical fields, including:

- run_id
- universal_asset_id
- platform_asset_id
- investable
- last_updated_at_utc
- forecast_origin_date
- forecast_horizon_months
- forecast_method
- normalized_score
- confidence_score
- risk_score
- risk_level
- position_value
- current_weight
- run_started_at_utc
- data_as_of_date
- records_published
- warning_count
- error_count

## Validation Result

METALS UNIVERSAL EXPORT: PASS

## Output Location

data/integration/metals

The latest successful package is also copied to:

data/integration/metals/latest

## Read/Write Restrictions

The adapter:

- Reads Metals source data
- Opens the Metals database in read-only mode
- Writes only to the Universal repository
- Does not change Metals scoring logic
- Does not change Metals forecasting logic
- Does not change Metals portfolio logic
- Does not modify the Metals database

## Certification Decision

The Metals Universal Export Adapter is certified as the first production
integration adapter for the Universal Investment Intelligence Platform.

It is approved as the reference implementation for future platform adapters.

## Next Phase

Phase 1.3 — Universal Import Engine