-- UIP Metals V3 tactical-state persistence.
-- Append-only history plus deterministic current-state view.
-- This migration does not alter recommendations, forecasts, risk metrics, or allocation tables.

CREATE TABLE IF NOT EXISTS metals_tactical_state_history (
    universal_asset_id VARCHAR NOT NULL,
    ticker VARCHAR NOT NULL,
    as_of_date DATE NOT NULL,
    candidate_regime VARCHAR NOT NULL,
    tactical_state VARCHAR NOT NULL,
    classifier_rule_version VARCHAR NOT NULL,
    action_mapping_version VARCHAR NOT NULL,
    price_semantics VARCHAR NOT NULL,
    source_package_id VARCHAR NOT NULL,
    state_available BOOLEAN NOT NULL,
    state_reason VARCHAR NOT NULL,
    is_reference_control BOOLEAN NOT NULL,
    return_1m_pct DOUBLE,
    return_3m_pct DOUBLE,
    return_6m_pct DOUBLE,
    distance_ma50_pct DOUBLE,
    distance_ma200_pct DOUBLE,
    current_drawdown_pct DOUBLE,
    realized_volatility_3m_pct DOUBLE,
    trend_slope DOUBLE,
    return_dispersion DOUBLE,
    volatility_change DOUBLE,
    drawdown_recovery_rate DOUBLE,
    distance_from_recent_extreme DOUBLE,
    short_vs_long_momentum_spread DOUBLE,
    source_state_sha256 VARCHAR NOT NULL,
    source_materialization_manifest_sha256 VARCHAR NOT NULL,
    source_row_json VARCHAR NOT NULL,
    _import_id VARCHAR NOT NULL,
    _package_id VARCHAR NOT NULL,
    _source_platform VARCHAR NOT NULL,
    _source_filename VARCHAR NOT NULL,
    _source_row_number BIGINT NOT NULL,
    _manifest_sha256 VARCHAR NOT NULL,
    _imported_at_utc TIMESTAMP NOT NULL
);

CREATE OR REPLACE VIEW metals_tactical_state_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY lower(universal_asset_id)
            ORDER BY as_of_date DESC, _imported_at_utc DESC, _source_row_number DESC
        ) AS _row_rank
    FROM metals_tactical_state_history
)
WHERE _row_rank = 1;
