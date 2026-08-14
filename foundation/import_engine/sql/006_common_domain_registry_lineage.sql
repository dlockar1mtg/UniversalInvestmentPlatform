CREATE TABLE IF NOT EXISTS universal_domain_registry (
    domain_id VARCHAR PRIMARY KEY,
    domain_name VARCHAR NOT NULL,
    platform_id VARCHAR NOT NULL,
    ownership_type VARCHAR NOT NULL,
    source_repository VARCHAR,
    publication_boundary VARCHAR NOT NULL,
    certification_state VARCHAR NOT NULL,
    dynamic_asset_universe BOOLEAN NOT NULL,
    native_semantics_authoritative BOOLEAN NOT NULL,
    cross_asset_ranking_authorized BOOLEAN NOT NULL,
    automatic_execution_authorized BOOLEAN NOT NULL,
    registry_version VARCHAR NOT NULL,
    notes VARCHAR
);

INSERT INTO universal_domain_registry (
    domain_id,
    domain_name,
    platform_id,
    ownership_type,
    source_repository,
    publication_boundary,
    certification_state,
    dynamic_asset_universe,
    native_semantics_authoritative,
    cross_asset_ranking_authorized,
    automatic_execution_authorized,
    registry_version,
    notes
) VALUES
    (
        'mtg',
        'Magic: The Gathering',
        'mtg',
        'external_source_repository',
        'dlockar1mtg/mtg-investment-terminal',
        'certified_external_package',
        'CERTIFIED',
        TRUE,
        TRUE,
        FALSE,
        FALSE,
        '1.0.0',
        'MTG native lane, rank, purchase, and authority semantics remain source-owned.'
    ),
    (
        'metals',
        'Metals',
        'metals',
        'uip_native_domain',
        NULL,
        'certified_internal_domain_package',
        'CERTIFIED',
        TRUE,
        TRUE,
        FALSE,
        FALSE,
        '1.0.0',
        'Metals remains UIP-native and promotes only through its certified publication boundary.'
    ),
    (
        'crypto',
        'Crypto',
        'crypto',
        'external_source_repository',
        'dlockar1mtg/CryptoIntelligencePlatform',
        'certified_external_package',
        'CERTIFIED',
        TRUE,
        TRUE,
        FALSE,
        FALSE,
        '1.0.0',
        'Crypto models and native recommendation semantics remain source-owned.'
    )
ON CONFLICT (domain_id) DO UPDATE SET
    domain_name = excluded.domain_name,
    platform_id = excluded.platform_id,
    ownership_type = excluded.ownership_type,
    source_repository = excluded.source_repository,
    publication_boundary = excluded.publication_boundary,
    certification_state = excluded.certification_state,
    dynamic_asset_universe = excluded.dynamic_asset_universe,
    native_semantics_authoritative = excluded.native_semantics_authoritative,
    cross_asset_ranking_authorized = excluded.cross_asset_ranking_authorized,
    automatic_execution_authorized = excluded.automatic_execution_authorized,
    registry_version = excluded.registry_version,
    notes = excluded.notes;

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
FROM universal_domain_registry d
LEFT JOIN universal_platform_registry p
    ON p.platform_id = d.platform_id;

CREATE OR REPLACE VIEW universal_row_lineage AS
SELECT
    'asset_master' AS dataset_name,
    platform_id,
    universal_asset_id,
    run_id,
    _import_id,
    _package_id,
    _source_platform,
    _source_filename,
    _source_row_number,
    _manifest_sha256,
    _imported_at_utc
FROM asset_master_history

UNION ALL

SELECT
    'forecasts' AS dataset_name,
    platform_id,
    universal_asset_id,
    run_id,
    _import_id,
    _package_id,
    _source_platform,
    _source_filename,
    _source_row_number,
    _manifest_sha256,
    _imported_at_utc
FROM forecasts_history

UNION ALL

SELECT
    'recommendations' AS dataset_name,
    platform_id,
    universal_asset_id,
    run_id,
    _import_id,
    _package_id,
    _source_platform,
    _source_filename,
    _source_row_number,
    _manifest_sha256,
    _imported_at_utc
FROM recommendations_history

UNION ALL

SELECT
    'risk_metrics' AS dataset_name,
    platform_id,
    universal_asset_id,
    run_id,
    _import_id,
    _package_id,
    _source_platform,
    _source_filename,
    _source_row_number,
    _manifest_sha256,
    _imported_at_utc
FROM risk_metrics_history

UNION ALL

SELECT
    'portfolio_positions' AS dataset_name,
    platform_id,
    universal_asset_id,
    run_id,
    _import_id,
    _package_id,
    _source_platform,
    _source_filename,
    _source_row_number,
    _manifest_sha256,
    _imported_at_utc
FROM portfolio_positions_history

UNION ALL

SELECT
    'platform_status' AS dataset_name,
    platform_id,
    CAST(NULL AS VARCHAR) AS universal_asset_id,
    run_id,
    _import_id,
    _package_id,
    _source_platform,
    _source_filename,
    _source_row_number,
    _manifest_sha256,
    _imported_at_utc
FROM platform_status_history

UNION ALL

SELECT
    'historical_performance' AS dataset_name,
    platform_id,
    universal_asset_id,
    run_id,
    _import_id,
    _package_id,
    _source_platform,
    _source_filename,
    _source_row_number,
    _manifest_sha256,
    _imported_at_utc
FROM historical_performance_history

UNION ALL

SELECT
    'mtg_native_authority' AS dataset_name,
    'mtg' AS platform_id,
    mtg_asset_id AS universal_asset_id,
    CAST(NULL AS VARCHAR) AS run_id,
    _import_id,
    _package_id,
    _source_platform,
    _source_filename,
    _source_row_number,
    _manifest_sha256,
    _imported_at_utc
FROM mtg_native_authority_history;

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
FROM universal_row_lineage l
LEFT JOIN universal_domain_registry d
    ON d.platform_id = l.platform_id;
