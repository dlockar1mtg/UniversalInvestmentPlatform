CREATE TABLE IF NOT EXISTS historical_performance_history (
    contract_version VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    run_id VARCHAR NOT NULL,
    universal_asset_id VARCHAR NOT NULL,
    performance_status VARCHAR NOT NULL,
    performance_eligible BOOLEAN NOT NULL,
    historical_start_date DATE,
    historical_end_date DATE,
    historical_start_value DOUBLE,
    historical_end_value DOUBLE,
    elapsed_days BIGINT,
    observation_count BIGINT,
    distinct_date_count BIGINT,
    source_count BIGINT,
    historical_sources VARCHAR,
    total_return_pct DOUBLE,
    cagr_pct DOUBLE,
    annualized_return_pct DOUBLE,
    minimum_value DOUBLE,
    maximum_value DOUBLE,
    data_quality VARCHAR NOT NULL,
    suppression_reason VARCHAR,
    currency VARCHAR NOT NULL,
    source_system VARCHAR NOT NULL,
    model_version VARCHAR,
    generated_at_utc TIMESTAMP NOT NULL,
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

CREATE OR REPLACE VIEW historical_performance_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY
                platform_id,
                universal_asset_id
            ORDER BY
                _imported_at_utc DESC,
                historical_end_date DESC NULLS LAST,
                generated_at_utc DESC
        ) AS _row_rank
    FROM historical_performance_history
)
WHERE _row_rank = 1;
