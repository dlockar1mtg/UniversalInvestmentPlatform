# Universal Integration Package Standard

## Purpose

A Universal Integration Package is the stable exchange format between a
standalone investment platform and the Universal Investment Intelligence
Platform.

Native platforms publish packages.

The Universal Import Engine validates and imports packages.

Native platforms must not write directly to the Universal database.

## Required Package Structure

A package must contain:

- export_manifest.csv
- platform_status.csv

A package may contain:

- asset_master.csv
- forecasts.csv
- recommendations.csv
- risk_metrics.csv
- portfolio_positions.csv
- macro_signals.csv
- native audit files
- package metadata files

## Package Identity

Every package must be uniquely identifiable using:

- platform_id
- package_id
- run_id
- adapter_version
- contract_version
- generated_at_utc

## Required Manifest Information

The export manifest must provide, where supported:

- package_id
- platform_id
- run_id
- adapter_version
- contract_version
- dataset_name
- filename
- row_count
- file_size_bytes
- sha256
- generated_at_utc
- required
- validation_status

## Package States

A package may be:

- DISCOVERED
- VALIDATING
- VALID
- INVALID
- IMPORTING
- IMPORTED
- FAILED
- REJECTED
- SUPERSEDED

## Validation Order

1. Package path exists
2. Export manifest exists
3. Manifest can be parsed
4. Package identity is complete
5. Required files exist
6. File checksums match
7. Row counts match
8. Dataset columns match Universal contracts
9. Required fields are populated
10. Platform is registered
11. Contract version is supported
12. Adapter version is supported
13. Package has not already been imported

## Import Guarantees

An import must be atomic.

Either all approved datasets are committed or none are committed.

A failure must not leave partial production data.

## Duplicate Policy

A standard import must reject:

- an already imported package_id
- an already imported manifest checksum
- a conflicting platform_id and run_id combination

A forced reimport must be explicitly requested and fully audited.

## Lineage

Every imported row must be traceable to:

- import_id
- package_id
- platform_id
- source filename
- source row number
- imported_at_utc
- manifest checksum

## Database Ownership

Only the Universal Investment Intelligence Platform may write to the Universal
DuckDB database.

Native platforms have no write access to the Universal database.