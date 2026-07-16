-- ============================================================
-- Universal Investment Intelligence Platform
-- Phase 0.5 Integration Database Schema
-- ============================================================

CREATE SCHEMA IF NOT EXISTS meta;
CREATE SCHEMA IF NOT EXISTS registry;
CREATE SCHEMA IF NOT EXISTS contracts;
CREATE SCHEMA IF NOT EXISTS analytics;

-- ============================================================
-- Metadata and import auditing
-- ============================================================

CREATE TABLE IF NOT EXISTS meta.database_version (
    version VARCHAR NOT NULL,
    applied_at_utc TIMESTAMP NOT NULL,
    description VARCHAR
);

CREATE TABLE IF NOT EXISTS meta.import_runs (
    import_batch_id VARCHAR NOT NULL,
    contract_name VARCHAR NOT NULL,
    contract_version VARCHAR,
    platform_id VARCHAR,
    platform_run_id VARCHAR,
    source_file VARCHAR NOT NULL,
    source_file_sha256 VARCHAR NOT NULL,
    source_record_count BIGINT NOT NULL,
    imported_record_count BIGINT NOT NULL,
    rejected_record_count BIGINT NOT NULL,
    validation_status VARCHAR NOT NULL,
    import_status VARCHAR NOT NULL,
    started_at_utc TIMESTAMP NOT NULL,
    completed_at_utc TIMESTAMP,
    message VARCHAR
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_import_runs_hash_contract
ON meta.import_runs(source_file_sha256, contract_name);

CREATE TABLE IF NOT EXISTS meta.import_errors (
    import_batch_id VARCHAR NOT NULL,
    contract_name VARCHAR NOT NULL,
    source_file VARCHAR NOT NULL,
    row_number BIGINT,
    error_type VARCHAR,
    error_message VARCHAR NOT NULL,
    created_at_utc TIMESTAMP NOT NULL
);

-- ============================================================
-- Registry
-- ============================================================

CREATE TABLE IF NOT EXISTS registry.machines (
    registry_version VARCHAR NOT NULL,
    machine_id VARCHAR NOT NULL,
    machine_name VARCHAR NOT NULL,
    machine_role VARCHAR NOT NULL,
    operating_system VARCHAR,
    python_version VARCHAR,
    git_available BOOLEAN NOT NULL,
    archive_support VARCHAR,
    availability_status VARCHAR NOT NULL,
    sync_method VARCHAR,
    last_verified_date DATE,
    notes VARCHAR,
    loaded_at_utc TIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_registry_machines
ON registry.machines(machine_id);

CREATE TABLE IF NOT EXISTS registry.platforms (
    registry_version VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    platform_name VARCHAR NOT NULL,
    repository_name VARCHAR NOT NULL,
    local_path VARCHAR,
    machine_id VARCHAR NOT NULL,
    platform_version VARCHAR,
    platform_status VARCHAR NOT NULL,
    integration_stage VARCHAR NOT NULL,
    primary_database VARCHAR,
    main_run_command VARCHAR,
    validation_command VARCHAR,
    dashboard_command VARCHAR,
    exchange_folder VARCHAR NOT NULL,
    published_contracts VARCHAR,
    expected_refresh_frequency VARCHAR NOT NULL,
    freshness_threshold_hours BIGINT,
    last_verified_date DATE,
    last_successful_run_at_utc TIMESTAMP,
    known_issue VARCHAR,
    github_repository VARCHAR,
    is_enabled BOOLEAN NOT NULL,
    notes VARCHAR,
    loaded_at_utc TIMESTAMP NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_registry_platforms
ON registry.platforms(platform_id);

-- ============================================================
-- Universal Data Contracts
-- ============================================================

CREATE TABLE IF NOT EXISTS contracts.platform_status (
    import_batch_id VARCHAR NOT NULL,
    contract_version VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    platform_name VARCHAR NOT NULL,
    platform_version VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    run_started_at_utc TIMESTAMP NOT NULL,
    run_completed_at_utc TIMESTAMP,
    run_status VARCHAR NOT NULL,
    data_as_of_date DATE NOT NULL,
    records_published BIGINT NOT NULL,
    warning_count BIGINT NOT NULL,
    error_count BIGINT NOT NULL,
    source_machine VARCHAR,
    message VARCHAR,
    imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS contracts.asset_master (
    import_batch_id VARCHAR NOT NULL,
    contract_version VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    universal_asset_id VARCHAR NOT NULL,
    platform_asset_id VARCHAR NOT NULL,
    asset_name VARCHAR NOT NULL,
    asset_symbol VARCHAR,
    asset_class VARCHAR NOT NULL,
    asset_subclass VARCHAR,
    currency VARCHAR,
    market_or_region VARCHAR,
    is_active BOOLEAN NOT NULL,
    investable BOOLEAN NOT NULL,
    liquidity_tier VARCHAR,
    data_source VARCHAR,
    first_available_date DATE,
    last_updated_at_utc TIMESTAMP NOT NULL,
    imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS contracts.recommendations (
    import_batch_id VARCHAR NOT NULL,
    contract_version VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    universal_asset_id VARCHAR NOT NULL,
    as_of_date DATE NOT NULL,
    recommendation VARCHAR NOT NULL,
    normalized_score DOUBLE NOT NULL,
    confidence_score DOUBLE NOT NULL,
    platform_native_score DOUBLE,
    platform_native_label VARCHAR,
    time_horizon VARCHAR,
    target_weight DOUBLE,
    minimum_weight DOUBLE,
    maximum_weight DOUBLE,
    rationale_summary VARCHAR,
    primary_risk VARCHAR,
    model_version VARCHAR,
    generated_at_utc TIMESTAMP NOT NULL,
    imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS contracts.forecasts (
    import_batch_id VARCHAR NOT NULL,
    contract_version VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    universal_asset_id VARCHAR NOT NULL,
    forecast_origin_date DATE NOT NULL,
    forecast_horizon_months BIGINT NOT NULL,
    forecast_date DATE NOT NULL,
    current_value DOUBLE,
    forecast_value_base DOUBLE,
    forecast_value_bear DOUBLE,
    forecast_value_bull DOUBLE,
    expected_total_return DOUBLE,
    expected_cagr DOUBLE,
    probability_positive_return DOUBLE,
    forecast_confidence DOUBLE,
    forecast_method VARCHAR NOT NULL,
    scenario_name VARCHAR,
    model_version VARCHAR,
    generated_at_utc TIMESTAMP NOT NULL,
    imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS contracts.risk_metrics (
    import_batch_id VARCHAR NOT NULL,
    contract_version VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    universal_asset_id VARCHAR NOT NULL,
    as_of_date DATE NOT NULL,
    risk_score DOUBLE NOT NULL,
    risk_level VARCHAR NOT NULL,
    annualized_volatility DOUBLE,
    maximum_drawdown DOUBLE,
    downside_deviation DOUBLE,
    value_at_risk_95 DOUBLE,
    liquidity_risk_score DOUBLE,
    concentration_risk_score DOUBLE,
    model_risk_score DOUBLE,
    data_quality_score DOUBLE,
    risk_notes VARCHAR,
    lookback_days BIGINT,
    generated_at_utc TIMESTAMP NOT NULL,
    imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS contracts.portfolio_positions (
    import_batch_id VARCHAR NOT NULL,
    contract_version VARCHAR NOT NULL,
    portfolio_id VARCHAR NOT NULL,
    universal_asset_id VARCHAR NOT NULL,
    as_of_date DATE NOT NULL,
    quantity DOUBLE,
    unit_value DOUBLE,
    position_value DOUBLE NOT NULL,
    cost_basis DOUBLE,
    unrealized_gain_loss DOUBLE,
    current_weight DOUBLE NOT NULL,
    target_weight DOUBLE,
    minimum_weight DOUBLE,
    maximum_weight DOUBLE,
    monthly_allocation_amount DOUBLE,
    source_platform VARCHAR,
    last_updated_at_utc TIMESTAMP NOT NULL,
    imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS contracts.macro_signals (
    import_batch_id VARCHAR NOT NULL,
    contract_version VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    signal_id VARCHAR NOT NULL,
    signal_name VARCHAR NOT NULL,
    as_of_date DATE NOT NULL,
    signal_value DOUBLE NOT NULL,
    normalized_score DOUBLE,
    signal_direction VARCHAR,
    signal_state VARCHAR,
    confidence_score DOUBLE,
    applicable_asset_classes VARCHAR,
    recommended_action VARCHAR,
    description VARCHAR,
    generated_at_utc TIMESTAMP NOT NULL,
    imported_at_utc TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS contracts.export_manifest (
    import_batch_id VARCHAR NOT NULL,
    contract_version VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    export_name VARCHAR NOT NULL,
    file_name VARCHAR NOT NULL,
    file_format VARCHAR NOT NULL,
    schema_name VARCHAR NOT NULL,
    schema_version VARCHAR NOT NULL,
    record_count BIGINT NOT NULL,
    file_size_bytes BIGINT,
    sha256 VARCHAR,
    created_at_utc TIMESTAMP NOT NULL,
    validation_status VARCHAR NOT NULL,
    imported_at_utc TIMESTAMP NOT NULL
);

-- ============================================================
-- Universal analytical views
-- ============================================================

CREATE OR REPLACE VIEW analytics.current_platform_registry AS
SELECT *
FROM registry.platforms;

CREATE OR REPLACE VIEW analytics.current_machine_registry AS
SELECT *
FROM registry.machines;

CREATE OR REPLACE VIEW analytics.latest_asset_master AS
SELECT *
EXCLUDE (row_number_value)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY universal_asset_id
            ORDER BY last_updated_at_utc DESC, imported_at_utc DESC
        ) AS row_number_value
    FROM contracts.asset_master
)
WHERE row_number_value = 1;

CREATE OR REPLACE VIEW analytics.latest_recommendations AS
SELECT *
EXCLUDE (row_number_value)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY universal_asset_id, COALESCE(time_horizon, '')
            ORDER BY as_of_date DESC, generated_at_utc DESC, imported_at_utc DESC
        ) AS row_number_value
    FROM contracts.recommendations
)
WHERE row_number_value = 1;

CREATE OR REPLACE VIEW analytics.latest_forecasts AS
SELECT *
EXCLUDE (row_number_value)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY
                universal_asset_id,
                forecast_horizon_months,
                forecast_method,
                COALESCE(scenario_name, '')
            ORDER BY forecast_origin_date DESC, generated_at_utc DESC
        ) AS row_number_value
    FROM contracts.forecasts
)
WHERE row_number_value = 1;

CREATE OR REPLACE VIEW analytics.latest_risk_metrics AS
SELECT *
EXCLUDE (row_number_value)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY universal_asset_id
            ORDER BY as_of_date DESC, generated_at_utc DESC
        ) AS row_number_value
    FROM contracts.risk_metrics
)
WHERE row_number_value = 1;

CREATE OR REPLACE VIEW analytics.asset_intelligence AS
SELECT
    a.universal_asset_id,
    a.asset_name,
    a.asset_symbol,
    a.asset_class,
    a.asset_subclass,
    a.currency,
    a.platform_id,
    r.recommendation,
    r.normalized_score,
    r.confidence_score,
    r.time_horizon,
    r.target_weight,
    r.rationale_summary,
    r.primary_risk,
    r.as_of_date AS recommendation_date
FROM analytics.latest_asset_master a
LEFT JOIN analytics.latest_recommendations r
    ON a.universal_asset_id = r.universal_asset_id;

CREATE OR REPLACE VIEW analytics.import_history AS
SELECT
    import_batch_id,
    contract_name,
    platform_id,
    platform_run_id,
    source_file,
    source_record_count,
    imported_record_count,
    rejected_record_count,
    validation_status,
    import_status,
    started_at_utc,
    completed_at_utc,
    message
FROM meta.import_runs
ORDER BY started_at_utc DESC;