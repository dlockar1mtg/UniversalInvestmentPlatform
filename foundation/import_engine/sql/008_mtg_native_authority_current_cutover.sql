-- Govern the MTG current-state authority cutover without rewriting history.
--
-- Recovery-era MTG imports used generic universal surfaces under platform_id = 'MTG'.
-- UIP-MTG-A2 later certified a lossless native MTG authority in
-- mtg_native_authority_history/current and explicitly prohibited creation of generic
-- MTG forecast, recommendation, or risk authority from that native interface.
--
-- This migration preserves every historical generic MTG row and all package/import
-- lineage. Before any native MTG authority has been imported, the legacy generic MTG
-- rows remain visible in current views. Once at least one certified native MTG row
-- exists transactionally, generic MTG analytical current rows are suppressed so they
-- cannot compete with the native authority. If the native import rolls back, the
-- condition remains false and legacy current visibility is preserved.
--
-- platform_status_current is handled differently: native MTG integration legitimately
-- publishes a lower-case `mtg` status row. MTG platform status therefore uses a
-- case-insensitive partition key so the latest native status supersedes legacy `MTG`
-- status without deleting status history.

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
    WHERE NOT (
        lower(platform_id) = 'mtg'
        AND EXISTS (
            SELECT 1
            FROM mtg_native_authority_history
            LIMIT 1
        )
    )
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
    WHERE NOT (
        lower(platform_id) = 'mtg'
        AND EXISTS (
            SELECT 1
            FROM mtg_native_authority_history
            LIMIT 1
        )
    )
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
    WHERE NOT (
        lower(platform_id) = 'mtg'
        AND EXISTS (
            SELECT 1
            FROM mtg_native_authority_history
            LIMIT 1
        )
    )
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
    WHERE NOT (
        lower(platform_id) = 'mtg'
        AND EXISTS (
            SELECT 1
            FROM mtg_native_authority_history
            LIMIT 1
        )
    )
)
WHERE _row_rank = 1;

CREATE OR REPLACE VIEW platform_status_current AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY
                CASE
                    WHEN lower(platform_id) = 'mtg'
                    THEN 'mtg'
                    ELSE platform_id
                END
            ORDER BY _imported_at_utc DESC, generated_at_utc DESC
        ) AS _row_rank
    FROM platform_status_history
)
WHERE _row_rank = 1;
