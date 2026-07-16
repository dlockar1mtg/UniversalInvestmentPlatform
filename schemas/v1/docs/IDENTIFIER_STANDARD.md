# Universal Identifier Standard

## Purpose

Universal identifiers allow the same asset to be recognized across multiple
platforms and over time.

## Format

Identifiers use lowercase colon-separated components.

General format:

`asset_class:asset_identifier`

Examples:

- `crypto:bitcoin`
- `crypto:ethereum`
- `etf:voo`
- `etf:schd`
- `metal:gold`
- `commodity:copper`
- `collectible:mtg:final-fantasy-collector-booster-display`
- `real_estate:metro:wichita-ks`
- `macro:recession_stress`

## Rules

Identifiers must:

- Be lowercase
- Use hyphens inside components
- Use colons between hierarchy levels
- Avoid spaces
- Avoid display names
- Avoid price or date information
- Remain stable when asset names change
- Be unique across the Universal Platform

## Platform Identifiers

Platforms may retain their native identifiers separately.

Examples:

| Platform | Native Identifier | Universal Identifier |
|---|---|---|
| Crypto | bitcoin | crypto:bitcoin |
| Crypto | xrp | crypto:xrp |
| Metals | GLD | etf:gld |
| MTG | product-12345 | collectible:mtg:product-12345 |
| Housing | Wichita, KS | real_estate:metro:wichita-ks |

## Identifier Mapping

Mappings will eventually be stored in:

`data/reference/asset_identifier_map.csv`

The mapping table will include:

- platform_id
- platform_asset_id
- universal_asset_id
- effective_start_date
- effective_end_date
- mapping_status