# UIP Database Schema Catalog

## Generation evidence

- Database: `C:\Users\DevonLockard\AppData\Local\Temp\uip-d1-schema-control-f081e70765d848d2865501f0dda5385c\d1_schema_control.duckdb`
- Database SHA-256: `414d80d097a98f6e620f4a7cb011c46bde6392b85cc5f2608814d8698b1b99f4`
- Database size: `1585152` bytes
- Inspected at: `2026-08-14T18:54:08.822414+00:00`
- Inspection mode: `READ_ONLY`
- Database objects: `31`
- Ordered SQL files: `6`

This catalog is generated from read-only DuckDB introspection. It records observed implementation evidence; it does not by itself authorize a schema change.

## Ordered SQL authority inventory

| Order | File | SHA-256 | Purpose |
|---:|---|---|---|
| 1 | `foundation/import_engine/sql/001_initialize_universal_database.sql` | `702d1e48edb79d6c0595586b12332619d71d4cb87201f3c3a12d40c1409225da` | create or extend canonical tables |
| 2 | `foundation/import_engine/sql/002_audit_registry_integration.sql` | `9563d6ca0a0b120d4de15a6fd78d47fd4d3f4c5afa530886a8289c8011b1cc5d` | create or extend canonical tables; import audit and platform registry |
| 3 | `foundation/import_engine/sql/003_health_status_latest_attempt.sql` | `130f47a6e95bbc8e2479466e2ea6f42d05e726f7fc22f94fd4a2f96fdbef7624` | import audit and platform registry |
| 4 | `foundation/import_engine/sql/004_historical_performance.sql` | `ae86fefd6113eb98d2a87f293797e34d4216001d7d55ba21276185d202c40041` | create or extend canonical tables |
| 5 | `foundation/import_engine/sql/005_mtg_native_authority.sql` | `33f44c15b9d0edcbf813162477077a18acf07833cd7f13e1fc4cbec60a0a37d4` | create or extend canonical tables |
| 6 | `foundation/import_engine/sql/006_common_domain_registry_lineage.sql` | `b155e0ab7e80dd5c23559a5cd2ade63b0ed967dad8e56b6fa41c3958a721b236` | create or extend canonical tables; import audit and platform registry |

## Database objects

### `main.asset_master_current`

- Type: `VIEW`
- Observed rows: `0`
- Description: Current canonical asset view derived from asset_master_history.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_asset_id` | `VARCHAR` | `YES` | `` |
| 4 | `platform_id` | `VARCHAR` | `YES` | `` |
| 5 | `asset_name` | `VARCHAR` | `YES` | `` |
| 6 | `asset_symbol` | `VARCHAR` | `YES` | `` |
| 7 | `asset_class` | `VARCHAR` | `YES` | `` |
| 8 | `asset_subclass` | `VARCHAR` | `YES` | `` |
| 9 | `currency` | `VARCHAR` | `YES` | `` |
| 10 | `investable` | `BOOLEAN` | `YES` | `` |
| 11 | `active` | `BOOLEAN` | `YES` | `` |
| 12 | `source_system` | `VARCHAR` | `YES` | `` |
| 13 | `source_record_id` | `VARCHAR` | `YES` | `` |
| 14 | `first_observed_date` | `DATE` | `YES` | `` |
| 15 | `last_observed_date` | `DATE` | `YES` | `` |
| 16 | `last_updated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 17 | `notes` | `VARCHAR` | `YES` | `` |
| 18 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 19 | `_import_id` | `VARCHAR` | `YES` | `` |
| 20 | `_package_id` | `VARCHAR` | `YES` | `` |
| 21 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 22 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 23 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 24 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 25 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW asset_master_current AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY universal_asset_id ORDER BY _imported_at_utc DESC, last_updated_at_utc DESC) AS _row_rank FROM asset_master_history) WHERE (_row_rank = 1);
```

</details>

### `main.asset_master_history`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Append-only canonical history of assets published by source domains. Each row represents an observed asset record for a platform run.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_asset_id` | `VARCHAR` | `YES` | `` |
| 4 | `platform_id` | `VARCHAR` | `YES` | `` |
| 5 | `asset_name` | `VARCHAR` | `YES` | `` |
| 6 | `asset_symbol` | `VARCHAR` | `YES` | `` |
| 7 | `asset_class` | `VARCHAR` | `YES` | `` |
| 8 | `asset_subclass` | `VARCHAR` | `YES` | `` |
| 9 | `currency` | `VARCHAR` | `YES` | `` |
| 10 | `investable` | `BOOLEAN` | `YES` | `` |
| 11 | `active` | `BOOLEAN` | `YES` | `` |
| 12 | `source_system` | `VARCHAR` | `YES` | `` |
| 13 | `source_record_id` | `VARCHAR` | `YES` | `` |
| 14 | `first_observed_date` | `DATE` | `YES` | `` |
| 15 | `last_observed_date` | `DATE` | `YES` | `` |
| 16 | `last_updated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 17 | `notes` | `VARCHAR` | `YES` | `` |
| 18 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 19 | `_import_id` | `VARCHAR` | `NO` | `` |
| 20 | `_package_id` | `VARCHAR` | `NO` | `` |
| 21 | `_source_platform` | `VARCHAR` | `NO` | `` |
| 22 | `_source_filename` | `VARCHAR` | `NO` | `` |
| 23 | `_source_row_number` | `BIGINT` | `NO` | `` |
| 24 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 25 | `_imported_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.forecasts_current`

- Type: `VIEW`
- Observed rows: `0`
- Description: Current forecast view derived from forecasts_history.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `forecast_origin_date` | `DATE` | `YES` | `` |
| 5 | `forecast_horizon_months` | `BIGINT` | `YES` | `` |
| 6 | `forecast_method` | `VARCHAR` | `YES` | `` |
| 7 | `point_forecast` | `DOUBLE` | `YES` | `` |
| 8 | `lower_bound` | `DOUBLE` | `YES` | `` |
| 9 | `upper_bound` | `DOUBLE` | `YES` | `` |
| 10 | `expected_return` | `DOUBLE` | `YES` | `` |
| 11 | `probability_positive` | `DOUBLE` | `YES` | `` |
| 12 | `confidence_score` | `DOUBLE` | `YES` | `` |
| 13 | `scenario` | `VARCHAR` | `YES` | `` |
| 14 | `source_system` | `VARCHAR` | `YES` | `` |
| 15 | `model_version` | `VARCHAR` | `YES` | `` |
| 16 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 17 | `notes` | `VARCHAR` | `YES` | `` |
| 18 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 19 | `_import_id` | `VARCHAR` | `YES` | `` |
| 20 | `_package_id` | `VARCHAR` | `YES` | `` |
| 21 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 22 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 23 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 24 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 25 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW forecasts_current AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY universal_asset_id, forecast_horizon_months, forecast_method ORDER BY _imported_at_utc DESC, generated_at_utc DESC) AS _row_rank FROM forecasts_history) WHERE (_row_rank = 1);
```

</details>

### `main.forecasts_history`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Append-only history of source and UIP forecast observations.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `forecast_origin_date` | `DATE` | `YES` | `` |
| 5 | `forecast_horizon_months` | `BIGINT` | `YES` | `` |
| 6 | `forecast_method` | `VARCHAR` | `YES` | `` |
| 7 | `point_forecast` | `DOUBLE` | `YES` | `` |
| 8 | `lower_bound` | `DOUBLE` | `YES` | `` |
| 9 | `upper_bound` | `DOUBLE` | `YES` | `` |
| 10 | `expected_return` | `DOUBLE` | `YES` | `` |
| 11 | `probability_positive` | `DOUBLE` | `YES` | `` |
| 12 | `confidence_score` | `DOUBLE` | `YES` | `` |
| 13 | `scenario` | `VARCHAR` | `YES` | `` |
| 14 | `source_system` | `VARCHAR` | `YES` | `` |
| 15 | `model_version` | `VARCHAR` | `YES` | `` |
| 16 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 17 | `notes` | `VARCHAR` | `YES` | `` |
| 18 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 19 | `_import_id` | `VARCHAR` | `NO` | `` |
| 20 | `_package_id` | `VARCHAR` | `NO` | `` |
| 21 | `_source_platform` | `VARCHAR` | `NO` | `` |
| 22 | `_source_filename` | `VARCHAR` | `NO` | `` |
| 23 | `_source_row_number` | `BIGINT` | `NO` | `` |
| 24 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 25 | `_imported_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.historical_performance_current`

- Type: `VIEW`
- Observed rows: `0`
- Description: Current historical-performance record for each platform and universal asset, selected deterministically from history.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `contract_version` | `VARCHAR` | `YES` | `` |
| 2 | `platform_id` | `VARCHAR` | `YES` | `` |
| 3 | `run_id` | `VARCHAR` | `YES` | `` |
| 4 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 5 | `performance_status` | `VARCHAR` | `YES` | `` |
| 6 | `performance_eligible` | `BOOLEAN` | `YES` | `` |
| 7 | `historical_start_date` | `DATE` | `YES` | `` |
| 8 | `historical_end_date` | `DATE` | `YES` | `` |
| 9 | `historical_start_value` | `DOUBLE` | `YES` | `` |
| 10 | `historical_end_value` | `DOUBLE` | `YES` | `` |
| 11 | `elapsed_days` | `BIGINT` | `YES` | `` |
| 12 | `observation_count` | `BIGINT` | `YES` | `` |
| 13 | `distinct_date_count` | `BIGINT` | `YES` | `` |
| 14 | `source_count` | `BIGINT` | `YES` | `` |
| 15 | `historical_sources` | `VARCHAR` | `YES` | `` |
| 16 | `total_return_pct` | `DOUBLE` | `YES` | `` |
| 17 | `cagr_pct` | `DOUBLE` | `YES` | `` |
| 18 | `annualized_return_pct` | `DOUBLE` | `YES` | `` |
| 19 | `minimum_value` | `DOUBLE` | `YES` | `` |
| 20 | `maximum_value` | `DOUBLE` | `YES` | `` |
| 21 | `data_quality` | `VARCHAR` | `YES` | `` |
| 22 | `suppression_reason` | `VARCHAR` | `YES` | `` |
| 23 | `currency` | `VARCHAR` | `YES` | `` |
| 24 | `source_system` | `VARCHAR` | `YES` | `` |
| 25 | `model_version` | `VARCHAR` | `YES` | `` |
| 26 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 27 | `notes` | `VARCHAR` | `YES` | `` |
| 28 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 29 | `_import_id` | `VARCHAR` | `YES` | `` |
| 30 | `_package_id` | `VARCHAR` | `YES` | `` |
| 31 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 32 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 33 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 34 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 35 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW historical_performance_current AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY platform_id, universal_asset_id ORDER BY _imported_at_utc DESC, historical_end_date DESC NULLS LAST, generated_at_utc DESC) AS _row_rank FROM historical_performance_history) WHERE (_row_rank = 1);
```

</details>

### `main.historical_performance_history`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Append-only history of source-published historical performance, including eligibility, suppression, period, return, quality, and lineage evidence.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `contract_version` | `VARCHAR` | `NO` | `` |
| 2 | `platform_id` | `VARCHAR` | `NO` | `` |
| 3 | `run_id` | `VARCHAR` | `NO` | `` |
| 4 | `universal_asset_id` | `VARCHAR` | `NO` | `` |
| 5 | `performance_status` | `VARCHAR` | `NO` | `` |
| 6 | `performance_eligible` | `BOOLEAN` | `NO` | `` |
| 7 | `historical_start_date` | `DATE` | `YES` | `` |
| 8 | `historical_end_date` | `DATE` | `YES` | `` |
| 9 | `historical_start_value` | `DOUBLE` | `YES` | `` |
| 10 | `historical_end_value` | `DOUBLE` | `YES` | `` |
| 11 | `elapsed_days` | `BIGINT` | `YES` | `` |
| 12 | `observation_count` | `BIGINT` | `YES` | `` |
| 13 | `distinct_date_count` | `BIGINT` | `YES` | `` |
| 14 | `source_count` | `BIGINT` | `YES` | `` |
| 15 | `historical_sources` | `VARCHAR` | `YES` | `` |
| 16 | `total_return_pct` | `DOUBLE` | `YES` | `` |
| 17 | `cagr_pct` | `DOUBLE` | `YES` | `` |
| 18 | `annualized_return_pct` | `DOUBLE` | `YES` | `` |
| 19 | `minimum_value` | `DOUBLE` | `YES` | `` |
| 20 | `maximum_value` | `DOUBLE` | `YES` | `` |
| 21 | `data_quality` | `VARCHAR` | `NO` | `` |
| 22 | `suppression_reason` | `VARCHAR` | `YES` | `` |
| 23 | `currency` | `VARCHAR` | `NO` | `` |
| 24 | `source_system` | `VARCHAR` | `NO` | `` |
| 25 | `model_version` | `VARCHAR` | `YES` | `` |
| 26 | `generated_at_utc` | `TIMESTAMP` | `NO` | `` |
| 27 | `notes` | `VARCHAR` | `YES` | `` |
| 28 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 29 | `_import_id` | `VARCHAR` | `NO` | `` |
| 30 | `_package_id` | `VARCHAR` | `NO` | `` |
| 31 | `_source_platform` | `VARCHAR` | `NO` | `` |
| 32 | `_source_filename` | `VARCHAR` | `NO` | `` |
| 33 | `_source_row_number` | `BIGINT` | `NO` | `` |
| 34 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 35 | `_imported_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.macro_signals_current`

- Type: `VIEW`
- Observed rows: `0`
- Description: Current macro-signal view.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `signal_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `signal_name` | `VARCHAR` | `YES` | `` |
| 5 | `signal_category` | `VARCHAR` | `YES` | `` |
| 6 | `signal_value` | `DOUBLE` | `YES` | `` |
| 7 | `normalized_score` | `DOUBLE` | `YES` | `` |
| 8 | `signal_direction` | `VARCHAR` | `YES` | `` |
| 9 | `signal_status` | `VARCHAR` | `YES` | `` |
| 10 | `confidence_score` | `DOUBLE` | `YES` | `` |
| 11 | `observation_date` | `DATE` | `YES` | `` |
| 12 | `source_system` | `VARCHAR` | `YES` | `` |
| 13 | `model_version` | `VARCHAR` | `YES` | `` |
| 14 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 15 | `notes` | `VARCHAR` | `YES` | `` |
| 16 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 17 | `_import_id` | `VARCHAR` | `YES` | `` |
| 18 | `_package_id` | `VARCHAR` | `YES` | `` |
| 19 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 20 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 21 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 22 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 23 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW macro_signals_current AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY signal_id ORDER BY _imported_at_utc DESC, generated_at_utc DESC) AS _row_rank FROM macro_signals_history) WHERE (_row_rank = 1);
```

</details>

### `main.macro_signals_history`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Append-only history of canonical macroeconomic or market signals.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `signal_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `signal_name` | `VARCHAR` | `YES` | `` |
| 5 | `signal_category` | `VARCHAR` | `YES` | `` |
| 6 | `signal_value` | `DOUBLE` | `YES` | `` |
| 7 | `normalized_score` | `DOUBLE` | `YES` | `` |
| 8 | `signal_direction` | `VARCHAR` | `YES` | `` |
| 9 | `signal_status` | `VARCHAR` | `YES` | `` |
| 10 | `confidence_score` | `DOUBLE` | `YES` | `` |
| 11 | `observation_date` | `DATE` | `YES` | `` |
| 12 | `source_system` | `VARCHAR` | `YES` | `` |
| 13 | `model_version` | `VARCHAR` | `YES` | `` |
| 14 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 15 | `notes` | `VARCHAR` | `YES` | `` |
| 16 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 17 | `_import_id` | `VARCHAR` | `NO` | `` |
| 18 | `_package_id` | `VARCHAR` | `NO` | `` |
| 19 | `_source_platform` | `VARCHAR` | `NO` | `` |
| 20 | `_source_filename` | `VARCHAR` | `NO` | `` |
| 21 | `_source_row_number` | `BIGINT` | `NO` | `` |
| 22 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 23 | `_imported_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.mtg_native_authority_current`

- Type: `VIEW`
- Observed rows: `0`
- Description: Database object discovered through read-only DuckDB introspection.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `mtg_asset_id` | `VARCHAR` | `YES` | `` |
| 2 | `mtg_lane` | `VARCHAR` | `YES` | `` |
| 3 | `native_asset_id` | `VARCHAR` | `YES` | `` |
| 4 | `product_name` | `VARCHAR` | `YES` | `` |
| 5 | `lane_authority_state` | `VARCHAR` | `YES` | `` |
| 6 | `current_price_usd` | `DOUBLE` | `YES` | `` |
| 7 | `current_price_authority_available` | `BOOLEAN` | `YES` | `` |
| 8 | `forecast_authority_available` | `BOOLEAN` | `YES` | `` |
| 9 | `forecast_1y_price_usd` | `DOUBLE` | `YES` | `` |
| 10 | `forecast_1y_return` | `DOUBLE` | `YES` | `` |
| 11 | `risk_authority_available` | `BOOLEAN` | `YES` | `` |
| 12 | `native_rank` | `BIGINT` | `YES` | `` |
| 13 | `native_rank_type` | `VARCHAR` | `YES` | `` |
| 14 | `native_purchase_status` | `VARCHAR` | `YES` | `` |
| 15 | `purchase_semantic` | `VARCHAR` | `YES` | `` |
| 16 | `evidence_state` | `VARCHAR` | `YES` | `` |
| 17 | `actionability_state` | `VARCHAR` | `YES` | `` |
| 18 | `execution_ready_purchase_certified` | `BOOLEAN` | `YES` | `` |
| 19 | `manual_execution_price_check_required` | `BOOLEAN` | `YES` | `` |
| 20 | `native_authority_pointer` | `VARCHAR` | `YES` | `` |
| 21 | `native_authority_sha256` | `VARCHAR` | `YES` | `` |
| 22 | `snapshot_population_is_permanent` | `BOOLEAN` | `YES` | `` |
| 23 | `automatic_purchase_execution` | `BOOLEAN` | `YES` | `` |
| 24 | `_import_id` | `VARCHAR` | `YES` | `` |
| 25 | `_package_id` | `VARCHAR` | `YES` | `` |
| 26 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 27 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 28 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 29 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 30 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW mtg_native_authority_current AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY mtg_asset_id ORDER BY _imported_at_utc DESC, _source_row_number DESC) AS _row_rank FROM mtg_native_authority_history) WHERE (_row_rank = 1);
```

</details>

### `main.mtg_native_authority_history`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Database object discovered through read-only DuckDB introspection.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `mtg_asset_id` | `VARCHAR` | `NO` | `` |
| 2 | `mtg_lane` | `VARCHAR` | `NO` | `` |
| 3 | `native_asset_id` | `VARCHAR` | `NO` | `` |
| 4 | `product_name` | `VARCHAR` | `NO` | `` |
| 5 | `lane_authority_state` | `VARCHAR` | `NO` | `` |
| 6 | `current_price_usd` | `DOUBLE` | `YES` | `` |
| 7 | `current_price_authority_available` | `BOOLEAN` | `NO` | `` |
| 8 | `forecast_authority_available` | `BOOLEAN` | `NO` | `` |
| 9 | `forecast_1y_price_usd` | `DOUBLE` | `YES` | `` |
| 10 | `forecast_1y_return` | `DOUBLE` | `YES` | `` |
| 11 | `risk_authority_available` | `BOOLEAN` | `NO` | `` |
| 12 | `native_rank` | `BIGINT` | `YES` | `` |
| 13 | `native_rank_type` | `VARCHAR` | `YES` | `` |
| 14 | `native_purchase_status` | `VARCHAR` | `YES` | `` |
| 15 | `purchase_semantic` | `VARCHAR` | `YES` | `` |
| 16 | `evidence_state` | `VARCHAR` | `NO` | `` |
| 17 | `actionability_state` | `VARCHAR` | `NO` | `` |
| 18 | `execution_ready_purchase_certified` | `BOOLEAN` | `NO` | `` |
| 19 | `manual_execution_price_check_required` | `BOOLEAN` | `NO` | `` |
| 20 | `native_authority_pointer` | `VARCHAR` | `NO` | `` |
| 21 | `native_authority_sha256` | `VARCHAR` | `NO` | `` |
| 22 | `snapshot_population_is_permanent` | `BOOLEAN` | `NO` | `` |
| 23 | `automatic_purchase_execution` | `BOOLEAN` | `NO` | `` |
| 24 | `_import_id` | `VARCHAR` | `NO` | `` |
| 25 | `_package_id` | `VARCHAR` | `NO` | `` |
| 26 | `_source_platform` | `VARCHAR` | `NO` | `` |
| 27 | `_source_filename` | `VARCHAR` | `NO` | `` |
| 28 | `_source_row_number` | `BIGINT` | `NO` | `` |
| 29 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 30 | `_imported_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.platform_status_current`

- Type: `VIEW`
- Observed rows: `0`
- Description: Current platform-status view.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `platform_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_name` | `VARCHAR` | `YES` | `` |
| 4 | `platform_version` | `VARCHAR` | `YES` | `` |
| 5 | `adapter_version` | `VARCHAR` | `YES` | `` |
| 6 | `contract_version` | `VARCHAR` | `YES` | `` |
| 7 | `run_status` | `VARCHAR` | `YES` | `` |
| 8 | `run_started_at_utc` | `TIMESTAMP` | `YES` | `` |
| 9 | `run_completed_at_utc` | `TIMESTAMP` | `YES` | `` |
| 10 | `data_as_of_date` | `DATE` | `YES` | `` |
| 11 | `records_published` | `BIGINT` | `YES` | `` |
| 12 | `warning_count` | `BIGINT` | `YES` | `` |
| 13 | `error_count` | `BIGINT` | `YES` | `` |
| 14 | `status_message` | `VARCHAR` | `YES` | `` |
| 15 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 16 | `_import_id` | `VARCHAR` | `YES` | `` |
| 17 | `_package_id` | `VARCHAR` | `YES` | `` |
| 18 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 19 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 20 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 21 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 22 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW platform_status_current AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY platform_id ORDER BY _imported_at_utc DESC, generated_at_utc DESC) AS _row_rank FROM platform_status_history) WHERE (_row_rank = 1);
```

</details>

### `main.platform_status_history`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Append-only history of source-platform publication and run status.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `platform_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_name` | `VARCHAR` | `YES` | `` |
| 4 | `platform_version` | `VARCHAR` | `YES` | `` |
| 5 | `adapter_version` | `VARCHAR` | `YES` | `` |
| 6 | `contract_version` | `VARCHAR` | `YES` | `` |
| 7 | `run_status` | `VARCHAR` | `YES` | `` |
| 8 | `run_started_at_utc` | `TIMESTAMP` | `YES` | `` |
| 9 | `run_completed_at_utc` | `TIMESTAMP` | `YES` | `` |
| 10 | `data_as_of_date` | `DATE` | `YES` | `` |
| 11 | `records_published` | `BIGINT` | `YES` | `` |
| 12 | `warning_count` | `BIGINT` | `YES` | `` |
| 13 | `error_count` | `BIGINT` | `YES` | `` |
| 14 | `status_message` | `VARCHAR` | `YES` | `` |
| 15 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 16 | `_import_id` | `VARCHAR` | `NO` | `` |
| 17 | `_package_id` | `VARCHAR` | `NO` | `` |
| 18 | `_source_platform` | `VARCHAR` | `NO` | `` |
| 19 | `_source_filename` | `VARCHAR` | `NO` | `` |
| 20 | `_source_row_number` | `BIGINT` | `NO` | `` |
| 21 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 22 | `_imported_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.portfolio_positions_current`

- Type: `VIEW`
- Observed rows: `0`
- Description: Current canonical portfolio-position view.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `account_id` | `VARCHAR` | `YES` | `` |
| 5 | `quantity` | `DOUBLE` | `YES` | `` |
| 6 | `unit_price` | `DOUBLE` | `YES` | `` |
| 7 | `position_value` | `DOUBLE` | `YES` | `` |
| 8 | `current_weight` | `DOUBLE` | `YES` | `` |
| 9 | `target_weight` | `DOUBLE` | `YES` | `` |
| 10 | `cost_basis` | `DOUBLE` | `YES` | `` |
| 11 | `unrealized_gain_loss` | `DOUBLE` | `YES` | `` |
| 12 | `currency` | `VARCHAR` | `YES` | `` |
| 13 | `source_system` | `VARCHAR` | `YES` | `` |
| 14 | `as_of_date` | `DATE` | `YES` | `` |
| 15 | `last_updated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 16 | `notes` | `VARCHAR` | `YES` | `` |
| 17 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 18 | `_import_id` | `VARCHAR` | `YES` | `` |
| 19 | `_package_id` | `VARCHAR` | `YES` | `` |
| 20 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 21 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 22 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 23 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 24 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW portfolio_positions_current AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY platform_id, account_id, universal_asset_id ORDER BY _imported_at_utc DESC, last_updated_at_utc DESC) AS _row_rank FROM portfolio_positions_history) WHERE (_row_rank = 1);
```

</details>

### `main.portfolio_positions_history`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Append-only history of canonical portfolio positions imported or derived for a platform run.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `account_id` | `VARCHAR` | `YES` | `` |
| 5 | `quantity` | `DOUBLE` | `YES` | `` |
| 6 | `unit_price` | `DOUBLE` | `YES` | `` |
| 7 | `position_value` | `DOUBLE` | `YES` | `` |
| 8 | `current_weight` | `DOUBLE` | `YES` | `` |
| 9 | `target_weight` | `DOUBLE` | `YES` | `` |
| 10 | `cost_basis` | `DOUBLE` | `YES` | `` |
| 11 | `unrealized_gain_loss` | `DOUBLE` | `YES` | `` |
| 12 | `currency` | `VARCHAR` | `YES` | `` |
| 13 | `source_system` | `VARCHAR` | `YES` | `` |
| 14 | `as_of_date` | `DATE` | `YES` | `` |
| 15 | `last_updated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 16 | `notes` | `VARCHAR` | `YES` | `` |
| 17 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 18 | `_import_id` | `VARCHAR` | `NO` | `` |
| 19 | `_package_id` | `VARCHAR` | `NO` | `` |
| 20 | `_source_platform` | `VARCHAR` | `NO` | `` |
| 21 | `_source_filename` | `VARCHAR` | `NO` | `` |
| 22 | `_source_row_number` | `BIGINT` | `NO` | `` |
| 23 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 24 | `_imported_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.recommendations_current`

- Type: `VIEW`
- Observed rows: `0`
- Description: Current recommendation view derived from recommendations_history.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `recommendation` | `VARCHAR` | `YES` | `` |
| 5 | `normalized_score` | `DOUBLE` | `YES` | `` |
| 6 | `confidence_score` | `DOUBLE` | `YES` | `` |
| 7 | `target_weight` | `DOUBLE` | `YES` | `` |
| 8 | `minimum_weight` | `DOUBLE` | `YES` | `` |
| 9 | `maximum_weight` | `DOUBLE` | `YES` | `` |
| 10 | `rationale` | `VARCHAR` | `YES` | `` |
| 11 | `risk_summary` | `VARCHAR` | `YES` | `` |
| 12 | `time_horizon_months` | `BIGINT` | `YES` | `` |
| 13 | `source_system` | `VARCHAR` | `YES` | `` |
| 14 | `model_version` | `VARCHAR` | `YES` | `` |
| 15 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 16 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 17 | `_import_id` | `VARCHAR` | `YES` | `` |
| 18 | `_package_id` | `VARCHAR` | `YES` | `` |
| 19 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 20 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 21 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 22 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 23 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW recommendations_current AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY universal_asset_id ORDER BY _imported_at_utc DESC, generated_at_utc DESC) AS _row_rank FROM recommendations_history) WHERE (_row_rank = 1);
```

</details>

### `main.recommendations_history`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Append-only history of recommendations and recommendation evidence.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `recommendation` | `VARCHAR` | `YES` | `` |
| 5 | `normalized_score` | `DOUBLE` | `YES` | `` |
| 6 | `confidence_score` | `DOUBLE` | `YES` | `` |
| 7 | `target_weight` | `DOUBLE` | `YES` | `` |
| 8 | `minimum_weight` | `DOUBLE` | `YES` | `` |
| 9 | `maximum_weight` | `DOUBLE` | `YES` | `` |
| 10 | `rationale` | `VARCHAR` | `YES` | `` |
| 11 | `risk_summary` | `VARCHAR` | `YES` | `` |
| 12 | `time_horizon_months` | `BIGINT` | `YES` | `` |
| 13 | `source_system` | `VARCHAR` | `YES` | `` |
| 14 | `model_version` | `VARCHAR` | `YES` | `` |
| 15 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 16 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 17 | `_import_id` | `VARCHAR` | `NO` | `` |
| 18 | `_package_id` | `VARCHAR` | `NO` | `` |
| 19 | `_source_platform` | `VARCHAR` | `NO` | `` |
| 20 | `_source_filename` | `VARCHAR` | `NO` | `` |
| 21 | `_source_row_number` | `BIGINT` | `NO` | `` |
| 22 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 23 | `_imported_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.risk_metrics_current`

- Type: `VIEW`
- Observed rows: `0`
- Description: Current risk-metric view derived from risk_metrics_history.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `risk_score` | `DOUBLE` | `YES` | `` |
| 5 | `risk_level` | `VARCHAR` | `YES` | `` |
| 6 | `volatility` | `DOUBLE` | `YES` | `` |
| 7 | `downside_volatility` | `DOUBLE` | `YES` | `` |
| 8 | `maximum_drawdown` | `DOUBLE` | `YES` | `` |
| 9 | `value_at_risk` | `DOUBLE` | `YES` | `` |
| 10 | `expected_shortfall` | `DOUBLE` | `YES` | `` |
| 11 | `beta` | `DOUBLE` | `YES` | `` |
| 12 | `liquidity_score` | `DOUBLE` | `YES` | `` |
| 13 | `concentration_score` | `DOUBLE` | `YES` | `` |
| 14 | `source_system` | `VARCHAR` | `YES` | `` |
| 15 | `model_version` | `VARCHAR` | `YES` | `` |
| 16 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 17 | `notes` | `VARCHAR` | `YES` | `` |
| 18 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 19 | `_import_id` | `VARCHAR` | `YES` | `` |
| 20 | `_package_id` | `VARCHAR` | `YES` | `` |
| 21 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 22 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 23 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 24 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 25 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW risk_metrics_current AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY universal_asset_id ORDER BY _imported_at_utc DESC, generated_at_utc DESC) AS _row_rank FROM risk_metrics_history) WHERE (_row_rank = 1);
```

</details>

### `main.risk_metrics_history`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Append-only history of asset-level risk measurements.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `run_id` | `VARCHAR` | `YES` | `` |
| 2 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `risk_score` | `DOUBLE` | `YES` | `` |
| 5 | `risk_level` | `VARCHAR` | `YES` | `` |
| 6 | `volatility` | `DOUBLE` | `YES` | `` |
| 7 | `downside_volatility` | `DOUBLE` | `YES` | `` |
| 8 | `maximum_drawdown` | `DOUBLE` | `YES` | `` |
| 9 | `value_at_risk` | `DOUBLE` | `YES` | `` |
| 10 | `expected_shortfall` | `DOUBLE` | `YES` | `` |
| 11 | `beta` | `DOUBLE` | `YES` | `` |
| 12 | `liquidity_score` | `DOUBLE` | `YES` | `` |
| 13 | `concentration_score` | `DOUBLE` | `YES` | `` |
| 14 | `source_system` | `VARCHAR` | `YES` | `` |
| 15 | `model_version` | `VARCHAR` | `YES` | `` |
| 16 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 17 | `notes` | `VARCHAR` | `YES` | `` |
| 18 | `metadata_json` | `VARCHAR` | `YES` | `` |
| 19 | `_import_id` | `VARCHAR` | `NO` | `` |
| 20 | `_package_id` | `VARCHAR` | `NO` | `` |
| 21 | `_source_platform` | `VARCHAR` | `NO` | `` |
| 22 | `_source_filename` | `VARCHAR` | `NO` | `` |
| 23 | `_source_row_number` | `BIGINT` | `NO` | `` |
| 24 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 25 | `_imported_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.universal_domain_operational_status`

- Type: `VIEW`
- Observed rows: `3`
- Description: Read-only join of governed domain authority with current universal platform import and package operational state.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `domain_id` | `VARCHAR` | `YES` | `` |
| 2 | `domain_name` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `ownership_type` | `VARCHAR` | `YES` | `` |
| 5 | `source_repository` | `VARCHAR` | `YES` | `` |
| 6 | `publication_boundary` | `VARCHAR` | `YES` | `` |
| 7 | `certification_state` | `VARCHAR` | `YES` | `` |
| 8 | `dynamic_asset_universe` | `BOOLEAN` | `YES` | `` |
| 9 | `native_semantics_authoritative` | `BOOLEAN` | `YES` | `` |
| 10 | `cross_asset_ranking_authorized` | `BOOLEAN` | `YES` | `` |
| 11 | `automatic_execution_authorized` | `BOOLEAN` | `YES` | `` |
| 12 | `registry_version` | `VARCHAR` | `YES` | `` |
| 13 | `platform_name` | `VARCHAR` | `YES` | `` |
| 14 | `platform_version` | `VARCHAR` | `YES` | `` |
| 15 | `adapter_version` | `VARCHAR` | `YES` | `` |
| 16 | `contract_version` | `VARCHAR` | `YES` | `` |
| 17 | `import_registry_status` | `VARCHAR` | `YES` | `` |
| 18 | `last_package_id` | `VARCHAR` | `YES` | `` |
| 19 | `last_run_id` | `VARCHAR` | `YES` | `` |
| 20 | `last_import_id` | `VARCHAR` | `YES` | `` |
| 21 | `last_import_status` | `VARCHAR` | `YES` | `` |
| 22 | `last_imported_at_utc` | `TIMESTAMP` | `YES` | `` |
| 23 | `last_data_as_of_date` | `DATE` | `YES` | `` |
| 24 | `warning_count` | `BIGINT` | `YES` | `` |
| 25 | `error_count` | `BIGINT` | `YES` | `` |
| 26 | `status_message` | `VARCHAR` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW universal_domain_operational_status AS SELECT d.domain_id, d.domain_name, d.platform_id, d.ownership_type, d.source_repository, d.publication_boundary, d.certification_state, d.dynamic_asset_universe, d.native_semantics_authoritative, d.cross_asset_ranking_authorized, d.automatic_execution_authorized, d.registry_version, p.platform_name, p.platform_version, p.adapter_version, p.contract_version, p.registry_status AS import_registry_status, p.last_package_id, p.last_run_id, p.last_import_id, p.last_import_status, p.last_imported_at_utc, p.last_data_as_of_date, p.warning_count, p.error_count, p.status_message FROM universal_domain_registry AS d LEFT JOIN universal_platform_registry AS p ON ((p.platform_id = d.platform_id));
```

</details>

### `main.universal_domain_registry`

- Type: `BASE TABLE`
- Observed rows: `3`
- Description: Governed D1 registry of currently certified UIP investment domains, their ownership boundaries, publication boundaries, semantic authority, and explicit execution restrictions.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `domain_id` | `VARCHAR` | `NO` | `` |
| 2 | `domain_name` | `VARCHAR` | `NO` | `` |
| 3 | `platform_id` | `VARCHAR` | `NO` | `` |
| 4 | `ownership_type` | `VARCHAR` | `NO` | `` |
| 5 | `source_repository` | `VARCHAR` | `YES` | `` |
| 6 | `publication_boundary` | `VARCHAR` | `NO` | `` |
| 7 | `certification_state` | `VARCHAR` | `NO` | `` |
| 8 | `dynamic_asset_universe` | `BOOLEAN` | `NO` | `` |
| 9 | `native_semantics_authoritative` | `BOOLEAN` | `NO` | `` |
| 10 | `cross_asset_ranking_authorized` | `BOOLEAN` | `NO` | `` |
| 11 | `automatic_execution_authorized` | `BOOLEAN` | `NO` | `` |
| 12 | `registry_version` | `VARCHAR` | `NO` | `` |
| 13 | `notes` | `VARCHAR` | `YES` | `` |

**Constraints**

- `PRIMARY KEY`: `PRIMARY KEY(domain_id)`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.universal_import_datasets`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Dataset-level evidence for universal import attempts.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `import_dataset_id` | `VARCHAR` | `NO` | `` |
| 2 | `import_id` | `VARCHAR` | `NO` | `` |
| 3 | `dataset_name` | `VARCHAR` | `NO` | `` |
| 4 | `source_filename` | `VARCHAR` | `NO` | `` |
| 5 | `required` | `BOOLEAN` | `YES` | `CAST('f' AS BOOLEAN)` |
| 6 | `expected_row_count` | `BIGINT` | `YES` | `0` |
| 7 | `imported_row_count` | `BIGINT` | `YES` | `0` |
| 8 | `source_sha256` | `VARCHAR` | `YES` | `` |
| 9 | `calculated_sha256` | `VARCHAR` | `YES` | `` |
| 10 | `contract_status` | `VARCHAR` | `YES` | `` |
| 11 | `checksum_status` | `VARCHAR` | `YES` | `` |
| 12 | `load_status` | `VARCHAR` | `YES` | `` |
| 13 | `warning_count` | `BIGINT` | `YES` | `0` |
| 14 | `error_count` | `BIGINT` | `YES` | `0` |
| 15 | `error_summary` | `VARCHAR` | `YES` | `` |

**Constraints**

- `PRIMARY KEY`: `PRIMARY KEY(import_dataset_id)`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.universal_import_error_summary`

- Type: `VIEW`
- Observed rows: `0`
- Description: Aggregated current import-error summary.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `import_id` | `VARCHAR` | `YES` | `` |
| 2 | `severity` | `VARCHAR` | `YES` | `` |
| 3 | `error_code` | `VARCHAR` | `YES` | `` |
| 4 | `occurrence_count` | `BIGINT` | `YES` | `` |
| 5 | `first_seen_at_utc` | `TIMESTAMP` | `YES` | `` |
| 6 | `last_seen_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW universal_import_error_summary AS SELECT import_id, severity, error_code, count_star() AS occurrence_count, min(created_at_utc) AS first_seen_at_utc, max(created_at_utc) AS last_seen_at_utc FROM universal_import_errors GROUP BY import_id, severity, error_code;
```

</details>

### `main.universal_import_errors`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Detailed import-validation and activation errors.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `import_error_id` | `VARCHAR` | `NO` | `` |
| 2 | `import_id` | `VARCHAR` | `NO` | `` |
| 3 | `dataset_name` | `VARCHAR` | `YES` | `` |
| 4 | `severity` | `VARCHAR` | `NO` | `` |
| 5 | `error_code` | `VARCHAR` | `YES` | `` |
| 6 | `error_message` | `VARCHAR` | `NO` | `` |
| 7 | `source_filename` | `VARCHAR` | `YES` | `` |
| 8 | `source_row_number` | `BIGINT` | `YES` | `` |
| 9 | `created_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `PRIMARY KEY`: `PRIMARY KEY(import_error_id)`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.universal_import_health`

- Type: `VIEW`
- Observed rows: `0`
- Description: Current import-health view by source platform.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `platform_id` | `VARCHAR` | `YES` | `` |
| 2 | `platform_name` | `VARCHAR` | `YES` | `` |
| 3 | `platform_version` | `VARCHAR` | `YES` | `` |
| 4 | `adapter_version` | `VARCHAR` | `YES` | `` |
| 5 | `contract_version` | `VARCHAR` | `YES` | `` |
| 6 | `registry_status` | `VARCHAR` | `YES` | `` |
| 7 | `last_package_id` | `VARCHAR` | `YES` | `` |
| 8 | `last_run_id` | `VARCHAR` | `YES` | `` |
| 9 | `last_import_id` | `VARCHAR` | `YES` | `` |
| 10 | `last_import_status` | `VARCHAR` | `YES` | `` |
| 11 | `last_imported_at_utc` | `TIMESTAMP` | `YES` | `` |
| 12 | `last_data_as_of_date` | `DATE` | `YES` | `` |
| 13 | `total_successful_imports` | `BIGINT` | `YES` | `` |
| 14 | `total_failed_imports` | `BIGINT` | `YES` | `` |
| 15 | `total_rows_imported` | `BIGINT` | `YES` | `` |
| 16 | `warning_count` | `BIGINT` | `YES` | `` |
| 17 | `error_count` | `BIGINT` | `YES` | `` |
| 18 | `status_message` | `VARCHAR` | `YES` | `` |
| 19 | `health_status` | `VARCHAR` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW universal_import_health AS SELECT r.platform_id, r.platform_name, r.platform_version, r.adapter_version, r.contract_version, r.registry_status, r.last_package_id, r.last_run_id, r.last_import_id, r.last_import_status, r.last_imported_at_utc, r.last_data_as_of_date, r.total_successful_imports, r.total_failed_imports, r.total_rows_imported, r.warning_count, r.error_count, r.status_message, CASE  WHEN (((r.registry_status = 'ACTIVE') AND (r.last_import_status = 'IMPORTED'))) THEN ('HEALTHY') WHEN ((r.last_import_status IN ('FAILED', 'REJECTED'))) THEN ('DEGRADED') WHEN ((r.last_import_status IS NULL)) THEN ('NOT_IMPORTED') ELSE 'WARNING' END AS health_status FROM universal_platform_registry AS r;
```

</details>

### `main.universal_imports`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Import-attempt registry containing package, platform, timing, and outcome evidence.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `import_id` | `VARCHAR` | `NO` | `` |
| 2 | `package_id` | `VARCHAR` | `NO` | `` |
| 3 | `platform_id` | `VARCHAR` | `NO` | `` |
| 4 | `run_id` | `VARCHAR` | `YES` | `` |
| 5 | `adapter_version` | `VARCHAR` | `YES` | `` |
| 6 | `contract_version` | `VARCHAR` | `YES` | `` |
| 7 | `import_mode` | `VARCHAR` | `NO` | `` |
| 8 | `import_status` | `VARCHAR` | `NO` | `` |
| 9 | `package_path` | `VARCHAR` | `NO` | `` |
| 10 | `manifest_sha256` | `VARCHAR` | `YES` | `` |
| 11 | `discovered_at_utc` | `TIMESTAMP` | `YES` | `` |
| 12 | `started_at_utc` | `TIMESTAMP` | `YES` | `` |
| 13 | `completed_at_utc` | `TIMESTAMP` | `YES` | `` |
| 14 | `dataset_count` | `BIGINT` | `YES` | `0` |
| 15 | `expected_row_count` | `BIGINT` | `YES` | `0` |
| 16 | `imported_row_count` | `BIGINT` | `YES` | `0` |
| 17 | `warning_count` | `BIGINT` | `YES` | `0` |
| 18 | `error_count` | `BIGINT` | `YES` | `0` |
| 19 | `error_summary` | `VARCHAR` | `YES` | `` |

**Constraints**

- `PRIMARY KEY`: `PRIMARY KEY(import_id)`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.universal_latest_import_attempt`

- Type: `VIEW`
- Observed rows: `0`
- Description: Latest import attempt per platform.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `import_id` | `VARCHAR` | `YES` | `` |
| 2 | `package_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `run_id` | `VARCHAR` | `YES` | `` |
| 5 | `adapter_version` | `VARCHAR` | `YES` | `` |
| 6 | `contract_version` | `VARCHAR` | `YES` | `` |
| 7 | `import_mode` | `VARCHAR` | `YES` | `` |
| 8 | `import_status` | `VARCHAR` | `YES` | `` |
| 9 | `package_path` | `VARCHAR` | `YES` | `` |
| 10 | `manifest_sha256` | `VARCHAR` | `YES` | `` |
| 11 | `discovered_at_utc` | `TIMESTAMP` | `YES` | `` |
| 12 | `started_at_utc` | `TIMESTAMP` | `YES` | `` |
| 13 | `completed_at_utc` | `TIMESTAMP` | `YES` | `` |
| 14 | `dataset_count` | `BIGINT` | `YES` | `` |
| 15 | `expected_row_count` | `BIGINT` | `YES` | `` |
| 16 | `imported_row_count` | `BIGINT` | `YES` | `` |
| 17 | `warning_count` | `BIGINT` | `YES` | `` |
| 18 | `error_count` | `BIGINT` | `YES` | `` |
| 19 | `error_summary` | `VARCHAR` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW universal_latest_import_attempt AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY platform_id ORDER BY started_at_utc DESC NULLS LAST, discovered_at_utc DESC NULLS LAST) AS _row_rank FROM universal_imports) WHERE (_row_rank = 1);
```

</details>

### `main.universal_latest_successful_import`

- Type: `VIEW`
- Observed rows: `0`
- Description: Latest successfully activated import per platform.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `import_id` | `VARCHAR` | `YES` | `` |
| 2 | `package_id` | `VARCHAR` | `YES` | `` |
| 3 | `platform_id` | `VARCHAR` | `YES` | `` |
| 4 | `run_id` | `VARCHAR` | `YES` | `` |
| 5 | `adapter_version` | `VARCHAR` | `YES` | `` |
| 6 | `contract_version` | `VARCHAR` | `YES` | `` |
| 7 | `import_mode` | `VARCHAR` | `YES` | `` |
| 8 | `import_status` | `VARCHAR` | `YES` | `` |
| 9 | `package_path` | `VARCHAR` | `YES` | `` |
| 10 | `manifest_sha256` | `VARCHAR` | `YES` | `` |
| 11 | `discovered_at_utc` | `TIMESTAMP` | `YES` | `` |
| 12 | `started_at_utc` | `TIMESTAMP` | `YES` | `` |
| 13 | `completed_at_utc` | `TIMESTAMP` | `YES` | `` |
| 14 | `dataset_count` | `BIGINT` | `YES` | `` |
| 15 | `expected_row_count` | `BIGINT` | `YES` | `` |
| 16 | `imported_row_count` | `BIGINT` | `YES` | `` |
| 17 | `warning_count` | `BIGINT` | `YES` | `` |
| 18 | `error_count` | `BIGINT` | `YES` | `` |
| 19 | `error_summary` | `VARCHAR` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW universal_latest_successful_import AS SELECT * EXCLUDE (_row_rank) FROM (SELECT *, row_number() OVER (PARTITION BY platform_id ORDER BY completed_at_utc DESC NULLS LAST, started_at_utc DESC NULLS LAST) AS _row_rank FROM universal_imports WHERE (import_status = 'IMPORTED')) WHERE (_row_rank = 1);
```

</details>

### `main.universal_lineage_with_domain`

- Type: `VIEW`
- Observed rows: `0`
- Description: Common row lineage enriched with governed domain identity and native-semantic ownership without redefining source-domain results.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `domain_id` | `VARCHAR` | `YES` | `` |
| 2 | `domain_name` | `VARCHAR` | `YES` | `` |
| 3 | `ownership_type` | `VARCHAR` | `YES` | `` |
| 4 | `native_semantics_authoritative` | `BOOLEAN` | `YES` | `` |
| 5 | `dataset_name` | `VARCHAR` | `YES` | `` |
| 6 | `platform_id` | `VARCHAR` | `YES` | `` |
| 7 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 8 | `run_id` | `VARCHAR` | `YES` | `` |
| 9 | `_import_id` | `VARCHAR` | `YES` | `` |
| 10 | `_package_id` | `VARCHAR` | `YES` | `` |
| 11 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 12 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 13 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 14 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 15 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW universal_lineage_with_domain AS SELECT d.domain_id, d.domain_name, d.ownership_type, d.native_semantics_authoritative, l.dataset_name, l.platform_id, l.universal_asset_id, l.run_id, l._import_id, l._package_id, l._source_platform, l._source_filename, l._source_row_number, l._manifest_sha256, l._imported_at_utc FROM universal_row_lineage AS l LEFT JOIN universal_domain_registry AS d ON ((d.platform_id = l.platform_id));
```

</details>

### `main.universal_packages`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Registry of received and validated universal delivery packages.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `package_id` | `VARCHAR` | `NO` | `` |
| 2 | `platform_id` | `VARCHAR` | `NO` | `` |
| 3 | `run_id` | `VARCHAR` | `YES` | `` |
| 4 | `adapter_version` | `VARCHAR` | `YES` | `` |
| 5 | `contract_version` | `VARCHAR` | `YES` | `` |
| 6 | `package_status` | `VARCHAR` | `NO` | `` |
| 7 | `package_path` | `VARCHAR` | `NO` | `` |
| 8 | `manifest_sha256` | `VARCHAR` | `YES` | `` |
| 9 | `generated_at_utc` | `TIMESTAMP` | `YES` | `` |
| 10 | `first_seen_at_utc` | `TIMESTAMP` | `NO` | `` |
| 11 | `last_seen_at_utc` | `TIMESTAMP` | `NO` | `` |
| 12 | `successful_import_id` | `VARCHAR` | `YES` | `` |

**Constraints**

- `PRIMARY KEY`: `PRIMARY KEY(package_id)`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.universal_platform_registry`

- Type: `BASE TABLE`
- Observed rows: `0`
- Description: Operational import-state registry for integrated source platforms.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `platform_id` | `VARCHAR` | `NO` | `` |
| 2 | `platform_name` | `VARCHAR` | `YES` | `` |
| 3 | `platform_version` | `VARCHAR` | `YES` | `` |
| 4 | `adapter_version` | `VARCHAR` | `YES` | `` |
| 5 | `contract_version` | `VARCHAR` | `YES` | `` |
| 6 | `registry_status` | `VARCHAR` | `NO` | `` |
| 7 | `last_package_id` | `VARCHAR` | `YES` | `` |
| 8 | `last_run_id` | `VARCHAR` | `YES` | `` |
| 9 | `last_import_id` | `VARCHAR` | `YES` | `` |
| 10 | `last_import_status` | `VARCHAR` | `YES` | `` |
| 11 | `last_imported_at_utc` | `TIMESTAMP` | `YES` | `` |
| 12 | `last_data_as_of_date` | `DATE` | `YES` | `` |
| 13 | `total_successful_imports` | `BIGINT` | `YES` | `0` |
| 14 | `total_failed_imports` | `BIGINT` | `YES` | `0` |
| 15 | `total_rows_imported` | `BIGINT` | `YES` | `0` |
| 16 | `warning_count` | `BIGINT` | `YES` | `0` |
| 17 | `error_count` | `BIGINT` | `YES` | `0` |
| 18 | `status_message` | `VARCHAR` | `YES` | `` |
| 19 | `created_at_utc` | `TIMESTAMP` | `NO` | `` |
| 20 | `updated_at_utc` | `TIMESTAMP` | `NO` | `` |

**Constraints**

- `PRIMARY KEY`: `PRIMARY KEY(platform_id)`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`
- `NOT NULL`: `NOT NULL`

### `main.universal_row_lineage`

- Type: `VIEW`
- Observed rows: `0`
- Description: Lossless common row-lineage interface across certified universal history datasets and MTG native-authority history.

| Position | Column | Type | Nullable | Default |
|---:|---|---|---|---|
| 1 | `dataset_name` | `VARCHAR` | `YES` | `` |
| 2 | `platform_id` | `VARCHAR` | `YES` | `` |
| 3 | `universal_asset_id` | `VARCHAR` | `YES` | `` |
| 4 | `run_id` | `VARCHAR` | `YES` | `` |
| 5 | `_import_id` | `VARCHAR` | `YES` | `` |
| 6 | `_package_id` | `VARCHAR` | `YES` | `` |
| 7 | `_source_platform` | `VARCHAR` | `YES` | `` |
| 8 | `_source_filename` | `VARCHAR` | `YES` | `` |
| 9 | `_source_row_number` | `BIGINT` | `YES` | `` |
| 10 | `_manifest_sha256` | `VARCHAR` | `YES` | `` |
| 11 | `_imported_at_utc` | `TIMESTAMP` | `YES` | `` |

<details>
<summary>View definition</summary>

```sql
CREATE VIEW universal_row_lineage AS (SELECT 'asset_master' AS dataset_name, platform_id, universal_asset_id, run_id, _import_id, _package_id, _source_platform, _source_filename, _source_row_number, _manifest_sha256, _imported_at_utc FROM asset_master_history) UNION ALL ((((SELECT 'forecasts' AS dataset_name, platform_id, universal_asset_id, run_id, _import_id, _package_id, _source_platform, _source_filename, _source_row_number, _manifest_sha256, _imported_at_utc FROM forecasts_history) UNION ALL (SELECT 'recommendations' AS dataset_name, platform_id, universal_asset_id, run_id, _import_id, _package_id, _source_platform, _source_filename, _source_row_number, _manifest_sha256, _imported_at_utc FROM recommendations_history)) UNION ALL ((SELECT 'risk_metrics' AS dataset_name, platform_id, universal_asset_id, run_id, _import_id, _package_id, _source_platform, _source_filename, _source_row_number, _manifest_sha256, _imported_at_utc FROM risk_metrics_history) UNION ALL (SELECT 'portfolio_positions' AS dataset_name, platform_id, universal_asset_id, run_id, _import_id, _package_id, _source_platform, _source_filename, _source_row_number, _manifest_sha256, _imported_at_utc FROM portfolio_positions_history))) UNION ALL (((SELECT 'platform_status' AS dataset_name, platform_id, CAST(NULL AS VARCHAR) AS universal_asset_id, run_id, _import_id, _package_id, _source_platform, _source_filename, _source_row_number, _manifest_sha256, _imported_at_utc FROM platform_status_history) UNION ALL (SELECT 'historical_performance' AS dataset_name, platform_id, universal_asset_id, run_id, _import_id, _package_id, _source_platform, _source_filename, _source_row_number, _manifest_sha256, _imported_at_utc FROM historical_performance_history)) UNION ALL (SELECT 'mtg_native_authority' AS dataset_name, 'mtg' AS platform_id, mtg_asset_id AS universal_asset_id, CAST(NULL AS VARCHAR) AS run_id, _import_id, _package_id, _source_platform, _source_filename, _source_row_number, _manifest_sha256, _imported_at_utc FROM mtg_native_authority_history)));
```

</details>

## Interpretation rule

When the migration chain, observed production schema, generated catalog, and semantic dictionary disagree, stop and reconcile the discrepancy. Do not silently treat generated documentation as migration authority.
