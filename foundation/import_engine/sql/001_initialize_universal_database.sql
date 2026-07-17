CREATE TABLE IF NOT EXISTS universal_imports (
    import_id VARCHAR PRIMARY KEY,
    package_id VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    run_id VARCHAR,
    adapter_version VARCHAR,
    contract_version VARCHAR,
    import_mode VARCHAR NOT NULL,
    import_status VARCHAR NOT NULL,
    package_path VARCHAR NOT NULL,
    manifest_sha256 VARCHAR,
    discovered_at_utc TIMESTAMP,
    started_at_utc TIMESTAMP,
    completed_at_utc TIMESTAMP,
    dataset_count BIGINT DEFAULT 0,
    expected_row_count BIGINT DEFAULT 0,
    imported_row_count BIGINT DEFAULT 0,
    warning_count BIGINT DEFAULT 0,
    error_count BIGINT DEFAULT 0,
    error_summary VARCHAR
);

CREATE TABLE IF NOT EXISTS universal_import_datasets (
    import_dataset_id VARCHAR PRIMARY KEY,
    import_id VARCHAR NOT NULL,
    dataset_name VARCHAR NOT NULL,
    source_filename VARCHAR NOT NULL,
    required BOOLEAN DEFAULT FALSE,
    expected_row_count BIGINT DEFAULT 0,
    imported_row_count BIGINT DEFAULT 0,
    source_sha256 VARCHAR,
    calculated_sha256 VARCHAR,
    contract_status VARCHAR,
    checksum_status VARCHAR,
    load_status VARCHAR,
    warning_count BIGINT DEFAULT 0,
    error_count BIGINT DEFAULT 0,
    error_summary VARCHAR
);

CREATE TABLE IF NOT EXISTS universal_import_errors (
    import_error_id VARCHAR PRIMARY KEY,
    import_id VARCHAR NOT NULL,
    dataset_name VARCHAR,
    severity VARCHAR NOT NULL,
    error_code VARCHAR,
    error_message VARCHAR NOT NULL,
    source_filename VARCHAR,
    source_row_number BIGINT,
    created_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS universal_packages (
    package_id VARCHAR PRIMARY KEY,
    platform_id VARCHAR NOT NULL,
    run_id VARCHAR,
    adapter_version VARCHAR,
    contract_version VARCHAR,
    package_status VARCHAR NOT NULL,
    package_path VARCHAR NOT NULL,
    manifest_sha256 VARCHAR,
    generated_at_utc TIMESTAMP,
    first_seen_at_utc TIMESTAMP NOT NULL,
    last_seen_at_utc TIMESTAMP NOT NULL,
    successful_import_id VARCHAR
);

CREATE TABLE IF NOT EXISTS asset_master_history (
    run_id VARCHAR,
    universal_asset_id VARCHAR,
    platform_asset_id VARCHAR,
    platform_id VARCHAR,
    asset_name VARCHAR,
    asset_symbol VARCHAR,
    asset_class VARCHAR,
    asset_subclass VARCHAR,
    currency VARCHAR,
    investable BOOLEAN,
    active BOOLEAN,
    source_system VARCHAR,
    source_record_id VARCHAR,
    first_observed_date DATE,
    last_observed_date DATE,
    last_updated_at_utc TIMESTAMP,
    notes VARCHAR,
    metadata_json VARCHAR,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_platform VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS forecasts_history (
    run_id VARCHAR,
    universal_asset_id VARCHAR,
    platform_id VARCHAR,
    forecast_origin_date DATE,
    forecast_horizon_months BIGINT,
    forecast_method VARCHAR,
    point_forecast DOUBLE,
    lower_bound DOUBLE,
    upper_bound DOUBLE,
    expected_return DOUBLE,
    probability_positive DOUBLE,
    confidence_score DOUBLE,
    scenario VARCHAR,
    source_system VARCHAR,
    model_version VARCHAR,
    generated_at_utc TIMESTAMP,
    notes VARCHAR,
    metadata_json VARCHAR,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_platform VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS recommendations_history (
    run_id VARCHAR,
    universal_asset_id VARCHAR,
    platform_id VARCHAR,
    recommendation VARCHAR,
    normalized_score DOUBLE,
    confidence_score DOUBLE,
    target_weight DOUBLE,
    minimum_weight DOUBLE,
    maximum_weight DOUBLE,
    rationale VARCHAR,
    risk_summary VARCHAR,
    time_horizon_months BIGINT,
    source_system VARCHAR,
    model_version VARCHAR,
    generated_at_utc TIMESTAMP,
    metadata_json VARCHAR,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_platform VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS risk_metrics_history (
    run_id VARCHAR,
    universal_asset_id VARCHAR,
    platform_id VARCHAR,
    risk_score DOUBLE,
    risk_level VARCHAR,
    volatility DOUBLE,
    downside_volatility DOUBLE,
    maximum_drawdown DOUBLE,
    value_at_risk DOUBLE,
    expected_shortfall DOUBLE,
    beta DOUBLE,
    liquidity_score DOUBLE,
    concentration_score DOUBLE,
    source_system VARCHAR,
    model_version VARCHAR,
    generated_at_utc TIMESTAMP,
    notes VARCHAR,
    metadata_json VARCHAR,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_platform VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS portfolio_positions_history (
    run_id VARCHAR,
    universal_asset_id VARCHAR,
    platform_id VARCHAR,
    account_id VARCHAR,
    quantity DOUBLE,
    unit_price DOUBLE,
    position_value DOUBLE,
    current_weight DOUBLE,
    target_weight DOUBLE,
    cost_basis DOUBLE,
    unrealized_gain_loss DOUBLE,
    currency VARCHAR,
    source_system VARCHAR,
    as_of_date DATE,
    last_updated_at_utc TIMESTAMP,
    notes VARCHAR,
    metadata_json VARCHAR,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_platform VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS platform_status_history (
    run_id VARCHAR,
    platform_id VARCHAR,
    platform_name VARCHAR,
    platform_version VARCHAR,
    adapter_version VARCHAR,
    contract_version VARCHAR,
    run_status VARCHAR,
    run_started_at_utc TIMESTAMP,
    run_completed_at_utc TIMESTAMP,
    data_as_of_date DATE,
    records_published BIGINT,
    warning_count BIGINT,
    error_count BIGINT,
    status_message VARCHAR,
    generated_at_utc TIMESTAMP,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_platform VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS macro_signals_history (
    run_id VARCHAR,
    signal_id VARCHAR,
    platform_id VARCHAR,
    signal_name VARCHAR,
    signal_category VARCHAR,
    signal_value DOUBLE,
    normalized_score DOUBLE,
    signal_direction VARCHAR,
    signal_status VARCHAR,
    confidence_score DOUBLE,
    observation_date DATE,
    source_system VARCHAR,
    model_version VARCHAR,
    generated_at_utc TIMESTAMP,
    notes VARCHAR,
    metadata_json VARCHAR,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_platform VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _imported_at_utc TIMESTAMP NOT NULL
);

CREATE OR REPLACE VIEW asset_master_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY universal_asset_id
            ORDER BY _imported_at_utc DESC, last_updated_at_utc DESC
        ) AS _row_rank
    FROM asset_master_history
)
WHERE _row_rank = 1;

CREATE OR REPLACE VIEW forecasts_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY universal_asset_id, forecast_horizon_months, forecast_method
            ORDER BY _imported_at_utc DESC, generated_at_utc DESC
        ) AS _row_rank
    FROM forecasts_history
)
WHERE _row_rank = 1;

CREATE OR REPLACE VIEW recommendations_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY universal_asset_id
            ORDER BY _imported_at_utc DESC, generated_at_utc DESC
        ) AS _row_rank
    FROM recommendations_history
)
WHERE _row_rank = 1;

CREATE OR REPLACE VIEW risk_metrics_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY universal_asset_id
            ORDER BY _imported_at_utc DESC, generated_at_utc DESC
        ) AS _row_rank
    FROM risk_metrics_history
)
WHERE _row_rank = 1;

CREATE OR REPLACE VIEW portfolio_positions_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY platform_id, account_id, universal_asset_id
            ORDER BY _imported_at_utc DESC, last_updated_at_utc DESC
        ) AS _row_rank
    FROM portfolio_positions_history
)
WHERE _row_rank = 1;

CREATE OR REPLACE VIEW platform_status_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY platform_id
            ORDER BY _imported_at_utc DESC, generated_at_utc DESC
        ) AS _row_rank
    FROM platform_status_history
)
WHERE _row_rank = 1;

CREATE OR REPLACE VIEW macro_signals_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY signal_id
            ORDER BY _imported_at_utc DESC, generated_at_utc DESC
        ) AS _row_rank
    FROM macro_signals_history
)
WHERE _row_rank = 1;