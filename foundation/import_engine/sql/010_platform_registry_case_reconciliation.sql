-- R3 cross-domain closeout: reconcile recovery-era uppercase MTG registry state
-- with the certified canonical lowercase native MTG authority.
--
-- Historical import/package/status rows remain untouched.  Only the mutable
-- operational platform registry identity is canonicalized, then refreshed from
-- the already-imported current MTG platform-status row and its import ledger.

UPDATE universal_platform_registry
SET platform_id = 'mtg'
WHERE platform_id = 'MTG'
  AND NOT EXISTS (
      SELECT 1
      FROM universal_platform_registry
      WHERE platform_id = 'mtg'
  );

UPDATE universal_platform_registry AS registry
SET
    platform_name = COALESCE(status.platform_name, registry.platform_name),
    platform_version = COALESCE(status.platform_version, registry.platform_version),
    adapter_version = status.adapter_version,
    contract_version = status.contract_version,
    registry_status = CASE
        WHEN imports.import_status = 'IMPORTED' THEN 'ACTIVE'
        WHEN imports.import_status IN ('FAILED', 'REJECTED') THEN 'DEGRADED'
        ELSE registry.registry_status
    END,
    last_package_id = status._package_id,
    last_run_id = status.run_id,
    last_import_id = status._import_id,
    last_import_status = imports.import_status,
    last_imported_at_utc = imports.completed_at_utc,
    last_data_as_of_date = status.data_as_of_date,
    total_successful_imports = registry.total_successful_imports + CASE
        WHEN registry.last_import_id IS DISTINCT FROM status._import_id
             AND imports.import_status = 'IMPORTED'
        THEN 1 ELSE 0
    END,
    total_failed_imports = registry.total_failed_imports + CASE
        WHEN registry.last_import_id IS DISTINCT FROM status._import_id
             AND imports.import_status IN ('FAILED', 'REJECTED')
        THEN 1 ELSE 0
    END,
    total_rows_imported = registry.total_rows_imported + CASE
        WHEN registry.last_import_id IS DISTINCT FROM status._import_id
             AND imports.import_status = 'IMPORTED'
        THEN COALESCE(imports.imported_row_count, 0) ELSE 0
    END,
    warning_count = registry.warning_count + CASE
        WHEN registry.last_import_id IS DISTINCT FROM status._import_id
        THEN COALESCE(imports.warning_count, 0) ELSE 0
    END,
    error_count = registry.error_count + CASE
        WHEN registry.last_import_id IS DISTINCT FROM status._import_id
        THEN COALESCE(imports.error_count, 0) ELSE 0
    END,
    status_message = status.status_message,
    updated_at_utc = COALESCE(imports.completed_at_utc, registry.updated_at_utc)
FROM platform_status_current AS status
JOIN universal_imports AS imports
  ON imports.import_id = status._import_id
WHERE registry.platform_id = 'mtg'
  AND lower(status.platform_id) = 'mtg';

-- Current import selectors are operational surfaces, so platform identity must
-- be case-insensitive even when preserved historical imports used legacy case.
CREATE OR REPLACE VIEW universal_latest_successful_import AS
SELECT * EXCLUDE (_row_rank)
FROM (
    SELECT *,
        ROW_NUMBER() OVER (
            PARTITION BY lower(platform_id)
            ORDER BY completed_at_utc DESC NULLS LAST,
                     started_at_utc DESC NULLS LAST,
                     discovered_at_utc DESC NULLS LAST,
                     import_id DESC
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
            PARTITION BY lower(platform_id)
            ORDER BY started_at_utc DESC NULLS LAST,
                     discovered_at_utc DESC NULLS LAST,
                     import_id DESC
        ) AS _row_rank
    FROM universal_imports
)
WHERE _row_rank = 1;

-- Domain operational health must bind canonical domain IDs to platform
-- registry state without treating historical casing as a different domain.
CREATE OR REPLACE VIEW universal_domain_operational_status AS
SELECT
    d.domain_id,
    d.domain_name,
    d.platform_id,
    d.ownership_type,
    d.source_repository,
    d.publication_boundary,
    d.certification_state,
    d.dynamic_asset_universe,
    d.native_semantics_authoritative,
    d.cross_asset_ranking_authorized,
    d.automatic_execution_authorized,
    d.registry_version,
    p.platform_name,
    p.platform_version,
    p.adapter_version,
    p.contract_version,
    p.registry_status AS import_registry_status,
    p.last_package_id,
    p.last_run_id,
    p.last_import_id,
    p.last_import_status,
    p.last_imported_at_utc,
    p.last_data_as_of_date,
    p.warning_count,
    p.error_count,
    p.status_message
FROM universal_domain_registry AS d
LEFT JOIN universal_platform_registry AS p
    ON lower(p.platform_id) = lower(d.platform_id);

-- Preserve legacy lineage rows while associating both MTG and mtg with the
-- same canonical domain registry record.
CREATE OR REPLACE VIEW universal_lineage_with_domain AS
SELECT
    d.domain_id,
    d.domain_name,
    d.ownership_type,
    d.native_semantics_authoritative,
    l.dataset_name,
    l.platform_id,
    l.universal_asset_id,
    l.run_id,
    l._import_id,
    l._package_id,
    l._source_platform,
    l._source_filename,
    l._source_row_number,
    l._manifest_sha256,
    l._imported_at_utc
FROM universal_row_lineage AS l
LEFT JOIN universal_domain_registry AS d
    ON lower(d.platform_id) = lower(l.platform_id);
