CREATE TABLE IF NOT EXISTS universal_platform_registry (
    platform_id VARCHAR PRIMARY KEY,
    platform_name VARCHAR,
    platform_version VARCHAR,
    adapter_version VARCHAR,
    contract_version VARCHAR,
    registry_status VARCHAR NOT NULL,
    last_package_id VARCHAR,
    last_run_id VARCHAR,
    last_import_id VARCHAR,
    last_import_status VARCHAR,
    last_imported_at_utc TIMESTAMP,
    last_data_as_of_date DATE,
    total_successful_imports BIGINT DEFAULT 0,
    total_failed_imports BIGINT DEFAULT 0,
    total_rows_imported BIGINT DEFAULT 0,
    warning_count BIGINT DEFAULT 0,
    error_count BIGINT DEFAULT 0,
    status_message VARCHAR,
    created_at_utc TIMESTAMP NOT NULL,
    updated_at_utc TIMESTAMP NOT NULL
);

CREATE OR REPLACE VIEW universal_latest_successful_import AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY platform_id
            ORDER BY completed_at_utc DESC NULLS LAST,
                     started_at_utc DESC NULLS LAST
        ) AS _row_rank
    FROM universal_imports
    WHERE import_status = 'IMPORTED'
)
WHERE _row_rank = 1;

CREATE OR REPLACE VIEW universal_latest_import_attempt AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY platform_id
            ORDER BY started_at_utc DESC NULLS LAST,
                     discovered_at_utc DESC NULLS LAST
        ) AS _row_rank
    FROM universal_imports
)
WHERE _row_rank = 1;

CREATE OR REPLACE VIEW universal_import_health AS
SELECT
    r.platform_id,
    r.platform_name,
    r.platform_version,
    r.adapter_version,
    r.contract_version,
    r.registry_status,
    r.last_package_id,
    r.last_run_id,
    r.last_import_id,
    r.last_import_status,
    r.last_imported_at_utc,
    r.last_data_as_of_date,
    r.total_successful_imports,
    r.total_failed_imports,
    r.total_rows_imported,
    r.warning_count,
    r.error_count,
    r.status_message,
    CASE
        WHEN r.last_import_status = 'IMPORTED' AND r.error_count = 0 THEN 'HEALTHY'
        WHEN r.last_import_status IN ('FAILED', 'REJECTED') THEN 'DEGRADED'
        WHEN r.last_import_status IS NULL THEN 'NOT_IMPORTED'
        ELSE 'WARNING'
    END AS health_status
FROM universal_platform_registry r;

CREATE OR REPLACE VIEW universal_import_error_summary AS
SELECT
    import_id,
    severity,
    error_code,
    COUNT(*) AS occurrence_count,
    MIN(created_at_utc) AS first_seen_at_utc,
    MAX(created_at_utc) AS last_seen_at_utc
FROM universal_import_errors
GROUP BY import_id, severity, error_code;
