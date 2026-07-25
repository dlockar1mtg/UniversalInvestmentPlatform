# Phase 8.9.4 — Metals Vehicle Metadata Completeness

## Objective

Create a canonical, dated, fail-closed vehicle metadata layer for all Metals investment vehicles. The layer separates durable structural facts from time-sensitive market observations and prevents incomplete or stale vehicles from qualifying for deterministic selection.

## Design

### Structural metadata

`config/metals/vehicle_structural_metadata.json` contains fields that normally change infrequently:

- issuer
- legal structure
- exposure type
- exposure share
- concentration description
- tax structure
- investability classification
- official metadata source URL

The structural file must cover every ticker in `config/metals/vehicles.json` exactly once. Missing or extra tickers fail closed.

### Market metadata

`config/metals/vehicle_market_metadata.csv` contains dated observations:

- expense ratio
- assets under management
- average daily share volume
- median bid-ask spread
- metadata as-of date
- source name
- source URL

The committed CSV is a controlled collection template. Values must be populated from dated official issuer or approved market-data sources before strict certification.

### Investability classifications

Allowed values are:

- `directly_investable`
- `diversified_fund_only`
- `futures_only`
- `research_only`
- `no_approved_vehicle`

Only complete, current or aging records in the first three categories are eligible for vehicle selection.

## Freshness policy

- `CURRENT`: 0–45 days old
- `AGING`: 46–90 days old
- `STALE`: more than 90 days old
- `MISSING`: no dated observation

Future-dated observations are rejected.

## Outputs

Run:

```powershell
python scripts\publish_metals_vehicle_metadata.py
```

Outputs are written to:

```text
data\operations\metals\vehicle_metadata\vehicle_metadata.json
data\operations\metals\vehicle_metadata\vehicle_metadata.csv
data\operations\metals\vehicle_metadata\vehicle_metadata_summary.json
```

Runtime outputs are ignored by Git.

## Strict certification mode

After every market row is populated, run:

```powershell
python scripts\publish_metals_vehicle_metadata.py --strict
```

Strict mode returns a nonzero exit code unless every registered vehicle is complete. A complete record may still be ineligible when stale or classified as research-only/no-approved-vehicle.

## Dashboard fields

The combined dataset includes:

- all structural and market fields
- completeness status
- freshness status
- metadata age in days
- missing-field list
- investability classification
- selection eligibility

## Tests

```powershell
python -m pytest tests\production\test_metals_vehicle_metadata.py -q
python -m pytest tests\production -q
python -m pytest -q
```

## Phase completion sequence

1. Validate structural registry coverage.
2. Populate dated market metadata from approved sources.
3. Publish the dashboard dataset.
4. Confirm every registered vehicle is complete.
5. Confirm stale vehicles remain ineligible.
6. Run strict mode.
7. Record certification evidence.
