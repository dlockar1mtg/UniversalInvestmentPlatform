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
        WHEN r.registry_status = 'ACTIVE'
             AND r.last_import_status = 'IMPORTED'
        THEN 'HEALTHY'
        WHEN r.last_import_status IN ('FAILED', 'REJECTED')
        THEN 'DEGRADED'
        WHEN r.last_import_status IS NULL
        THEN 'NOT_IMPORTED'
        ELSE 'WARNING'
    END AS health_status
FROM universal_platform_registry r;
