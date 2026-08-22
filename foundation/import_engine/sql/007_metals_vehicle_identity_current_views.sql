-- Reconcile the legacy Metals vehicle universal_asset_id case transition in current-state views.
--
-- Metals adapter 2.0.0 standardized vehicle IDs from legacy lowercase values such as
-- `metals:vehicle:gld` to canonical values such as `metals:vehicle:GLD`. Historical rows
-- remain immutable. Current-state selection treats those case-only Metals vehicle IDs as
-- one identity so superseded legacy rows do not survive beside the canonical row.

CREATE OR REPLACE VIEW asset_master_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY
                CASE
                    WHEN platform_id = 'metals'
                     AND lower(universal_asset_id) LIKE 'metals:vehicle:%'
                    THEN lower(universal_asset_id)
                    ELSE universal_asset_id
                END
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
            PARTITION BY
                CASE
                    WHEN platform_id = 'metals'
                     AND lower(universal_asset_id) LIKE 'metals:vehicle:%'
                    THEN lower(universal_asset_id)
                    ELSE universal_asset_id
                END,
                forecast_horizon_months,
                forecast_method
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
            PARTITION BY
                CASE
                    WHEN platform_id = 'metals'
                     AND lower(universal_asset_id) LIKE 'metals:vehicle:%'
                    THEN lower(universal_asset_id)
                    ELSE universal_asset_id
                END
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
            PARTITION BY
                CASE
                    WHEN platform_id = 'metals'
                     AND lower(universal_asset_id) LIKE 'metals:vehicle:%'
                    THEN lower(universal_asset_id)
                    ELSE universal_asset_id
                END
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
            PARTITION BY
                platform_id,
                account_id,
                CASE
                    WHEN platform_id = 'metals'
                     AND lower(universal_asset_id) LIKE 'metals:vehicle:%'
                    THEN lower(universal_asset_id)
                    ELSE universal_asset_id
                END
            ORDER BY _imported_at_utc DESC, last_updated_at_utc DESC
        ) AS _row_rank
    FROM portfolio_positions_history
)
WHERE _row_rank = 1;

CREATE OR REPLACE VIEW historical_performance_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY
                platform_id,
                CASE
                    WHEN platform_id = 'metals'
                     AND lower(universal_asset_id) LIKE 'metals:vehicle:%'
                    THEN lower(universal_asset_id)
                    ELSE universal_asset_id
                END
            ORDER BY
                _imported_at_utc DESC,
                historical_end_date DESC NULLS LAST,
                generated_at_utc DESC
        ) AS _row_rank
    FROM historical_performance_history
)
WHERE _row_rank = 1;
