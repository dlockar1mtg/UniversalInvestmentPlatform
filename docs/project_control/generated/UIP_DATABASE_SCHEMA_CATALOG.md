# UIP Database Schema Catalog

## Generation evidence

- Database: `data/universal/universal_investment.duckdb`
- Database SHA-256: `dcc390bba481d649f591847ec32332f725b0b62473dcc4104d51e8c532076116`
- Database size: `11546624` bytes
- Inspected at: `2026-07-30T15:48:06.222874+00:00`
- Inspection mode: `READ_ONLY`
- Database objects: `23`
- Ordered SQL files: `3`

This catalog is generated from read-only DuckDB introspection. It records observed implementation evidence; it does not by itself authorize a schema change.

## Ordered SQL authority inventory

| Order | File | SHA-256 | Purpose |
|---:|---|---|---|
| 1 | `foundation/import_engine/sql/001_initialize_universal_database.sql` | `702d1e48edb79d6c0595586b12332619d71d4cb87201f3c3a12d40c1409225da` | create or extend canonical tables |
| 2 | `foundation/import_engine/sql/002_audit_registry_integration.sql` | `9563d6ca0a0b120d4de15a6fd78d47fd4d3f4c5afa530886a8289c8011b1cc5d` | create or extend canonical tables; import audit and platform registry |
| 3 | `foundation/import_engine/sql/003_health_status_latest_attempt.sql` | `130f47a6e95bbc8e2479466e2ea6f42d05e726f7fc22f94fd4a2f96fdbef7624` | import audit and platform registry |

## Database objects

### `main.asset_master_current`

- Type: `VIEW`
- Observed rows: `1174`
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
- Observed rows: `8199`
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
- Observed rows: `1499`
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
- Observed rows: `5254`
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

### `main.platform_status_current`

- Type: `VIEW`
- Observed rows: `3`
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
- Observed rows: `24`
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
- Observed rows: `12`
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
- Observed rows: `66`
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
- Observed rows: `1169`
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
- Observed rows: `5285`
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
- Observed rows: `1168`
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
- Observed rows: `2439`
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

### `main.universal_import_datasets`

- Type: `BASE TABLE`
- Observed rows: `132`
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
- Observed rows: `1`
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
- Observed rows: `1`
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
- Observed rows: `3`
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
- Observed rows: `25`
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
- Observed rows: `3`
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
- Observed rows: `3`
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

### `main.universal_packages`

- Type: `BASE TABLE`
- Observed rows: `24`
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
- Observed rows: `3`
- Description: Canonical registry of integrated source platforms.

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

## Interpretation rule

When the migration chain, observed production schema, generated catalog, and semantic dictionary disagree, stop and reconcile the discrepancy. Do not silently treat generated documentation as migration authority.
