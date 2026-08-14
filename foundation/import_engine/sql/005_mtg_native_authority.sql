CREATE TABLE IF NOT EXISTS mtg_native_authority_history (
    mtg_asset_id VARCHAR NOT NULL,
    mtg_lane VARCHAR NOT NULL,
    native_asset_id VARCHAR NOT NULL,
    product_name VARCHAR NOT NULL,
    lane_authority_state VARCHAR NOT NULL,
    current_price_usd DOUBLE,
    current_price_authority_available BOOLEAN NOT NULL,
    forecast_authority_available BOOLEAN NOT NULL,
    forecast_1y_price_usd DOUBLE,
    forecast_1y_return DOUBLE,
    risk_authority_available BOOLEAN NOT NULL,
    native_rank BIGINT,
    native_rank_type VARCHAR,
    native_purchase_status VARCHAR,
    purchase_semantic VARCHAR,
    evidence_state VARCHAR NOT NULL,
    actionability_state VARCHAR NOT NULL,
    execution_ready_purchase_certified BOOLEAN NOT NULL,
    manual_execution_price_check_required BOOLEAN NOT NULL,
    native_authority_pointer VARCHAR NOT NULL,
    native_authority_sha256 VARCHAR NOT NULL,
    snapshot_population_is_permanent BOOLEAN NOT NULL,
    automatic_purchase_execution BOOLEAN NOT NULL,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_platform VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR,
    _imported_at_utc TIMESTAMP NOT NULL
);

CREATE OR REPLACE VIEW mtg_native_authority_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY mtg_asset_id
            ORDER BY
                _imported_at_utc DESC,
                _source_row_number DESC
        ) AS _row_rank
    FROM mtg_native_authority_history
)
WHERE _row_rank = 1;