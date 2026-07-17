# Universal Database Standard

## Database Location

data/universal/universal_investment.duckdb

## Administrative Tables

### universal_imports

One row per import attempt.

Recommended fields:

- import_id
- package_id
- platform_id
- run_id
- adapter_version
- contract_version
- import_mode
- import_status
- package_path
- manifest_sha256
- discovered_at_utc
- started_at_utc
- completed_at_utc
- dataset_count
- expected_row_count
- imported_row_count
- warning_count
- error_count
- error_summary

### universal_import_datasets

One row per dataset in an import.

Recommended fields:

- import_dataset_id
- import_id
- dataset_name
- source_filename
- required
- expected_row_count
- imported_row_count
- source_sha256
- calculated_sha256
- contract_status
- checksum_status
- load_status
- warning_count
- error_count
- error_summary

### universal_import_errors

One row per warning or error.

Recommended fields:

- import_error_id
- import_id
- dataset_name
- severity
- error_code
- error_message
- source_filename
- source_row_number
- created_at_utc

### universal_packages

One row per known package.

Recommended fields:

- package_id
- platform_id
- run_id
- adapter_version
- contract_version
- package_status
- package_path
- manifest_sha256
- generated_at_utc
- first_seen_at_utc
- last_seen_at_utc
- successful_import_id

## Universal History Tables

- asset_master_history
- forecasts_history
- recommendations_history
- risk_metrics_history
- portfolio_positions_history
- platform_status_history
- macro_signals_history

## Ingestion Metadata

Every history table must include:

- _import_id
- _package_id
- _source_platform
- _source_filename
- _source_row_number
- _manifest_sha256
- _imported_at_utc

## Current-State Views

- asset_master_current
- forecasts_current
- recommendations_current
- risk_metrics_current
- portfolio_positions_current
- platform_status_current
- macro_signals_current

Current-state views must select the latest accepted record according to the
dataset's natural business key and import timestamp.