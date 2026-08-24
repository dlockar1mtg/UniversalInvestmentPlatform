-- First-class UIP authority for retained Metals-native tactical research evidence.
-- This migration defines history/current surfaces only. It does not itself
-- populate production data or authorize any tactical action or execution.

CREATE TABLE IF NOT EXISTS metals_forecast_model_component_history (
    universal_asset_id VARCHAR NOT NULL,
    forecast_run_id VARCHAR NOT NULL,
    metal VARCHAR NOT NULL,
    horizon_months BIGINT NOT NULL,
    model_name VARCHAR NOT NULL,
    model_forecast DOUBLE NOT NULL,
    model_weight DOUBLE NOT NULL,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _promoted_at_utc TIMESTAMP NOT NULL
);

CREATE OR REPLACE VIEW metals_forecast_model_component_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY universal_asset_id, horizon_months, model_name
        ORDER BY _promoted_at_utc DESC, _source_row_number DESC
    ) AS _row_rank
    FROM metals_forecast_model_component_history
)
WHERE _row_rank = 1;

CREATE TABLE IF NOT EXISTS metals_regime_probability_history (
    universal_asset_id VARCHAR NOT NULL,
    forecast_run_id VARCHAR NOT NULL,
    metal VARCHAR NOT NULL,
    regime VARCHAR NOT NULL,
    probability DOUBLE NOT NULL,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _promoted_at_utc TIMESTAMP NOT NULL
);

CREATE OR REPLACE VIEW metals_regime_probability_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY universal_asset_id, regime
        ORDER BY _promoted_at_utc DESC, _source_row_number DESC
    ) AS _row_rank
    FROM metals_regime_probability_history
)
WHERE _row_rank = 1;

CREATE TABLE IF NOT EXISTS metals_uncertainty_adjusted_view_history (
    universal_vehicle_id VARCHAR NOT NULL,
    universal_metal_id VARCHAR NOT NULL,
    forecast_run_id VARCHAR NOT NULL,
    ticker VARCHAR NOT NULL,
    metal VARCHAR NOT NULL,
    horizon_months BIGINT NOT NULL,
    raw_expected_return DOUBLE NOT NULL,
    uncertainty_penalty DOUBLE NOT NULL,
    downside_penalty DOUBLE NOT NULL,
    adjusted_expected_return DOUBLE NOT NULL,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _promoted_at_utc TIMESTAMP NOT NULL
);

CREATE OR REPLACE VIEW metals_uncertainty_adjusted_view_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY universal_vehicle_id, horizon_months
        ORDER BY _promoted_at_utc DESC, _source_row_number DESC
    ) AS _row_rank
    FROM metals_uncertainty_adjusted_view_history
)
WHERE _row_rank = 1;

CREATE TABLE IF NOT EXISTS metals_recommendation_change_history (
    universal_vehicle_id VARCHAR NOT NULL,
    decision_run_id VARCHAR NOT NULL,
    ticker VARCHAR NOT NULL,
    previous_action VARCHAR,
    current_action VARCHAR,
    previous_weight_pct DOUBLE,
    current_weight_pct DOUBLE,
    weight_change_pct DOUBLE,
    previous_confidence DOUBLE,
    current_confidence DOUBLE,
    confidence_change DOUBLE,
    explanation VARCHAR,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _promoted_at_utc TIMESTAMP NOT NULL
);

CREATE OR REPLACE VIEW metals_recommendation_change_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY universal_vehicle_id
        ORDER BY _promoted_at_utc DESC, _source_row_number DESC
    ) AS _row_rank
    FROM metals_recommendation_change_history
)
WHERE _row_rank = 1;

CREATE TABLE IF NOT EXISTS metals_data_freshness_history (
    decision_run_id VARCHAR NOT NULL,
    series_key VARCHAR NOT NULL,
    frequency VARCHAR,
    last_observation VARCHAR,
    age_days DOUBLE,
    freshness_status VARCHAR,
    health_score DOUBLE,
    message VARCHAR,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _promoted_at_utc TIMESTAMP NOT NULL
);

CREATE OR REPLACE VIEW metals_data_freshness_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY series_key
        ORDER BY _promoted_at_utc DESC, _source_row_number DESC
    ) AS _row_rank
    FROM metals_data_freshness_history
)
WHERE _row_rank = 1;

CREATE TABLE IF NOT EXISTS metals_platform_health_history (
    decision_run_id VARCHAR NOT NULL,
    data_freshness_score DOUBLE,
    model_confidence_score DOUBLE,
    recommendation_quality_score DOUBLE,
    pipeline_completeness_score DOUBLE,
    overall_platform_health DOUBLE,
    platform_grade VARCHAR,
    explanation VARCHAR,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _promoted_at_utc TIMESTAMP NOT NULL
);

CREATE OR REPLACE VIEW metals_platform_health_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *, ROW_NUMBER() OVER (
        PARTITION BY decision_run_id
        ORDER BY _promoted_at_utc DESC, _source_row_number DESC
    ) AS _row_rank
    FROM metals_platform_health_history
)
WHERE _row_rank = 1;
