# Universal Data Contracts v1

## Purpose

The Universal Data Contracts define the standardized exports produced by each
investment intelligence platform.

Each platform may use any internal database, scoring model, or forecasting
methodology. Integration occurs only through these contracts.

## Contract Version

Current contract version:

`1.0.0`

## Required Export Set

Each registered platform should eventually publish:

1. `platform_status`
2. `asset_master`
3. `recommendations`
4. `forecasts`
5. `risk_metrics`
6. `export_manifest`

Optional contracts include:

7. `portfolio_positions`
8. `macro_signals`

## Supported File Formats

Initial supported formats:

- CSV
- Parquet
- JSON

CSV is used for human inspection and early migration.

Parquet is the preferred long-term tabular exchange format.

JSON is used for manifests, platform status, and validation definitions.

## General Rules

All contracts must:

- Include a contract version
- Identify the source platform
- Use UTC timestamps
- Use stable asset identifiers
- Include the originating platform run identifier
- Avoid platform-specific column names where a universal name exists
- Represent missing values as null or blank, not text such as `N/A`
- Use ISO 8601 dates and timestamps
- Use decimal values rather than formatted percentage strings
- Use lowercase snake_case column names

## Percentage Rules

Percentages are stored as decimals.

Examples:

- 10% is stored as `0.10`
- 5.5% is stored as `0.055`
- -12% is stored as `-0.12`

## Score Rules

Universal normalized scores use a range of:

`0.0` to `100.0`

Platform-native scores may also be included when necessary.

## Recommendation Vocabulary

Preferred standardized recommendation values:

- `strong_buy`
- `buy`
- `accumulate`
- `hold`
- `reduce`
- `sell`
- `strong_sell`
- `watch`
- `not_ready`
- `insufficient_data`

## Asset Classes

Initial supported values:

- `crypto`
- `equity`
- `etf`
- `metal`
- `commodity`
- `collectible`
- `real_estate`
- `cash`
- `bond`
- `macro_signal`
- `personal_finance`

## Identifier Rules

Every asset must have:

- `platform_asset_id`
- `universal_asset_id`
- `asset_name`
- `asset_class`

The universal identifier must remain stable across exports.

Examples:

- `crypto:bitcoin`
- `etf:voo`
- `metal:gold`
- `collectible:mtg:lotr-collector-booster-display`
- `real_estate:metro:wichita-ks`

## Contract Compatibility

Patch releases may clarify validation without changing required fields.

Minor releases may add optional fields.

Major releases may add, remove, or redefine required fields.

Platforms must declare the exact contract version used in every export.