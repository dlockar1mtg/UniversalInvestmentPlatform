-- Make forecasts_current deterministic when multiple history rows share the same
-- semantic forecast identity and the same primary recency timestamps.
--
-- R3 MTG production cutover forensic evidence found five Crypto forecast-current
-- rows whose semantic contents were identical before/after a view rebuild and whose
-- only difference was _source_row_number. Underlying forecasts_history was unchanged.
-- The prior current view ordered only by _imported_at_utc DESC, generated_at_utc DESC,
-- leaving exact ties implementation-dependent.
--
-- This migration preserves the existing Metals vehicle identity reconciliation and
-- MTG native-authority suppression rule, while adding stable lineage tie-breakers.

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
            ORDER BY
                _imported_at_utc DESC,
                generated_at_utc DESC,
                _import_id DESC,
                _package_id DESC,
                _source_filename ASC,
                _source_row_number ASC,
                _manifest_sha256 DESC NULLS LAST
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
