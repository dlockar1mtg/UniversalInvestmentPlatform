# Metals Universal Export Adapter 1.2.2

## Release Status

Stable and certified

## Summary

This release establishes the Metals Investment Intelligence Platform as the
first successfully integrated platform in the Universal Investment
Intelligence Platform.

## Initial Release Features

- Native Metals output discovery
- Read-only DuckDB access
- Universal contract loading
- Universal dataset transformation
- Strict required-field validation
- Timestamped export package creation
- Latest-package publication
- Export manifest generation
- File checksum generation

## Phase 1.2.1 Corrections

- Added support for `_columns.csv` contract filenames
- Added Universal canonical field aliases
- Added run-level metadata alignment

## Phase 1.2.2 Corrections

- Moved canonical field construction into source-row mapping
- Corrected asset identifier population
- Corrected forecast horizon population
- Corrected recommendation score population
- Corrected confidence score population
- Corrected risk score population
- Corrected portfolio position value population

## Certification

The adapter completed strict Universal contract validation with a PASS result.

## Compatibility

Certified against:

- Metals platform v8.1
- Universal contracts v1
- Python 3.14
- Windows 11
- DuckDB-based Metals repository